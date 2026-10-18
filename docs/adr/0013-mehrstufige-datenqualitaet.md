# 0013: Mehrstufige Datenqualität

- Status: Akzeptiert
- Datum: 2026-10-18
- Stufe: 1, 5, 8

## Kontext
Fehlerhafte Daten können an mehreren Stellen entstehen: unerwartete API-Antworten und Schema Drift (bei Strava wurde z. B. `type` durch `sport_type` abgelöst), Fehler in Transformationen und inhaltlich unplausible Werte wie GPS-Aussetzer. Je später ein Fehler auffällt, desto mehr Tabellen und Auswertungen sind schon betroffen.

## Entscheidung
- Beim Extract: Schema-Validierung jedes Datensatzes, mit Pydantic oder pandera (noch offen).
- Ab Stufe 5: dbt-Tests (unique, not_null, accepted_values, relationships) auf Staging und Marts, als Teil von `dbt build`.
- Ab Stufe 8: Data Contracts für die Staging-Models, Plausibilitätsprüfungen und Quarantäne.
- Schwere Fehler stoppen die Pipeline. Einzelne fehlerhafte Datensätze landen mit Begründung in Quarantäne, statt gelöscht zu werden.

## Betrachtete Alternativen
- Nur am Ende prüfen (dbt-Tests auf den Marts): weniger Aufwand, aber Fehler fallen spät auf.
- Fehlerhafte Datensätze verwerfen: einfach, aber es gehen Daten ohne Spur verloren.

## Konsequenzen
- Fehler fallen nah an ihrer Ursache auf, und gute Daten fließen weiter.
- Die Quarantäne muss regelmäßig angeschaut werden, sonst ist sie nur ein Mülleimer.
