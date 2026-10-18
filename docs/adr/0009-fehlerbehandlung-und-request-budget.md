# 0009: Fehlerbehandlung nach Fehlerart und Request-Budget

- Status: Akzeptiert
- Datum: 2026-10-18
- Stufe: 1, 7

## Kontext
Strava begrenzt die Anfragen pro App in einem 15-Minuten- und einem Tagesfenster. Lese-Anfragen haben ein eigenes, niedrigeres Limit (grob 100 pro 15 Minuten und 1.000 pro Tag, aktuellen Stand in der Doku prüfen). Fehler haben unterschiedliche Ursachen: kurze Aussetzer (Netzfehler, 5xx), ein erschöpftes Kontingent (429) und dauerhafte Fehler (400, 401, 404). Der Streams-Backfill in Stufe 7 braucht mehr Anfragen, als an einem Tag erlaubt sind.

## Entscheidung
- Netzfehler und 5xx: Retry mit Exponential Backoff und Jitter, mit begrenzter Anzahl Versuche.
- 429: kein Backoff, sondern bis zum nächsten Fenster warten oder sauber abbrechen und später fortsetzen.
- 400, 401, 404: nicht wiederholen, sondern den Fehler melden.
- Verbrauch und Limit kommen aus den Antwort-Headern (`X-ReadRateLimit-Usage`, `X-ReadRateLimit-Limit`), nicht aus fest eingebauten Zahlen.
- Ein fester Teil des Tagesbudgets ist für den täglichen Sync reserviert, der Rest geht an den Backfill.

## Betrachtete Alternativen
- Alle Fehler gleich mit Backoff behandeln: einfach, verbrennt bei einem 429 aber weitere Anfragen.
- Feste Limits im Code: bricht, wenn Strava die Limits ändert, und zählt andere Läufe derselben App nicht mit.

## Konsequenzen
- Die Pipeline reißt das Limit nicht, und neue Aktivitäten kommen auch während eines laufenden Backfills an.
- Der Extract enthält mehr Logik, die mit gemockten Antworten getestet werden muss ([0014](0014-tests-mit-gemockter-api.md)).
