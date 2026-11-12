from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Stop:
    id: int
    diva: int | None
    name: str
    city: str
    lat: float | None
    lon: float | None
    next: Stop | None = None  # direction 1
    prev: Stop | None = None  # direction 2
    x_coord: int = 0
    y_coord: int = 0
    line: Line | None = None
    departures: list[int] = field(default_factory=list)
    led_index: dict[str, int] = field(default_factory=dict)
    led_index_overwritten: dict[str, int] = field(default_factory=dict)

    def __str__(self) -> str:
        return f'{self.id}:{self.name}'

    def __repr__(self) -> str:
        return self.__str__()

    def get_departures(self, count: int) -> str:
        return '|'.join(str(d) for d in self.departures[:count])


@dataclass
class Line:
    id: int
    name: str
    type: str
    stops: dict[int, Stop] = field(default_factory=dict)
    patterns: dict[int, dict[int, Stop]] = field(
        default_factory=lambda: {1: {}, 2: {}}
    )  # direction -> sequence -> stop
    color: str = '#000000'
    led_color: dict[int, list[int]] = field(default_factory=dict)

    def __str__(self) -> str:
        return f'{self.id}:{self.name}'

    def __repr__(self) -> str:
        stops = '|'.join(str(stop) for stop in self.stops.values())
        return f'{self.__str__()}({len(self.stops)}stops){stops}'


def get_stop_by_name(
    stops: dict[int, Stop], name: str, all: bool = False
) -> Stop | None | list[Stop]:
    if all:
        return [stop for stop in stops.values() if stop.name == name]
    for stop in stops.values():
        if stop.name == name:
            return stop
    return None


def get_line_by_name(lines: dict[int, Line], name: str) -> Line | None:
    for line in lines.values():
        if line.name == name:
            return line
    return None
