# 0003: DuckDB als Warehouse

- Status: Akzeptiert
- Datum: 2026-10-18
- Stufe: 4

## Kontext
Ab Stufe 4 braucht das Projekt ein Warehouse, in dem Rohdaten geladen, dedupliziert und ausgewertet werden. Die Abfragen sind analytisch (Summen, Wochenwerte, Trends). Die Datenmenge ist klein bis mittel: Die Aktivitäten sind wenige Megabyte, die Streams später Millionen Zeilen. dbt muss mit dem Warehouse arbeiten können.

## Entscheidung
DuckDB als Warehouse, gespeichert als eine lokale Datei.

## Betrachtete Alternativen
- Postgres: weit verbreitet, aber zeilenorientiert (OLTP) und braucht einen laufenden Server.
- SQLite: auch nur eine Datei, aber für Analysen langsam und mit wenigen analytischen Funktionen.
- BigQuery oder Snowflake: echte Cloud-Warehouses, aber mit Kosten und Konto (siehe [0002](0002-lokaler-stack.md)).

## Konsequenzen
- Spaltenorientiert und schnell für Analysen, kein Server, liest JSON und Parquet direkt, gute dbt-Unterstützung über `dbt-duckdb`.
- `MERGE INTO` gibt es erst ab DuckDB 1.4.
- Eine DuckDB-Datei kann entweder von einem Prozess gelesen und beschrieben oder von mehreren Prozessen nur gelesen werden. Pipeline und Dashboard können also nicht gleichzeitig darauf zugreifen. Das muss spätestens in Stufe 10 gelöst werden.
- Ein späterer Umstieg auf MotherDuck (DuckDB in der Cloud) wäre ein kleiner Schritt.
