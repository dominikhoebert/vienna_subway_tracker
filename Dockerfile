FROM python:3.10-slim-buster
LABEL authors="Dominik"

WORKDIR /app

COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY data/fahrwegverlaeufe.csv .
COPY data/haltepunkte.csv .
COPY data/led_index.csv .
COPY data/linien.csv .

COPY lines.py .
COPY main.py .

ENTRYPOINT ["python3", "main.py", "linien.csv", "haltepunkte.csv", "fahrwegverlaeufe.csv", "led_index.csv", "--debug"]