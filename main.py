import csv
import argparse

from datetime import datetime

from p5 import *

from lines import Line, Stop, get_line_by_name, get_stop_by_name

LINES_FILE_NAME = "data/linien.csv"
STOPS_FILE_NAME = "data/haltepunkte.csv"
CONNECTION_FILE_NAME = "data/fahrwegverlaeufe.csv"
LED_INDEX_FILE_NAME = "data/led_index.csv"

BASE_URL = "https://www.wienerlinien.at/ogd_realtime/monitor?stopId="
URL_JOINER = "&stopId="

SIZE = (1000, 1000)  # x, y
station_size = 10

stop_list = []
global_lines: dict[int:Line] = {}

line_colors = {301: '#DA3831', 302: '#9769A6', 303: '#E7883B', 304: '#4AA45A', 306: '#946A41'}


def parse_args():
    parser = argparse.ArgumentParser(description='Wiener Linien Monitor')
    parser.add_argument('lines', type=str, help='Path to the lines file')
    parser.add_argument('stops', type=str, help='Path to the stops file')
    parser.add_argument('connections', type=str, help='Path to the connections file')
    parser.add_argument('led_index', type=str, help='Path to the led index file')
    parser.add_argument('--p5', action='store_true', help='Enable p5 Simulation')
    args = parser.parse_args()
    LINES_FILE_NAME = args.lines
    STOPS_FILE_NAME = args.stops
    CONNECTION_FILE_NAME = args.connections
    LED_INDEX_FILE_NAME = args.led_index


def read_lines(lines_file_name: str) -> dict[int:Line]:
    with open(lines_file_name, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        headers = next(csvfile)
        lines: dict[int:Line] = {}
        for row in reader:
            l = Line(int(row[0]), row[1], row[4])
            if l.id in line_colors.keys():
                l.color = line_colors[l.id]
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


def map_range(value: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def calc_coordinates(stops: list[Stop]):
    # get min and max lat and lon
    min_lat = min([s.lat for s in stops])
    max_lat = max([s.lat for s in stops])
    min_lon = min([s.lon for s in stops])
    max_lon = max([s.lon for s in stops])

    min_x = 20
    min_y = 20
    max_x = SIZE[0] - 80
    max_y = SIZE[1] - 140

    # calculate x and y coordinates
    for s in stops:
        # x = int((s.lat - min_lat) / (max_lat - min_lat) * SIZE[0])
        # y = SIZE[1] - int((s.lon - min_lon) / (max_lon - min_lon) * SIZE[1])
        x = int(map_range(s.lat, min_lat, max_lat, min_x, max_x))
        y = int(map_range(s.lon, min_lon, max_lon, max_y, min_y))
        s.x_coord = x
        s.y_coord = y


def calc_between_coords(s1: Stop, s2: Stop) -> tuple[int, int]:
    x = int((s1.x_coord + s2.x_coord) / 2)
    y = int((s1.y_coord + s2.y_coord) / 2)
    return x, y


def setup():
    size(SIZE[0], SIZE[1])
    no_stroke()
    no_loop()


def draw():
    dir = 0
    show_name = True
    show_departures = True
    background(255)
    fill(0)
    ellipse_mode(CENTER)
    global global_lines
    for l_id, l in global_lines.items():
        for direction, pattern in l.patterns.items():
            for s in pattern.values():
                fill(*color_to_rgb(s.line.color))
                if direction == 1:
                    ellipse(s.x_coord, s.y_coord, station_size, station_size)
                    if show_name:
                        text(s.name, s.x_coord + 10, s.y_coord)
                    if (dir == 0 or dir == 1) and show_departures:
                        text(s.get_departures(3), s.x_coord + 10, s.y_coord + 10)
                    if s.next is not None:
                        stroke(*color_to_rgb(s.line.color))
                        line(s.x_coord, s.y_coord, s.next.x_coord, s.next.y_coord)
                if direction == 2 and (dir == 0 or dir == 2) and show_departures:
                    text(s.get_departures(3), s.x_coord + 10, s.y_coord + 20)
                if direction == dir or dir == 0:
                    if 0 in s.departures:
                        fill(240, 240, 0)
                        ellipse(s.x_coord, s.y_coord, 8, 8)
                    if 1 in s.departures:
                        fill(240, 240, 0)
                        if s.prev is not None:
                            cx, cy = calc_between_coords(s, s.prev)
                            ellipse(cx, cy, 8, 8)


def color_to_rgb(color: str) -> tuple[int, ...]:
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


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
    calc_coordinates(stops)
    global stop_list
    stop_list = stops
    global global_lines
    global_lines = lines
    return create_url(lines)


def main():
    parse_args()
    url = startup(LINES_FILE_NAME, STOPS_FILE_NAME, CONNECTION_FILE_NAME, LED_INDEX_FILE_NAME)
    response = request_stations(url, save=True)
    # response = load_response('responses/20250227133034_stations.json')
    # print(response)
    global global_lines
    parse_response(response, global_lines)
    # for s in stops:
    #     print(s.name, s.departures)
    run()


if __name__ == "__main__":
    main()
