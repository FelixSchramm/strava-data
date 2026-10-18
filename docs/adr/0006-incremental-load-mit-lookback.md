# 0006: Incremental Load mit Lookback und wöchentlichem Full Refresh

- Status: Akzeptiert
- Datum: 2026-10-18
- Stufe: 3

## Kontext
Strava filtert die Aktivitätenliste nur über das Startdatum (`after`, `before`), ein Änderungsdatum enthält sie nicht. Ein einfacher Watermark auf `start_date` verpasst deshalb drei Fälle:
- Aktivitäten, die erst Tage später hochgeladen werden, etwa weil die Uhr spät synchronisiert.
- Nachträgliche Änderungen an Titel, Sporttyp oder Gear.
- Gelöschte Aktivitäten.

## Entscheidung
- Täglich inkrementell mit `after` = Watermark minus 7 Tage (Lookback).
- Einmal pro Woche ein Full Refresh, der alle Aktivitäten holt, um Änderungen und Löschungen zu erkennen.

## Betrachtete Alternativen
- Nur Incremental Load: verpasst Änderungen und Löschungen dauerhaft.
- Immer Full Load: für die Liste machbar, weil es nur wenige Anfragen sind. Man lernt das Konzept aber nicht, und für Detaildaten funktioniert es nicht.
- Webhooks: würden Änderungen und Löschungen sofort melden, brauchen aber einen öffentlich erreichbaren Server. Vorgemerkt für Stufe 11.

## Konsequenzen
- Spät hochgeladene Aktivitäten (bis 7 Tage) werden täglich erkannt, Änderungen und Löschungen spätestens nach einer Woche.
- Bekannte Aktivitäten werden mehrfach geholt, deshalb ist Deduplizierung Pflicht ([0008](0008-idempotenz-merge-soft-deletes.md)).
- Änderungen an Aktivitäten außerhalb des Lookback-Fensters sind bis zum nächsten Full Refresh bis zu einer Woche veraltet.
