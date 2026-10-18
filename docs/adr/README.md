# Architecture Decision Records

Ein ADR (Architecture Decision Record) hält eine Architekturentscheidung fest: Was war die Ausgangslage, was wurde entschieden, welche Alternativen gab es und was folgt daraus. Ein ADR pro Entscheidung, fortlaufend nummeriert.

## Wann ein ADR?
Wenn eine Entscheidung die Struktur des Projekts prägt und sich nicht mit einem kleinen Commit rückgängig machen lässt: Werkzeugwahl, Datenhaltung, Ladestrategie, Datenmodell. Nicht für Kleinigkeiten wie Variablennamen.

## Regeln
- Neue ADRs mit [template.md](template.md) anlegen, mit der nächsten freien Nummer.
- Status: Vorgeschlagen → Akzeptiert → später eventuell Abgelöst oder Verworfen.
- Akzeptierte ADRs werden nicht umgeschrieben. Ändert sich eine Entscheidung, entsteht ein neues ADR, und das alte bekommt den Status "Abgelöst durch NNNN".

## Übersicht

| Nr | Entscheidung | Stufe | Status |
|---|---|---|---|
| [0001](0001-adrs-verwenden.md) | Architekturentscheidungen als ADRs festhalten | alle | Akzeptiert |
| [0002](0002-lokaler-stack.md) | Lokaler, kostenloser Stack | alle | Akzeptiert |
| [0003](0003-duckdb-als-warehouse.md) | DuckDB als Warehouse | 4 | Akzeptiert |
| [0004](0004-elt-mit-medallion.md) | ELT mit Medallion-Schichten | 2, 5 | Akzeptiert |
| [0005](0005-raw-layer-unveraenderlich.md) | Unveränderlicher Raw Layer als JSON | 2 | Akzeptiert |
| [0006](0006-incremental-load-mit-lookback.md) | Incremental Load mit Lookback und wöchentlichem Full Refresh | 3 | Akzeptiert |
| [0007](0007-state-aus-daten-ableiten.md) | State aus den Daten ableiten | 3, 7 | Akzeptiert |
| [0008](0008-idempotenz-merge-soft-deletes.md) | Idempotenz über MERGE und Soft Deletes | 4 | Akzeptiert |
| [0009](0009-fehlerbehandlung-und-request-budget.md) | Fehlerbehandlung nach Fehlerart und Request-Budget | 1, 7 | Akzeptiert |
| [0010](0010-star-schema-und-scd2-fuer-gear.md) | Star Schema mit historisiertem Gear | 5 | Akzeptiert |
| [0011](0011-merge-erst-von-hand-dann-dbt.md) | MERGE erst von Hand, dann mit dbt | 4, 5 | Akzeptiert |
| [0012](0012-dagster-als-orchestrator.md) | Dagster als Orchestrator | 6 | Akzeptiert |
| [0013](0013-mehrstufige-datenqualitaet.md) | Mehrstufige Datenqualität | 1, 5, 8 | Akzeptiert |
| [0014](0014-tests-mit-gemockter-api.md) | Tests mit gemockter API ab Stufe 1 | 1 | Akzeptiert |
| [0015](0015-oeffentliches-repo-und-datenschutz.md) | Öffentliches Repo mit Datenschutzregeln | alle | Akzeptiert |

## Offene Entscheidungen
Diese Fragen sind noch nicht entschieden. Gute Übung: Das ADR schreibst du selbst, wenn du die Entscheidung triffst.

| Frage | Optionen | Spätestens |
|---|---|---|
| Wo wird der rotierte Refresh Token gespeichert? | Datei in `.gitignore`, macOS-Schlüsselbund, GitHub Secret | Stufe 1 |
| Wo läuft die Pipeline dauerhaft? | Laptop mit launchd, GitHub Actions mit MotherDuck, kleiner Server | Stufe 6 |
| Pydantic oder pandera für die Schema-Validierung? | Pydantic (pro Datensatz), pandera (pro DataFrame) | Stufe 8 |
| Wie greifen Pipeline und Dashboard gleichzeitig auf DuckDB zu? | Read-only-Kopie fürs Dashboard, MotherDuck, Zeitfenster | Stufe 10 |
| Streamlit oder Evidence fürs Dashboard? | Streamlit (Python), Evidence (SQL und Markdown) | Stufe 10 |

## Mehr
- [Michael Nygard: Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions), der Artikel, der ADRs bekannt gemacht hat
- [adr.github.io](https://adr.github.io/), Vorlagen und Werkzeuge, darunter das ausführlichere Format [MADR](https://adr.github.io/madr/)
