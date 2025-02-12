import csv
import requests
from datetime import datetime

from p5 import *

from lines import Line, Stop

LINES_FILE_NAME = "data/wienerlinien-ogd-linien.csv"
STOPS_FILE_NAME = "data/wienerlinien-ogd-haltepunkte.csv"
CONNECTION_FILE_NAME = "data/wienerlinien-ogd-fahrwegverlaeufe.csv"

BASE_URL = "https://www.wienerlinien.at/ogd_realtime/monitor?stopId="
URL_JOINER = "&stopId="

SIZE = (1000, 1000)  # x, y
station_size = 10

stop_list = []

line_colors = {301: '#DA3831', 302: '#9769A6', 303: '#E7883B', 304: '#4AA45A', 306: '#946A41'}


def read_lines(lines_file_name: str) -> dict[int:Line]:
    with open(lines_file_name, newline='') as csvfile:
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
    with open(stops_file_name, newline='') as csvfile:
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
    with open(connections_file_name, newline='') as csvfile:
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


def filter_lines(lines: dict[int:Line], type: str) -> dict[int:Line]:
    l: dict[int:Line] = {}
    for id, line in lines.items():
        if line.type == type:
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
                stop.color = l.color


def calc_coordinates(stops: list[Stop]):
    # get min and max lat and lon
    min_lat = min([s.lat for s in stops])
    max_lat = max([s.lat for s in stops])
    min_lon = min([s.lon for s in stops])
    max_lon = max([s.lon for s in stops])

    # calculate x and y coordinates
    for s in stops:
        x = int((s.lat - min_lat) / (max_lat - min_lat) * SIZE[0])
        y = SIZE[1] - int((s.lon - min_lon) / (max_lon - min_lon) * SIZE[1])
        s.x_coord = x
        s.y_coord = y


def setup():
    size(SIZE[0], SIZE[1])
    no_stroke()
    no_loop()


def draw():
    background(255)
    fill(0)
    ellipse_mode(CENTER)
    global stop_list
    for s in stop_list:
        fill(*color_to_rgb(s.color))
        ellipse(s.x_coord, s.y_coord, station_size, station_size)
        if s.next is not None:
            stroke(*color_to_rgb(s.color))
            line(s.x_coord, s.y_coord, s.next.x_coord, s.next.y_coord)


def color_to_rgb(color: str) -> tuple[int, int, int]:
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


def main():
    lines = read_lines(LINES_FILE_NAME)
    lines = filter_lines(lines, 'ptMetro')
    print(lines)
    stops = read_stops(STOPS_FILE_NAME)
    read_connections(CONNECTION_FILE_NAME, lines, stops)
    for id, l in lines.items():
        print(l.patterns)
    parse_line_patterns(lines)
    stops: list[Stop] = [s for id, l in lines.items() for id, s in l.stops.items()]
    calc_coordinates(stops)
    global stop_list
    stop_list = stops
    # create_url(lines)
    # url = create_url(lines)
    # print(url)
    # response = request_stations(url, save=True)
    # print(response)
    run()


if __name__ == "__main__":
    main()
