# strava-data

Holt alle eigenen Aktivitäten über die Strava-API und speichert sie als JSON in `data/activities.json`.

## Roadmap und Projektplanung

- [ROADMAP.md](ROADMAP.md): Lern-Roadmap mit allen Stufen
- [GitHub-Issues](https://github.com/FelixSchramm/strava-data/issues): ein Epic pro Stufe, die Umsetzungsschritte als Sub-Issues
- [Projektplan in Google Sheets](https://docs.google.com/spreadsheets/d/1UnMTlwxNuaTQoNBttb11oBDMxZ_hOs1dvuAChn1CpBo/edit): Übersicht mit Fortschritt je Stufe und Aufgabenliste mit Status, Aufwand und Terminen

## 1. Strava-App anlegen

1. Auf https://www.strava.com/settings/api eine App anlegen.
2. `Client ID` und `Client Secret` notieren.
3. Als `Authorization Callback Domain` `localhost` eintragen.

## 2. Refresh Token erzeugen (einmalig)

Im Browser diese URL öffnen (`DEINE_CLIENT_ID` ersetzen):

```
https://www.strava.com/oauth/authorize?client_id=DEINE_CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=read,activity:read_all
```

Nach dem Zustimmen landet der Browser auf `http://localhost/?code=...` (Seite selbst lädt nicht, das ist ok). Den Wert von `code` kopieren und dann im Terminal ausführen:

```bash
curl -X POST https://www.strava.com/oauth/token \
  -d client_id=DEINE_CLIENT_ID \
  -d client_secret=DEIN_CLIENT_SECRET \
  -d code=DER_CODE \
  -d grant_type=authorization_code
```

Aus der Antwort das Feld `refresh_token` nehmen.

## 3. Einrichten und ausführen

```bash
cp .env.example .env          # Werte eintragen
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python fetch_activities.py
```

Hinweis: Strava kann das Refresh Token bei jeder Erneuerung ändern. Wenn der Abruf mit `401` fehlschlägt, den Schritt 2 erneut durchführen und `.env` aktualisieren.
