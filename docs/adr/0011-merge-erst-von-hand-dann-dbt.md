# 0011: MERGE erst von Hand, dann mit dbt

- Status: Akzeptiert
- Datum: 2026-10-18
- Stufe: 4, 5

## Kontext
dbt kann das Laden per MERGE über Incremental Models selbst übernehmen. Wer nur dbt nutzt, sieht aber nicht, welches SQL dahintersteckt und welche Probleme es löst, etwa die Deduplizierung vor dem MERGE oder das Verhalten bei mehreren Treffern pro Key.

## Entscheidung
Das ist eine Lernentscheidung: In Stufe 4 wird der MERGE von Hand in SQL geschrieben. In Stufe 5 ersetzt ihn ein dbt-Incremental-Model mit `unique_key`, das direkt aus dem Raw Layer liest.

## Betrachtete Alternativen
- Direkt mit dbt starten: weniger Arbeit, und so würde man es in einem echten Projekt machen.
- Beim handgeschriebenen MERGE bleiben: volle Kontrolle, aber kein Abhängigkeitsgraph, keine Tests und keine Lineage.

## Konsequenzen
- Der Code aus Stufe 4 wird in Stufe 5 bewusst ersetzt.
- Du verstehst, was dbt erzeugt, und kannst das generierte SQL im Ordner `target/` nachlesen.
