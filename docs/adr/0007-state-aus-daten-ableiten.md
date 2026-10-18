# 0007: State aus den Daten ableiten

- Status: Akzeptiert
- Datum: 2026-10-18
- Stufe: 3, 7

## Kontext
Der Incremental Load braucht einen Watermark, der Streams-Backfill eine Liste der noch fehlenden Aktivitäten. Wird dieser State separat gespeichert, kann er von den Daten abweichen: Stürzt ein Lauf ab, nachdem die Daten geschrieben, aber bevor der State aktualisiert wurde, stimmen beide nicht mehr überein.

## Entscheidung
State wird nicht separat gespeichert, sondern bei jedem Lauf aus den vorhandenen Daten berechnet:
- Watermark = `max(start_date)` im Raw Layer.
- Backfill-Queue = alle nicht gelöschten Aktivitäten ohne Streams-Datei.

## Betrachtete Alternativen
- State-Datei (z. B. `state.json`): einfach und schnell, aber es gibt zwei Wahrheiten, die auseinanderlaufen können.
- State-Tabelle in DuckDB, die in derselben Transaktion wie die Daten aktualisiert wird: konsistent, koppelt den Extract aber an das Warehouse.

## Konsequenzen
- Es gibt nur eine Wahrheit, und Abstürze können den State nicht verfälschen.
- Jeder Lauf liest einmal den Raw Layer. Bei dieser Datenmenge ist das vernachlässigbar.
- Wer Rohdateien löscht, ändert damit auch den State. Das ist gewollt, man muss es aber wissen.
