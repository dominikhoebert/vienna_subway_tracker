from __future__ import annotations

from p5 import *

import main
from lines import Stop

SIZE = (1000, 1000)  # x, y
STATION_SIZE = 10
SHOW_NAMES = True
SHOW_DEPARTURES = True


def color_to_rgb(color: str) -> tuple[int, ...]:
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def calc_between_coords(s1: Stop, s2: Stop) -> tuple[int, int]:
    return (s1.x_coord + s2.x_coord) // 2, (s1.y_coord + s2.y_coord) // 2


def map_range(
    value: float, in_min: float, in_max: float, out_min: float, out_max: float
) -> float:
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def calc_coordinates(stops: list[Stop]) -> None:
    located = [stop for stop in stops if stop.lat is not None and stop.lon is not None]
    if not located:
        return

    min_lat = min(stop.lat for stop in located)
    max_lat = max(stop.lat for stop in located)
    min_lon = min(stop.lon for stop in located)
    max_lon = max(stop.lon for stop in located)

    min_x = 20
    min_y = 20
    max_x = SIZE[0] - 80
    max_y = SIZE[1] - 140

    for stop in located:
        lat, lon = stop.lat, stop.lon
        if lat is None or lon is None:
            continue
        stop.x_coord = int(map_range(lon, min_lon, max_lon, min_x, max_x))
        stop.y_coord = int(map_range(lat, min_lat, max_lat, max_y, min_y))


def setup() -> None:
    size(SIZE[0], SIZE[1])
    no_stroke()
    no_loop()


def draw() -> None:
    direction_filter = 0
    background(255)
    fill(0)
    ellipse_mode(CENTER)

    for metro_line in main.global_lines.values():
        for direction, pattern in metro_line.patterns.items():
            for stop in pattern.values():
                fill(*color_to_rgb(metro_line.color))
                if direction == 1:
                    ellipse(stop.x_coord, stop.y_coord, STATION_SIZE, STATION_SIZE)
                    if SHOW_NAMES:
                        text(stop.name, stop.x_coord + 10, stop.y_coord)
                    if direction_filter in (0, 1) and SHOW_DEPARTURES:
                        text(
                            stop.get_departures(3),
                            stop.x_coord + 10,
                            stop.y_coord + 10,
                        )
                    if stop.next is not None:
                        stroke(*color_to_rgb(metro_line.color))
                        line(
                            stop.x_coord,
                            stop.y_coord,
                            stop.next.x_coord,
                            stop.next.y_coord,
                        )
                if (
                    direction == 2
                    and direction_filter in (0, 2)
                    and SHOW_DEPARTURES
                ):
                    text(
                        stop.get_departures(3),
                        stop.x_coord + 10,
                        stop.y_coord + 20,
                    )
                if direction_filter in (0, direction):
                    departures = set(stop.departures)
                    if 0 in departures:
                        fill(240, 240, 0)
                        ellipse(stop.x_coord, stop.y_coord, 8, 8)
                    if 1 in departures and stop.prev is not None:
                        fill(240, 240, 0)
                        cx, cy = calc_between_coords(stop, stop.prev)
                        ellipse(cx, cy, 8, 8)


if __name__ == '__main__':
    args = main.parse_args()
    url = main.startup(args.lines, args.stops, args.connections, args.led_index)
    calc_coordinates(main.stop_list)
    response = main.request_stations(url, save=True)
    main.parse_response(response, main.global_lines)
    run()
