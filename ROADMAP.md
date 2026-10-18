# Lern-Roadmap: Data Engineering mit der Strava-API

Ziel: Eine kleine, aber echte Datenpipeline bauen und dabei die Kernkonzepte des Data Engineering lernen. Jede Stufe baut auf der vorigen auf und hat ein klares "Fertig wenn".

Stack-Vorschlag (alles lokal, kostenlos): Python, DuckDB, dbt, pytest, Dagster, GitHub Actions.

Meilenstein 1 ist Stufe 5: Danach steht eine komplette Pipeline von der API bis zur Auswertung, auch wenn du danach pausierst.

## Stufe 0: Ist-Stand
`fetch_activities.py` holt alle Aktivitäten und schreibt eine JSON-Datei.
Das ist ein Full Load ohne State, ohne Tests und ohne Fehlerbehandlung. Die nächsten Stufen beheben genau das.
- Aufgabe: Die JSON-Datei direkt mit DuckDB abfragen (`select * from read_json_auto('data/activities.json')`) und Felder, Einheiten und Zeitstempel anschauen.
- Fertig wenn: Du weißt, welche Felder es gibt, und der Ist-Stand ist der erste Commit.

## Stufe 1: Extract sauber machen
- Konzepte: REST-API, OAuth2 (Access- und Refresh-Token), Pagination, Rate Limits (Standard grob 100 Read-Requests pro 15 Min und 1000 pro Tag, in der Strava-Doku prüfen), transiente Fehler vs. erschöpfte Quota, Retry mit Exponential Backoff, Secrets-Handling, Logging, Unit-Tests, Mocking.
- Aufgabe: Token-Handling kapseln (Refresh-Token-Rotation speichern), `logging` statt `print`. Bei 5xx und Netzfehlern mit Exponential Backoff wiederholen. Bei 429 bringt Backoff nichts, weil das Kontingent aufgebraucht ist: die Header `X-RateLimit-Usage` und `X-ReadRateLimit-Usage` auswerten und bis zum nächsten Fenster warten oder sauber abbrechen. pytest mit gemockter API (`responses` oder `respx`) und ruff fürs Linting. Strava hat keine Sandbox, jeder echte Testlauf kostet Rate-Limit.
- Fertig wenn: Tests mit gemockter API zeigen, dass das Skript einen 5xx und einen Netzfehler per Retry übersteht und bei einem 429 nicht weiter anfragt.

## Stufe 2: Raw Layer (Bronze)
- Konzepte: Data Lake, Immutable Raw Data, Ingestion-Timestamp, Partitionierung, Schema-on-Read.
- Aufgabe: Jede abgerufene Seite sofort unverändert unter `data/raw/activities/ingested_date=YYYY-MM-DD/` ablegen, mit Metadaten (Abrufzeit, Request-Parameter), statt am Ende alles auf einmal zu schreiben.
- Fertig wenn: Ein Abbruch mitten im Lauf verliert keine bereits geholten Seiten, und du kannst alle Downstream-Tabellen aus dem Raw Layer komplett neu aufbauen, ohne die API anzufragen.

## Stufe 3: Incremental Load
- Konzepte: Full vs. Incremental Load, Watermark/State, Late-Arriving Data, Lookback-Fenster, Updates und Deletes erkennen, Backfill.
- Aufgabe: Mit dem `after`-Parameter nur neue Aktivitäten holen, mit einem Lookback von z. B. 7 Tagen für nachträglich synchronisierte oder manuell eingetragene Aktivitäten. Den Watermark aus den Daten ableiten (`max(start_date)` im Raw Layer) statt separat speichern, dann können State und Daten nicht auseinanderlaufen. Zusätzlich ein wöchentlicher Full Refresh, der gelöschte Aktivitäten erkennt (sie tauchen einfach nicht mehr auf). Die Überlappung durch den Lookback ist gewollt und wird in Stufe 4 aufgelöst.
- Hinweis: Bei der Aktivitätenliste spart das kaum Requests (200 Aktivitäten pro Seite). Spürbar wird es erst bei den Streams in Stufe 7. Hier geht es um die Konzepte.
- Fertig wenn: Der zweite Lauf holt nur das Lookback-Fenster, eine nachträglich hochgeladene Aktivität mit älterem Startdatum wird gefunden und der Full Refresh liefert die IDs gelöschter Aktivitäten.

## Stufe 4: Warehouse laden
- Konzepte: OLAP vs. OLTP, Columnar Storage, Datentypen, Primary Keys, Upsert/MERGE, Deduplizierung, Idempotenz, Soft Deletes.
- Aufgabe: DuckDB als Warehouse. Raw-Daten in eine Staging-Tabelle laden und per MERGE von Hand in `activities` überführen (Key: Activity-ID). Pro ID gewinnt die neueste Version, gelöschte Aktivitäten bekommen ein `is_deleted`-Flag. Das manuelle MERGE ist bewusst eine Übung und wird in Stufe 5 durch dbt ersetzt.
- Fertig wenn: Erneutes Laden derselben Dateien ändert den Tabelleninhalt nicht, eine in Strava umbenannte Aktivität hat den neuen Namen und eine gelöschte ist markiert.

## Stufe 5: Transformation (ELT)
- Konzepte: ELT vs. ETL, Medallion-Layer (bronze/silver/gold), dbt (Models, Sources, Refs, Materialisierung, Incremental Models, Tests, Snapshots), Dimensionsmodellierung (Fakten- und Dimensionstabellen, Star Schema), Historisierung (SCD Typ 2), Window Functions, Zeitzonen und Einheiten.
- Aufgabe: dbt-duckdb liest direkt aus dem Raw Layer. Das MERGE aus Stufe 4 durch ein Incremental Model mit `unique_key` ersetzen. `stg_activities` (bereinigt, umbenannt, Einheiten umgerechnet, Wochen nach `start_date_local`), `fct_activities`, `dim_date`, `dim_sport_type` und ein Mart `weekly_training_volume` bauen. Zusätzlich `/athlete` in den Raw Layer laden (Schuhe und Räder mit Kilometerstand, Gewicht, FTP) und daraus `dim_gear` als dbt-Snapshot bauen. dbt-Tests (unique, not_null, accepted_values, relationships) gleich mitschreiben.
- Fertig wenn: `dbt build` läuft inklusive Tests durch, eine Abfrage liefert Wochenumfang, Pace-Trend und gleitenden Durchschnitt, und `dim_gear` zeigt die Historie eines Schuhs. Damit ist Meilenstein 1 erreicht.

## Stufe 6: Orchestrierung
- Konzepte: DAGs, Abhängigkeiten, Scheduling, Retries, Alerting, Backfills über Zeiträume, Assets (Dagster) vs. Tasks (Airflow).
- Aufgabe: extract → raw → dbt build als Dagster-Assets mit täglichem Schedule, die dbt-Models über `dagster-dbt`. Zum Vergleich vorher mit cron. Entscheiden, wo die Pipeline dauerhaft läuft: nur bei eingeschaltetem Laptop (cron verpasst Läufe im Ruhezustand, launchd holt sie nach), GitHub Actions mit externem Storage (z. B. MotherDuck) oder ein kleiner Server.
- Fertig wenn: Ein fehlgeschlagener Schritt wird automatisch wiederholt und die UI zeigt Laufhistorie und Abhängigkeiten.

## Stufe 7: Detaildaten und Skalierung
- Konzepte: N+1-Requests, Request-Budgeting, Priorisierung, Zeitreihen, Backfill-Strategien, Datenvolumen, Dateiformate (JSON vs. Parquet).
- Aufgabe: Activity-Streams (Herzfrequenz, Höhe, GPS pro Sekunde) für ausgewählte Aktivitäten laden. Das Rate-Limit zwingt zu einem Queue- und Budget-Ansatz, der über mehrere Tage nachlädt, angestoßen vom Schedule aus Stufe 6. Streams als JSON und als Parquet ablegen und Größe und Abfragegeschwindigkeit vergleichen. Erst bei diesen Datenmengen wird der Unterschied sichtbar.
- Fertig wenn: Ein Backfill über Hunderte Aktivitäten läuft, ohne das Limit zu reißen, und kann nach einem Abbruch fortgesetzt werden.

## Stufe 8: Datenqualität
- Konzepte: Schema-Validierung, Schema Drift, Data Contracts, Plausibilitätsprüfungen, Quarantäne für fehlerhafte Datensätze.
- Aufgabe: Pydantic- oder pandera-Schema für den API-Output, Plausibilitätsprüfungen (z. B. Pace, Distanz > 0) als dbt-Tests. Die Basis-Tests gibt es schon seit Stufe 5.
- Fertig wenn: Ein absichtlich kaputter Datensatz wird erkannt und blockiert die Pipeline oder landet in Quarantäne.

## Stufe 9: Software-Engineering-Praxis
- Konzepte: Projektstruktur, Packaging, Typen, Integrationstests, Fixtures, pre-commit, CI, Docker, Konfiguration per Umgebung.
- Aufgabe: Code in ein Paket (`src/strava_data/`) aufteilen, pre-commit mit ruff, GitHub Actions mit Lint und Tests, Dockerfile.
- Fertig wenn: Ein Push löst CI aus und die Pipeline läuft in einem Container reproduzierbar.

## Stufe 10: Serving und Betrieb
- Konzepte: Semantic Layer/Metriken, BI/Dashboards, Observability (Laufzeiten, Row Counts, Freshness), Lineage, Dokumentation.
- Aufgabe: Dashboard mit Streamlit oder Evidence, dbt-Docs für Lineage, einfache Freshness-Checks.
- Fertig wenn: Das Dashboard zeigt aktuelle Daten und du siehst sofort, wenn die Pipeline seit 2 Tagen nichts geladen hat.

## Stufe 11: Fortgeschritten (optional)
- Webhooks statt Polling (Strava Webhook Events), Event-getriebene Verarbeitung, Streaming-Grundlagen. Webhooks melden auch Updates und Deletes, die bisher der Full Refresh aus Stufe 3 abfängt.
- Cloud: Object Storage (S3), Postgres/BigQuery statt DuckDB, Infrastructure as Code.
- Mehr Quellen zusammenführen, z. B. Wetterdaten per Datum und Ort über die kostenlose historische API von Open-Meteo (ohne Key). Joins über Datenquellen, konforme Dimensionen, Entity Resolution. Lohnt sich schon direkt nach Meilenstein 1.

## Arbeitsweise
Pro Stufe: erst selbst versuchen, dann Review oder Hilfe. Nach jeder Stufe committen und in 3 Sätzen notieren, was du gelernt hast.

Datenschutz ab dem ersten Commit: `start_latlng`, `end_latlng` und `map.summary_polyline` verraten deinen Wohnort. Test-Fixtures synthetisch oder anonymisiert erzeugen, bei aufgezeichneten API-Antworten (z. B. VCR-Cassettes) auch Tokens entfernen, und ein öffentlich erreichbares Dashboard ohne Karten und Startpunkte bauen.
