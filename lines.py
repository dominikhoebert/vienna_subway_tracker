from dataclasses import dataclass, field


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
    color: str = '#000000'

    def __str__(self):
        return f'{self.id}:{self.name}'

    def __repr__(self):
        return self.__str__()


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
