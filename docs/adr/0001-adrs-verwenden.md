# 0001: Architekturentscheidungen als ADRs festhalten

- Status: Akzeptiert
- Datum: 2026-10-18
- Stufe: alle

## Kontext
Das Projekt ist ein Lernprojekt, das über viele Stufen wächst. Viele Entscheidungen (Werkzeuge, Datenhaltung, Ladestrategie) sind bewusst getroffen, manche wegen eines Lernziels statt aus rein technischen Gründen. Ohne Notiz ist in ein paar Monaten nicht mehr nachvollziehbar, warum etwas so ist und ob die Gründe noch gelten.

## Entscheidung
Jede Entscheidung, die die Struktur des Projekts prägt und sich nicht billig rückgängig machen lässt, bekommt ein ADR in `docs/adr/`, nummeriert und nach der Vorlage [template.md](template.md). Akzeptierte ADRs werden nicht umgeschrieben. Ändert sich eine Entscheidung, entsteht ein neues ADR, und das alte bekommt den Status "Abgelöst durch NNNN".

## Betrachtete Alternativen
- Entscheidungen nur in Commit-Messages: verstreut und schwer auffindbar.
- Ein großes Architektur-Dokument: veraltet schnell, und die Historie der Entscheidungen geht verloren.
- Nichts aufschreiben: am einfachsten, führt aber genau zum Problem aus dem Kontext.

## Konsequenzen
- Die Gründe bleiben nachvollziehbar, auch für Reviews und für dich selbst in einem halben Jahr.
- Pro Entscheidung etwas Schreibaufwand.
- Die ADRs 0002 bis 0015 wurden am 2026-10-18 nachträglich aus Roadmap und Review dokumentiert. Ab jetzt entstehen ADRs zusammen mit der Entscheidung.
