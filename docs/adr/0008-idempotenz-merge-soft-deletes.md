# 0008: Idempotenz über MERGE und Soft Deletes

- Status: Akzeptiert
- Datum: 2026-10-18
- Stufe: 4

## Kontext
Durch Lookback und Full Refresh ([0006](0006-incremental-load-mit-lookback.md)) liegt dieselbe Aktivität mehrfach im Raw Layer, eventuell in verschiedenen Versionen. Läufe sollen sich nach einem Abbruch einfach wiederholen lassen, ohne Duplikate zu erzeugen. Löschungen erkennt nur der Full Refresh, und ein fehlerhafter Full Refresh darf nicht die Hälfte der Daten löschen.

## Entscheidung
- Primary Key ist die Activity-ID von Strava (`BIGINT`).
- Pro ID gewinnt die Version mit dem neuesten Ingestion-Timestamp.
- Geladen wird per `MERGE` (Upsert), nicht per `INSERT`.
- Gelöschte Aktivitäten werden mit `is_deleted` markiert statt gelöscht (Soft Delete).
- Löschungen werden nur aus einem vollständig abgeschlossenen Full Refresh abgeleitet, also erst, wenn alle Seiten bis zur leeren Seite geholt wurden.

## Betrachtete Alternativen
- Die Tabelle bei jedem Lauf komplett neu bauen: ebenfalls idempotent und einfacher, aber man lernt MERGE nicht, und es skaliert schlecht.
- Hartes `DELETE`: sauberer Datenbestand, aber ein kaputter Full Refresh löscht Daten unwiderruflich.

## Konsequenzen
- Jeder Lauf kann beliebig oft wiederholt werden, das Ergebnis bleibt gleich.
- Löschungen sind nachvollziehbar. Fälschlich markierte Aktivitäten setzt der nächste vollständige Full Refresh zurück.
- Jede Abfrage muss gelöschte Aktivitäten ausfiltern. Das passiert einmal zentral im Staging-Model.
