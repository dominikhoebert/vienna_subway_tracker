from dataclasses import dataclass, field
from typing import Any


@dataclass()
class Stop:
    id: int
    diva: int
    name: str
    city: str
    lat: float
    lon: float
    next: 'Stop' = None  # direction 1
    prev: 'Stop' = None  # direction 2
    x_coord: int = 0
    y_coord: int = 0
    line = None
    departures: list[int] = field(default_factory=lambda: [])
    led_index: dict[str:int] = field(default_factory=lambda: {})

    def __str__(self):
        return f'{self.id}:{self.name}'

    def __repr__(self):
        return self.__str__()

    def get_departures(self, count: int) -> str:
        deps = [str(d) for d in self.departures[:count]]
        return '|'.join(deps)


def get_stop_by_name(stops: dict[int:Stop], name: str) -> Stop | None:
    for id, stop in stops.items():
        if stop.name == name:
            return stop
    return None


@dataclass
class Line:
    id: int
    name: str
    type: str
    stops: dict[int:Stop] = field(default_factory=lambda: {})
    patterns: dict[int:dict[int:Stop]] = field(default_factory=lambda: {1: {}, 2: {}})  # direction -> sequence -> stop
    color: str = '#000000'

    def __str__(self):
        return f'{self.id}:{self.name}'

    def __repr__(self):
        return self.__str__() + f'({len(self.stops)}stops)' + '|'.join([str(s) for id, s in self.stops.items()])


def get_line_by_name(lines: dict[int:Line], name: str) -> Line | None:
    for id, line in lines.items():
        if line.name == name:
            return line
    return None
