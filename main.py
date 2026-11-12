from __future__ import annotations

import argparse
import csv
import json
import math
import os
import threading
import time
from datetime import datetime
from typing import Any

import requests
from flask import Flask, render_template

from lines import Line, Stop, get_stop_by_name

BASE_URL = 'https://www.wienerlinien.at/ogd_realtime/monitor?stopId='
URL_JOINER = '&stopId='
CACHE_TTL_SECONDS = 30
REQUEST_TIMEOUT_SECONDS = 10
MAP_SIZE = (1000, 1000)  # x, y

LINE_COLORS = {
    301: '#DA3831',
    302: '#9769A6',
    303: '#E7883B',
    304: '#4AA45A',
    306: '#946A41',
}
LED_COLORS = {
    301: {1: [218, 56, 49], 2: [133, 34, 30]},
    302: {1: [151, 105, 166], 2: [228, 159, 251]},
    303: {1: [231, 136, 59], 2: [61, 36, 16]},
    304: {1: [74, 164, 90], 2: [112, 249, 137]},
    306: {1: [148, 106, 65], 2: [233, 167, 102]},
}

stop_list: list[Stop] = []
map_projection: tuple[float, float, float, float] | None = None
global_lines: dict[int, Line] = {}
led_index_names: list[str] = []
url = ''

app = Flask(__name__)

_cache_lock = threading.Lock()
_last_response: dict[str, Any] | None = None
_last_response_at = 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Wiener Linien Monitor')
    parser.add_argument('lines', type=str, help='Path to the lines file')
    parser.add_argument('stops', type=str, help='Path to the stops file')
    parser.add_argument('connections', type=str, help='Path to the connections file')
    parser.add_argument('led_index', type=str, help='Path to the led index file')
    parser.add_argument('--debug', action='store_true', help='Enable Debug Mode')
    return parser.parse_args()


def read_lines(lines_file_name: str) -> dict[int, Line]:
    with open(lines_file_name, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        next(reader)  # header
        lines: dict[int, Line] = {}
        for row in reader:
            line = Line(int(row[0]), row[1], row[4])
            if line.id in LINE_COLORS:
                line.color = LINE_COLORS[line.id]
                line.led_color = LED_COLORS[line.id]
            lines[line.id] = line
        return lines


def read_stops(stops_file_name: str) -> dict[int, Stop]:
    with open(stops_file_name, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        next(reader)  # header
        stops: dict[int, Stop] = {}
        for row in reader:
            diva = int(row[1]) if row[1] != '' else None
            # haltepunkte.csv: ...;MunicipalityID;Longitude;Latitude
            lat = float(row[6]) if row[6] != '' else None
            lon = float(row[5]) if row[5] != '' else None
            stop = Stop(int(row[0]), diva, row[2], row[3], lat, lon)
            stops[stop.id] = stop
        return stops


def read_connections(
    connections_file_name: str,
    lines: dict[int, Line],
    stops: dict[int, Stop],
) -> None:
    # Keep every pattern first, then select the longest one per line/direction.
    # A line can have short-turn patterns; picking the last row would make the
    # rendered route depend on CSV order.
    patterns: dict[tuple[int, int, str], dict[int, Stop]] = {}
    pattern_order: list[tuple[int, int, str]] = []

    with open(connections_file_name, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        next(reader)  # header
        for row in reader:
            line = lines.get(int(row[0]))
            if line is None:
                continue
            stop = stops.get(int(row[3]))
            if stop is None:
                continue
            direction = int(row[4])
            if direction not in line.patterns:
                continue
            key = (line.id, direction, row[1])
            if key not in patterns:
                patterns[key] = {}
                pattern_order.append(key)
            patterns[key][int(row[2])] = stop

    best_patterns: dict[tuple[int, int], dict[int, Stop]] = {}
    for line_id, direction, pattern_id in pattern_order:
        pattern = patterns[(line_id, direction, pattern_id)]
        current = best_patterns.get((line_id, direction))
        if current is None or len(pattern) >= len(current):
            best_patterns[(line_id, direction)] = pattern

    for (line_id, direction), pattern in best_patterns.items():
        lines[line_id].patterns[direction] = pattern


def read_led_index(stops: dict[int, Stop], file_name: str) -> None:
    with open(file_name, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        headers = next(reader)
        for row in reader:
            stop = stops.get(int(row[1]))
            if stop is None:
                continue
            for header, value in zip(headers[4:], row[4:]):
                if value != '':
                    stop.led_index[header] = int(value)


def filter_lines(
    lines: dict[int, Line], line_type: str, name: str | None = None
) -> dict[int, Line]:
    return {
        line.id: line
        for line in lines.values()
        if line.type == line_type and (name is None or line.name == name)
    }


def parse_line_patterns(lines: dict[int, Line]) -> None:
    for line in lines.values():
        line.stops.clear()
        for pattern in line.patterns.values():
            ordered = [pattern[sequence] for sequence in sorted(pattern)]
            for i, stop in enumerate(ordered):
                stop.prev = ordered[i - 1] if i > 0 else None
                stop.next = ordered[i + 1] if i + 1 < len(ordered) else None
                line.stops[stop.id] = stop
                stop.line = line


def create_url(lines: dict[int, Line]) -> str:
    # The realtime endpoint is queried once per unique stop ID.
    stop_ids = dict.fromkeys(
        stop.id for line in lines.values() for stop in line.stops.values()
    )
    return BASE_URL + URL_JOINER.join(map(str, stop_ids))


def request_stations(url: str, save: bool = False) -> dict[str, Any]:
    response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    if save:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        path = os.path.join('responses', f'{timestamp}_stations.json')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(response.text)
    return response.json()


def parse_response(response: dict[str, Any], lines: dict[int, Line]) -> None:
    """Replace the previous departure snapshot with the latest API response."""
    lines_by_name = {line.name: line for line in lines.values()}
    departures_by_stop: dict[int, list[int]] = {}

    for monitor in response.get('data', {}).get('monitors', []):
        rbl = int(monitor['locationStop']['properties']['attributes']['rbl'])
        for line_data in monitor.get('lines', []):
            line = lines_by_name.get(line_data['name'])
            if line is None or rbl not in line.stops:
                continue
            departures_by_stop.setdefault(rbl, []).extend(
                departure['departureTime']['countdown']
                for departure in line_data.get('departures', {}).get('departure', [])
            )

    for line in lines.values():
        for stop in line.stops.values():
            stop.departures[:] = departures_by_stop.get(stop.id, [])


def load_response(file_name: str) -> dict[str, Any]:
    with open(file_name, 'r', encoding='utf-8') as f:
        return json.load(f)


def export_stop_csv(stops: list[Stop], file_name: str) -> None:
    with open(file_name, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(['line', 'id', 'diva', 'name', 'led_index_simple'])
        for stop in stops:
            writer.writerow(
                [
                    stop.line.name if stop.line is not None else '',
                    stop.id,
                    stop.diva if stop.diva is not None else '',
                    stop.name,
                    stop.led_index.get('led_index_simple', ''),
                ]
            )


def create_led_index(lines: dict[int, Line]) -> None:
    led_index = 0
    for line in lines.values():
        forward = line.patterns.get(1, {})
        backward = line.patterns.get(2, {})
        for sequence in sorted(forward):
            stop = forward[sequence]
            stop.led_index['led_index_simple'] = led_index
            counterpart = get_stop_by_name(backward, stop.name)
            if counterpart is not None:
                counterpart.led_index['led_index_simple'] = led_index
            led_index += 2


def overwrite_led_index(stops: dict[int, Stop]) -> None:
    stops_by_name: dict[str, list[Stop]] = {}
    for stop in stops.values():
        stops_by_name.setdefault(stop.name, []).append(stop)

    for same_name_stops in stops_by_name.values():
        source = next(
            (stop for stop in same_name_stops if stop.led_index),
            same_name_stops[0],
        )
        for stop in same_name_stops:
            stop.led_index_overwritten = source.led_index


def calc_coordinates(stops: list[Stop]) -> tuple[float, float, float, float] | None:
    # Returns (ax, bx, ay, by) with x = ax * lon + bx and y = ay * lat + by.
    # Longitude is scaled by cos(latitude) so the map keeps its real proportions
    # and the OpenStreetMap background lines up with the stops.
    located = [stop for stop in stops if stop.lat is not None and stop.lon is not None]
    if not located:
        return None

    min_lat = min(stop.lat for stop in located)
    max_lat = max(stop.lat for stop in located)
    min_lon = min(stop.lon for stop in located)
    max_lon = max(stop.lon for stop in located)

    min_x = 20
    min_y = 20
    max_x = MAP_SIZE[0] - 80
    max_y = MAP_SIZE[1] - 140

    lon_scale = math.cos(math.radians((min_lat + max_lat) / 2))
    geo_width = (max_lon - min_lon) * lon_scale
    geo_height = max_lat - min_lat
    scale = min((max_x - min_x) / geo_width, (max_y - min_y) / geo_height)
    offset_x = min_x + ((max_x - min_x) - geo_width * scale) / 2
    offset_y = min_y + ((max_y - min_y) - geo_height * scale) / 2

    ax = lon_scale * scale
    bx = offset_x - min_lon * ax
    ay = -scale
    by = offset_y + max_lat * scale

    for stop in located:
        stop.x_coord = int(ax * stop.lon + bx)
        stop.y_coord = int(ay * stop.lat + by)
    return ax, bx, ay, by


def startup(
    lines_file: str,
    stops_file: str,
    connection_file: str,
    led_index_file: str,
) -> str:
    global stop_list, global_lines, led_index_names, url, map_projection

    lines = filter_lines(read_lines(lines_file), 'ptMetro')
    stops = read_stops(stops_file)
    read_connections(connection_file, lines, stops)
    parse_line_patterns(lines)
    stops = {
        stop_id: stop for stop_id, stop in stops.items() if stop.line is not None
    }
    read_led_index(stops, led_index_file)
    overwrite_led_index(stops)

    global_lines = lines
    stop_list = list(stops.values())
    map_projection = calc_coordinates(stop_list)
    led_index_names = sorted(
        {key for stop in stops.values() for key in stop.led_index_overwritten}
    )
    url = create_url(lines)
    return url


def build_leds(name: str) -> dict[int, list[int]]:
    leds: dict[int, list[int]] = {}
    for line in global_lines.values():
        for direction, pattern in line.patterns.items():
            color = line.led_color.get(direction)
            if color is None:
                continue
            for stop in pattern.values():
                led_id = stop.led_index_overwritten.get(name)
                if led_id is None:
                    continue
                departures = set(stop.departures)
                if 0 in departures:
                    leds[led_id] = color
                if 1 in departures and stop.prev is not None:
                    # TODO: interpolate the LED between this stop and the previous one.
                    leds[led_id + 1] = color
    return leds


def get_response() -> dict[str, Any]:
    """Return a cached API response, refreshing it at most once per TTL."""
    global _last_response, _last_response_at

    now = time.time()
    if _last_response is not None and now - _last_response_at <= CACHE_TTL_SECONDS:
        return _last_response

    with _cache_lock:
        now = time.time()
        if _last_response is not None and now - _last_response_at <= CACHE_TTL_SECONDS:
            return _last_response

        response = request_stations(url)
        parse_response(response, global_lines)
        _last_response = response
        _last_response_at = time.time()
        return response


@app.route('/api/<name>')
def api(name: str):
    # TODO: implement the `filter` query parameter (currently ignored).
    if name not in led_index_names:
        return {
            'error': f'unknown led index {name!r}',
            'available': led_index_names,
        }, 404

    get_response()
    with _cache_lock:
        leds = build_leds(name)
        timestamp = _last_response_at

    return {
        'timestamp_iso': timestamp,
        'timestamp': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
        'led_index_name': name,
        'leds': leds,
    }


def station_departures(group: list[tuple[int, Stop]], direction: int) -> list[int]:
    return sorted(
        countdown
        for platform_direction, stop in group
        if platform_direction == direction
        for countdown in stop.departures
    )[:3]


def build_map_data() -> dict[str, Any]:
    # Platforms of one station (one StopID per direction) share a name, so they
    # are merged into one map station named by that name.
    platforms: dict[str, list[tuple[int, Stop]]] = {}
    lines: list[dict[str, Any]] = []
    for line in global_lines.values():
        directions: dict[str, list[str]] = {}
        for direction, pattern in line.patterns.items():
            ordered = [pattern[sequence] for sequence in sorted(pattern)]
            located = [s for s in ordered if s.lat is not None and s.lon is not None]
            if not located:
                continue
            directions[str(direction)] = [s.name for s in located]
            for s in located:
                platforms.setdefault(s.name, []).append((direction, s))
        if directions:
            lines.append(
                {
                    'id': line.id,
                    'name': line.name,
                    'color': line.color,
                    'directions': directions,
                }
            )
    projection = None
    if map_projection is not None:
        ax, bx, ay, by = map_projection
        projection = {'x': [ax, bx], 'y': [ay, by]}
    return {
        'projection': projection,
        'stations': [
            {
                'name': name,
                'x': int(sum(s.x_coord for _, s in group) / len(group)),
                'y': int(sum(s.y_coord for _, s in group) / len(group)),
                'departures': {
                    '1': station_departures(group, 1),
                    '2': station_departures(group, 2),
                },
            }
            for name, group in platforms.items()
        ],
        'lines': lines,
    }


@app.route('/map')
def map_view():
    return render_template('map.html')


@app.route('/map/data')
def map_data():
    get_response()
    with _cache_lock:
        data = build_map_data()
        timestamp = _last_response_at
    data['timestamp'] = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    return data


def main() -> None:
    args = parse_args()
    startup(args.lines, args.stops, args.connections, args.led_index)
    app.run(debug=args.debug, host='0.0.0.0')


if __name__ == '__main__':
    main()
