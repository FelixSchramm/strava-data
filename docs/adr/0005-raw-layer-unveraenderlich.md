# 0005: Unveränderlicher Raw Layer als JSON

- Status: Akzeptiert
- Datum: 2026-10-18
- Stufe: 2

## Kontext
`fetch_activities.py` überschreibt `data/activities.json` bei jedem Lauf und schreibt erst am Ende. Ein Abbruch verliert alles, und alte Stände sind weg. Für Incremental Load, Deduplizierung und Fehleranalyse braucht es eine verlässliche Historie der API-Antworten.

## Entscheidung
- Jede abgerufene Seite wird sofort als eigene Datei gespeichert, nicht erst am Ende des Laufs.
- Dateien werden nie überschrieben oder geändert.
- Die Ablage erfolgt unter `data/raw/<endpunkt>/ingested_date=YYYY-MM-DD/` (Hive-Partitionierung), mit Metadaten wie Abrufzeit und Request-Parametern.
- Das Format ist JSON, genau so, wie die API es liefert.

## Betrachtete Alternativen
- Eine Datei pro Lauf: einfacher, aber ein Abbruch verliert den ganzen Lauf.
- Parquet im Raw Layer: kleiner und schneller, aber nicht mehr die Originalantwort. Parquet kommt in Stufe 7 bei den Streams, wo es einen spürbaren Unterschied macht.
- Direkt in DuckDB schreiben: kein Datei-Layer nötig, aber es gibt keinen vom Warehouse unabhängigen Rohstand mehr.

## Konsequenzen
- Abbrüche verlieren keine bereits geholten Daten, und jeder Lauf ist nachvollziehbar und nachspielbar.
- Es entstehen viele kleine Dateien, und dieselbe Aktivität kommt mehrfach vor. Die Deduplizierung übernimmt die nächste Schicht ([0008](0008-idempotenz-merge-soft-deletes.md)).
