import csv

from setuptools.dist import sequence

from lines import Line, Stop

LINES_FILE_NAME = "data/wienerlinien-ogd-linien.csv"
STOPS_FILE_NAME = "data/wienerlinien-ogd-haltepunkte.csv"
CONNECTION_FILE_NAME = "data/wienerlinien-ogd-fahrwegverlaeufe.csv"


def read_lines(lines_file_name: str) -> dict[int:Line]:
    with open(lines_file_name, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        headers = next(csvfile)
        lines: dict[int:Line] = {}
        for row in reader:
            l = Line(int(row[0]), row[1], row[4])
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


def parse_line_patterns(lines: Line, stops: dict[int:Stop]):
    for l in lines:
        for direction, pattern in l.patterns.items():
            for i in range(0, len(pattern)):
                stop = pattern[i]
                stop.prev = pattern[i - 1] if i > 0 else None
                stop.next = pattern[i + 1] if i < len(pattern) - 1 else None


def create_url(line: Line) -> str:
    pass


def main():
    lines = read_lines(LINES_FILE_NAME)
    lines = filter_lines(lines, 'ptMetro')
    print(lines)
    stops = read_stops(STOPS_FILE_NAME)
    read_connections(CONNECTION_FILE_NAME, lines, stops)
    for id, l in lines.items():
        print(l.patterns)
    parse_line_patterns(lines, stops)
    print(lines.pa)


if __name__ == "__main__":
    main()
