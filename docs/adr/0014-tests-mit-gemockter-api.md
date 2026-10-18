# 0014: Tests mit gemockter API ab Stufe 1

- Status: Akzeptiert
- Datum: 2026-10-18
- Stufe: 1

## Kontext
Strava bietet keine Sandbox. Jeder Testlauf gegen die echte API verbraucht Rate-Limit und hängt von Netz und Konto ab. Die wichtigsten Fälle (429, 5xx, Netzabbruch mitten in der Pagination) lassen sich gegen die echte API kaum gezielt auslösen. Ursprünglich waren Tests erst für Stufe 9 geplant.

## Entscheidung
Ab Stufe 1 gibt es pytest-Tests, in denen die API mit `responses` gemockt wird. Linting mit ruff kommt ebenfalls ab Stufe 1. Packaging, CI und Docker bleiben in Stufe 9.

## Betrachtete Alternativen
- Tests erst in Stufe 9: weniger Aufwand am Anfang, aber das Fertig-Kriterium von Stufe 1 (übersteht 429 und Netzfehler) ließe sich nicht prüfen.
- Aufgezeichnete echte Antworten (VCR): realistischer, enthalten aber Tokens und Koordinaten (siehe [0015](0015-oeffentliches-repo-und-datenschutz.md)).

## Konsequenzen
- Die Fehlerbehandlung ist reproduzierbar testbar, ohne Kontingent und ohne Netz.
- Mocks können von der echten API abweichen. Ab und zu sollte man sie mit echten, anonymisierten Antworten abgleichen.
