# 0004: ELT mit Medallion-Schichten

- Status: Akzeptiert
- Datum: 2026-10-18
- Stufe: 2, 5

## Kontext
Die Strava-API erlaubt grob 1.000 Lese-Anfragen pro Tag. Beim Lernen werden sich die Transformationen oft ändern und Fehler enthalten. Für jede Korrektur neu von der API zu laden, wäre langsam und würde das Kontingent verbrauchen.

## Entscheidung
ELT statt ETL: Rohdaten werden unverändert gespeichert und erst danach mit SQL (dbt) transformiert. Die Daten durchlaufen drei Schichten: raw (Bronze), staging (Silver) und marts (Gold). Jede Schicht liest nur aus der vorigen.

## Betrachtete Alternativen
- ETL: in Python transformieren und nur das Ergebnis speichern. Braucht weniger Speicher, aber jeder Fehler in der Transformation erfordert einen neuen API-Abruf.
- Eine einzige Schicht: einfacher, aber Rohdaten, Bereinigung und Fachlogik vermischen sich.

## Konsequenzen
- Alle Tabellen lassen sich aus dem Raw Layer neu bauen, ohne die API anzufragen.
- Die Daten liegen mehrfach vor.
- Für die kleine Datenmenge sind drei Schichten mehr als nötig. Das ist als Lernziel gewollt.
