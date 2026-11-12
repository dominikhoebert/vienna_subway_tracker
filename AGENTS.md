# AGENTS.md

Flask service that turns Wiener Linien realtime departures into LED-map JSON, plus a separate p5 desktop simulation.

## Run

```bash
pip install -r requirements.txt
python3 main.py data/linien.csv data/haltepunkte.csv data/fahrwegverlaeufe.csv data/led_index.csv [--debug]
```

- Positional order is fixed (`lines stops connections led_index`); the server listens on `0.0.0.0:5000`.
- Shortcuts: `just run`, `just run-debug`, `just sim`, `just check`, `just docker-build`.
- `startup()` parses CSVs and computes stop map coordinates. The upstream API is first called on an API request, then cached for 30 s.
- Web map: `GET /map` serves `templates/map.html` (SVG, polls `/map/data` every 30 s). `/map/data` returns stops, line patterns and the next departures.
- `GET /api/<name>`: `<name>` must be a key in `Stop.led_index`, i.e. a column name from `data/led_index.csv` — currently `/api/led_index_simple`. Unknown names return `404` with the available names.
- Docker: `docker build -t vienna-subway-tracker .` then `docker run -p 5000:5000 vienna-subway-tracker`. The image copies the four CSVs into `/app` and passes bare filenames; `sim.py` is not in the image.

## Layout

- `main.py` — CSV loaders, `startup()`, `calc_coordinates()`, Flask app. Module globals `global_lines`, `stop_list`, `url` are filled by `startup()`.
- `lines.py` — `Line`/`Stop` dataclasses and name lookups.
- `templates/map.html` — web map page served at `/map`.
- `sim.py` — p5 map view. It reuses `main.startup()` (which computes coordinates); run it separately from a checkout containing `p5`.
- `data/*.csv` — semicolon-separated, parsed positionally; the header row is skipped.

## CSV columns actually read

- `linien.csv`: `0 LineID`, `1 LineText`, `4 MeansOfTransport`. Only `ptMetro` rows are kept.
- `haltepunkte.csv`: `0 StopID`, `1 DIVA`, `2 StopText`, `3 Municipality`, `5 Longitude`, `6 Latitude`. The loader stores these as `Stop.lon` and `Stop.lat` respectively.
- `fahrwegverlaeufe.csv`: `0 LineID`, `1 PatternID`, `2 StopSeqCount`, `3 StopID`, `4 Direction`. When a line/direction has several patterns, the loader keeps the longest one.
- `led_index.csv`: `1` is `StopID`; every column from index 4 onward becomes an LED index name (e.g. `led_index_simple`).

## Gotchas

- `sim.py` maps `lon` to x and `lat` to y; keep that orientation when touching `calc_coordinates()`.
- `read_connections()` picks the longest `PatternID` per line/direction. Don't switch it back to "last row wins" without checking short-turn patterns.
- Line colors and LED colors are hardcoded in `main.py` for IDs `301`, `302`, `303`, `304`, `306`; any other line gets no color/LED color.
- `sim.py` needs `p5`, which is not in `requirements.txt`; it also imports `main`, so Flask and requests must be installed too.
- `parse_response()` replaces all departure lists on every poll. Preserve that reset when changing the API parsing, or countdowns will accumulate.
- `?filter=` is still ignored (no implementation yet).
- `README.md` is German and partly aspirational (the data-generation script it mentions is not in the repo); trust code and config over it.
- No test, lint, typecheck, or CI config exists. Verify by importing/running `startup()` or by building the Docker image; don't assume pytest/flake8 setup.
