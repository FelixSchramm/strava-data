# 0012: Dagster als Orchestrator

- Status: Akzeptiert
- Datum: 2026-10-18
- Stufe: 6

## Kontext
Ab Stufe 6 sollen Extract, Raw Layer und dbt täglich und in der richtigen Reihenfolge laufen, mit Retries, Laufhistorie und Backfills über Zeiträume. Der Streams-Backfill in Stufe 7 muss über mehrere Tage immer wieder angestoßen werden. Die Transformationen liegen in dbt.

## Entscheidung
Dagster mit Assets, die dbt-Models werden über `dagster-dbt` eingebunden. Vorher wird derselbe Ablauf einmal mit cron gebaut, zum Vergleich.

## Betrachtete Alternativen
- Airflow: am weitesten verbreitet, aber task-basiert, lokal aufwendiger zu betreiben, und dbt läuft dort meist als ein einzelner Schritt statt als einzelne Tabellen.
- Prefect: leichtgewichtig und nah an normalem Python, aber flow-basiert, mit derselben Einschränkung bei dbt.
- Nur cron oder launchd: technisch ausreichend, aber ohne Abhängigkeiten, Historie und Backfills.

## Konsequenzen
- Das Asset-Modell passt zu den Schichten aus [0004](0004-elt-mit-medallion.md): Jede Tabelle ist ein Asset mit sichtbarer Herkunft und Aktualität.
- Für eine einzige kleine Pipeline ist Dagster überdimensioniert. Das ist als Lernziel gewollt.
- Wo Dagster dauerhaft läuft, ist noch offen (siehe [README](README.md#offene-entscheidungen)).
