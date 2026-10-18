# 0015: Öffentliches Repo mit Datenschutzregeln

- Status: Akzeptiert
- Datum: 2026-10-18
- Stufe: alle

## Kontext
Das Repository ist als Portfolio öffentlich auf GitHub. Strava-Daten enthalten sensible Informationen: `start_latlng`, `end_latlng` und `map.summary_polyline` zeigen, wo du wohnst und regelmäßig trainierst. Dazu kommen Client Secret und Tokens. Öffentliche Repos werden automatisiert nach Secrets durchsucht, und was einmal gepusht ist, bleibt in der Git-Historie.

## Entscheidung
- Secrets stehen nur in `.env` (in `.gitignore`), im Repo liegt nur `.env.example` mit leeren Werten. In der CI kommen sie aus GitHub Secrets.
- `data/` steht in `.gitignore`, echte Daten kommen nie ins Repo.
- Test-Fixtures sind synthetisch oder anonymisiert, ohne echte Koordinaten und Tokens.
- Ein öffentlich erreichbares Dashboard zeigt keine Karten und Startpunkte.
- An externe Dienste wie Open-Meteo gehen Koordinaten nur gerundet.

## Betrachtete Alternativen
- Privates Repo: weniger Risiko, aber kein Portfolio. Die Regeln wären trotzdem sinnvoll.

## Konsequenzen
- Das Repo kann öffentlich bleiben, ohne den Wohnort preiszugeben.
- Fixtures müssen von Hand gebaut oder bereinigt werden, statt echte Antworten zu kopieren.
- Ein versehentlich gepushtes Secret muss sofort neu erzeugt werden. Es nur aus der Historie zu löschen, reicht nicht.
