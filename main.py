import csv
import argparse
from datetime import datetime
import json
import requests

from flask import Flask, request

from lines import Line, Stop, get_line_by_name, get_stop_by_name

BASE_URL = "https://www.wienerlinien.at/ogd_realtime/monitor?stopId="
URL_JOINER = "&stopId="

stop_list = []
global_lines: dict[int:Line] = {}
url = ""

line_colors = {301: '#DA3831', 302: '#9769A6', 303: '#E7883B', 304: '#4AA45A', 306: '#946A41'}
led_colors = {301: {1: [218, 56, 49], 2: [133, 34, 30]}, 302: {1: [151, 105, 166], 2: [228, 159, 251]},
              303: {1: [231, 136, 59], 2: [61, 36, 16]}, 304: {1: [74, 164, 90], 2: [112, 249, 137, ]},
              306: {1: [148, 106, 65], 2: [233, 167, 102]}}
app = Flask(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description='Wiener Linien Monitor')
    parser.add_argument('lines', type=str, help='Path to the lines file')
    parser.add_argument('stops', type=str, help='Path to the stops file')
    parser.add_argument('connections', type=str, help='Path to the connections file')
    parser.add_argument('led_index', type=str, help='Path to the led index file')
    parser.add_argument('--debug', action='store_true', help='Enable Debug Mode')
    args = parser.parse_args()
    return args


def read_lines(lines_file_name: str) -> dict[int:Line]:
    with open(lines_file_name, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        headers = next(csvfile)
        lines: dict[int:Line] = {}
        for row in reader:
            l = Line(int(row[0]), row[1], row[4])
            if l.id in line_colors.keys():
                l.color = line_colors[l.id]
                l.led_color = led_colors[l.id]
            lines[row[0]] = l
        return lines


def read_stops(stops_file_name: str) -> dict[int:Stop]:
    with open(stops_file_name, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        headers = next(csvfile)
        stops: dict[int:Stop] = {}
        for row in reader:
            diva = int(row[1]) if row[1] != '' else None
            lat = float(row[5]) if row[5] != '' else None
            lon = float(row[6]) if row[6] != '' else None
            s = Stop(int(row[0]), diva, row[2], row[3], lat, lon)
            stops[int(row[0])] = s
        return stops


def read_connections(connections_file_name: str, lines: dict[int:Line], stops: dict[int:Stop]):
    with open(connections_file_name, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        headers = next(csvfile)
        for row in reader:
            if int(row[0]) in lines.keys():
                line_id = int(row[0])
                stop_id = int(row[3])
                direction = int(row[4])
                sequence = int(row[2])
                line = lines[line_id]
                line.patterns[direction][sequence] = stops[stop_id]


def read_led_index(stops: dict[int:Stop], file_name: str):
    with open(file_name, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        headers = next(reader)
        for row in reader:
            stop = stops[int(row[1])]
            for i in range(4, len(row)):
                stop.led_index[headers[i]] = int(row[i])


def filter_lines(lines: dict[int:Line], type: str, name: str = None) -> dict[int:Line]:
    l: dict[int:Line] = {}
    for id, line in lines.items():
        if line.type == type:
            if name is not None:
                if line.name == name:
                    l[line.id] = line
            else:
                l[line.id] = line
    return l


def parse_line_patterns(lines: dict[int:Line]):
    for id, l in lines.items():
        for direction, pattern in l.patterns.items():
            for i in range(0, len(pattern)):
                stop = pattern[i]
                stop.prev = pattern[i - 1] if i > 0 else None
                stop.next = pattern[i + 1] if i < len(pattern) - 1 else None
                l.stops[stop.id] = stop
                stop.line = l


def create_url(lines: dict[int:Line]) -> str:
    stop_list = []
    for lid, line in lines.items():
        for id, stop in line.stops.items():
            stop_list.append(id)
    stop_tup = tuple(stop_list)

    return BASE_URL + URL_JOINER.join(map(str, stop_tup))


def request_stations(url: str, save: bool = False):
    response = requests.get(url)
    if save:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        with open(f'responses/{timestamp}_stations.json', 'w') as f:
            f.write(response.text)
    return response.json()


def parse_response(response: dict, lines: dict[int:Line]):
    for monitor in response['data']['monitors']:
        rbl = monitor['locationStop']['properties']['attributes']['rbl']
        for line_dict in monitor['lines']:
            line_name = line_dict['name']
            line = get_line_by_name(lines, line_name)
            for departure in line_dict['departures']['departure']:
                line.stops[rbl].departures.append(departure['departureTime']['countdown'])


def load_response(file_name: str) -> dict:
    with open(file_name, 'r') as f:
        return json.load(f)


def export_stop_csv(stops: dict[int:Stop], file_name: str):
    with open(file_name, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(['line', 'id', 'diva', 'name', 'led_index_simple'])
        for s in stops:
            writer.writerow([s.line.name, s.id, s.diva, s.name, s.led_index['simple']])


def create_led_index(lines: dict[int:Line]):
    led_index: int = 0
    for _, l in lines.items():
        for _, s in l.patterns[1].items():
            s.led_index['simple'] = led_index
            get_stop_by_name(l.patterns[2], s.name).led_index['simple'] = led_index
            led_index += 2


def overwrite_led_index(stops: dict[int:Stop]):
    searched = []
    for _, stop in stops.items():
        if stop.name not in searched:
            searched.append(stop.name)
            similar_stops = get_stop_by_name(stops, stop.name, all=True)
            first_stop = similar_stops[0]
            for s in similar_stops:
                s.led_index_overwritten = first_stop.led_index


def startup(lines_file: str, stops_file: str, connection_file: str, led_index_file: str, ) -> str:
    lines = read_lines(lines_file)
    lines = filter_lines(lines, 'ptMetro', None)
    stops_dict = read_stops(stops_file)
    read_connections(connection_file, lines, stops_dict)
    parse_line_patterns(lines)
    stops_dict: dict[int:Stop] = {id: s for id, s in stops_dict.items() if s.line is not None}
    stops: list[Stop] = [s for id, l in lines.items() for id, s in l.stops.items()]
    # create_led_index(lines)
    # export_stop_csv(stops, LED_INDEX_FILE_NAME)
    read_led_index(stops_dict, led_index_file)
    overwrite_led_index(stops_dict)
    global stop_list
    stop_list = stops
    global global_lines
    global_lines = lines
    return create_url(lines)


def main():
    args = parse_args()
    global url
    url = startup(args.lines, args.stops, args.connections, args.led_index)
    app.run(debug=args.debug, host='0.0.0.0')


last_response = None
last_response_time = 0


@app.route("/api/<name>")
def api(name: str):
    filter_param = request.args.get('filter')
    print(filter_param)  # TODO: implement filter
    # request if response is older than 30 seconds
    global last_response
    global last_response_time
    global global_lines
    timestamp_now = datetime.now().timestamp()
    if (timestamp_now - last_response_time) > 30:
        last_response_time = timestamp_now
        last_response = request_stations(url)
        parse_response(last_response, global_lines)
        last_response_time = timestamp_now
    # convert to led index -> color json
    color_dict = {}
    for l_id, l in global_lines.items():
        for direction, pattern in l.patterns.items():
            for s in pattern.values():
                if 0 in s.departures:
                    color_dict[s.led_index_overwritten[name]] = l.led_color[direction]
                if 1 in s.departures:
                    if s.prev is not None:
                        color_dict[s.led_index_overwritten[name] + 1] = l.led_color[
                            direction]  # TODO: calc between station led id
    # TODO: implement two trains on one LED ID
    return {"timestamp_iso": last_response_time,
            "timestamp": datetime.fromtimestamp(timestamp_now).strftime('%Y-%m-%d %H:%M:%S'),
            "led_index_name": name,
            "leds": color_dict}


if __name__ == "__main__":
    main()
