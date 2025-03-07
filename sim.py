from p5 import *

from lines import Stop
from main import *

SIZE = (1000, 1000)  # x, y
station_size = 10

stop_list = []
global_lines: dict[int:Line] = {}
url = ""


def color_to_rgb(color: str) -> tuple[int, ...]:
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def calc_between_coords(s1: Stop, s2: Stop) -> tuple[int, int]:
    x = int((s1.x_coord + s2.x_coord) / 2)
    y = int((s1.y_coord + s2.y_coord) / 2)
    return x, y


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
    calc_coordinates(stops)
    global stop_list
    stop_list = stops
    global global_lines
    global_lines = lines
    return create_url(lines)


if __name__ == '__main__':
    args = parse_args()
    url = startup(args.lines, args.stops, args.connections, args.led_index)
    response = request_stations(url, save=True)
    # response = load_response('responses/20250227133034_stations.json')
    # print(response)
    parse_response(response, global_lines)
    run()
