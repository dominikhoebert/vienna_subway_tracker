# List available recipes.
default:
    @just --list

# Install runtime dependencies.
install:
    python3 -m pip install -r requirements.txt

# Run the Flask server with the checked-in CSV data.
run:
    python3 main.py data/linien.csv data/haltepunkte.csv data/fahrwegverlaeufe.csv data/led_index.csv

# Run the Flask server with Flask's debug mode enabled.
run-debug:
    python3 main.py data/linien.csv data/haltepunkte.csv data/fahrwegverlaeufe.csv data/led_index.csv --debug

# Run the p5 simulation. Requires `p5` in addition to requirements.txt.
sim:
    python3 sim.py data/linien.csv data/haltepunkte.csv data/fahrwegverlaeufe.csv data/led_index.csv

# Byte-compile all Python sources.
check:
    python3 -m compileall -q main.py sim.py lines.py

# Build the server image.
docker-build:
    docker build -t vienna-subway-tracker .

# Run the server image on port 5000.
docker-run:
    docker run --rm -p 5000:5000 vienna-subway-tracker

# Remove generated Python bytecode caches.
clean:
    rm -rf __pycache__ */__pycache__
