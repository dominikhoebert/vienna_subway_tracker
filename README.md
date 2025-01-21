# vienna_subway_tracker

![nyc tracker](https://store.moma.org/cdn/shop/files/a9eb8fc7-5739-484c-833c-dd63cb09d930_cf8b2548-e9fb-497e-a577-26484dc17238_1296x.jpg?v=1704608154)
[NYC Traintracker](https://store.moma.org/en-at/products/traintrackr-nyc-subway-circuit-board-2) für Wiener Ubahn
# Data
aus der [WL API](https://www.data.gv.at/katalog/dataset/522d3045-0b37-48d0-b868-57c99726b1c4) eine große Abfrage für alle Ubahnstationen (oder per linie?) erstellen:
[RBL-tool](https://till.mabe.at/rbl/?line=301&station=75010)
```
https://www.wienerlinien.at/ogd_realtime/monitor?stopId=2171&stopId=168
```
mit Python Script aus wienerlinien-ogd-fahrverlaeufe.csv, haltepunkte und linien