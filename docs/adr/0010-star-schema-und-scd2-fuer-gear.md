# 0010: Star Schema mit historisiertem Gear

- Status: Akzeptiert
- Datum: 2026-10-18
- Stufe: 5

## Kontext
Die Auswertungen fragen nach Mengen über Zeit, Sportart und Ausrüstung: Wochenumfang, Pace-Trend, Kilometer pro Schuh. Für Gear und Athletenprofil (Gewicht, FTP) liefert Strava nur den aktuellen Stand. Fragen wie "Kilometerstand des Schuhs am Renntag" oder "W/kg zum Zeitpunkt der Aktivität" brauchen aber den damaligen Stand.

## Entscheidung
- Dimensionale Modellierung als Star Schema: Die Faktentabelle `fct_activities` (eine Zeile pro Aktivität) hat die Dimensionen `dim_date`, `dim_sport_type` und `dim_gear`.
- `dim_gear` wird mit einem dbt-Snapshot historisiert (SCD Typ 2).
- Gear und Profil kommen über `/athlete`. Dafür braucht der Token den Scope `profile:read_all`.

## Betrachtete Alternativen
- Eine breite Tabelle mit allem: einfacher abzufragen, aber man lernt keine Dimensionsmodellierung, und es wird unübersichtlich, sobald weitere Quellen dazukommen.
- SCD Typ 1 (überschreiben): einfacher, aber historische Fragen werden falsch beantwortet.
- Data Vault: flexibel bei vielen Quellen und häufigen Änderungen, für eine einzige Quelle aber zu viel Aufwand.

## Konsequenzen
- Auswertungen folgen immer demselben Muster: Fakten summieren, nach Dimension gruppieren.
- Der Snapshot kennt die Historie erst ab seinem ersten Lauf. Frühere Stände lassen sich nicht rekonstruieren.
- Mit nur einer Quelle wirkt das Star Schema etwas groß. Das ist als Lernziel gewollt und zahlt sich aus, sobald Wetterdaten dazukommen.
- Der Refresh Token muss für Stufe 5 einmal mit erweitertem Scope neu erzeugt werden.
