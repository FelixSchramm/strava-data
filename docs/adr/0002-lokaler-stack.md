# 0002: Lokaler, kostenloser Stack

- Status: Akzeptiert
- Datum: 2026-10-18
- Stufe: alle

## Kontext
Ziel ist, Data-Engineering-Konzepte zu lernen, nicht Cloud-Konten zu verwalten. Die Datenmenge (eigene Strava-Aktivitäten) ist klein, und es gibt kein Budget.

## Entscheidung
Alles läuft lokal und mit kostenlosen Werkzeugen: Python für den Extract, DuckDB als Warehouse, dbt für Transformationen, Dagster für die Orchestrierung, pytest für Tests und GitHub Actions für CI.

## Betrachtete Alternativen
- Cloud von Anfang an (S3, BigQuery, verwalteter Orchestrator): näher am Berufsalltag, aber Kosten, Rechteverwaltung und Setup lenken von den Konzepten ab.
- Nur Python-Skripte ohne Werkzeuge: einfacher, aber die Standardwerkzeuge des Fachs lernt man so nicht kennen.

## Konsequenzen
- Schnelles Feedback, keine Kosten, alles offline testbar.
- Die Pipeline läuft nur, wenn der Laptop läuft. Wo sie dauerhaft laufen soll, ist noch offen (siehe [README](README.md#offene-entscheidungen)).
- Cloud-Themen wie Object Storage und Infrastructure as Code kommen erst in Stufe 11.
