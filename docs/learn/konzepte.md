# Konzepte zum Nachschlagen

Alle Konzepte aus der [Roadmap](../../ROADMAP.md), sortiert nach Stufe. Pro Konzept steht hier, was es ist (auch für Einsteiger), eine genauere Erklärung mit Bezug zu diesem Projekt, wo es hilft ein Beispiel und ein Link zum Weiterlesen.

Die Links führen meist auf englische Originaldokumentation, weil die am aktuellsten ist.

## Inhalt
- [Stufe 1: Extract sauber machen](#stufe-1-extract-sauber-machen)
- [Stufe 2: Raw Layer (Bronze)](#stufe-2-raw-layer-bronze)
- [Stufe 3: Incremental Load](#stufe-3-incremental-load)
- [Stufe 4: Warehouse laden](#stufe-4-warehouse-laden)
- [Stufe 5: Transformation (ELT)](#stufe-5-transformation-elt)
- [Stufe 6: Orchestrierung](#stufe-6-orchestrierung)
- [Stufe 7: Detaildaten und Skalierung](#stufe-7-detaildaten-und-skalierung)
- [Stufe 8: Datenqualität](#stufe-8-datenqualität)
- [Stufe 9: Software-Engineering-Praxis](#stufe-9-software-engineering-praxis)
- [Stufe 10: Serving und Betrieb](#stufe-10-serving-und-betrieb)
- [Stufe 11: Fortgeschritten](#stufe-11-fortgeschritten)

---

## Stufe 1: Extract sauber machen

### REST-API
**Was ist das?** Eine Art, wie ein Programm einem Server über das Internet Fragen stellt. Du rufst eine Adresse (URL) auf und bekommst Daten zurück, meist als JSON.

**Genauer:** REST organisiert alles als Ressourcen mit eigener URL, etwa `/athlete/activities` für deine Aktivitäten. Was du tun willst, sagt die HTTP-Methode: `GET` liest, `POST` legt an, `PUT` ändert, `DELETE` löscht. Ob es geklappt hat, sagt der Statuscode: `200` ok, `401` nicht angemeldet, `429` zu viele Anfragen, `5xx` Fehler beim Server.

**Beispiel:**
```bash
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://www.strava.com/api/v3/athlete/activities?per_page=5"
```

**Mehr:** [MDN: REST](https://developer.mozilla.org/en-US/docs/Glossary/REST), [Strava: API Reference](https://developers.strava.com/docs/reference/)

### OAuth2, Access Token und Refresh Token
**Was ist das?** Ein Verfahren, mit dem du einer App erlaubst, auf deine Daten zuzugreifen, ohne ihr dein Passwort zu geben. Stattdessen bekommt die App Tokens, eine Art zeitlich begrenzter Schlüssel.

**Genauer:** Der Access Token öffnet die API, läuft bei Strava aber nach 6 Stunden ab. Mit dem langlebigen Refresh Token holst du dir einen neuen Access Token. Strava kann dabei auch einen neuen Refresh Token zurückgeben, den du dann speichern musst, weil der alte ungültig werden kann. Das ist die Refresh-Token-Rotation aus Stufe 1 und der Grund für den 401-Hinweis in der README. Was die App lesen darf, regeln Scopes wie `activity:read_all`.

**Beispiel:** Antwort von `POST /oauth/token`:
```json
{"access_token": "a1b2...", "expires_at": 1760800000, "refresh_token": "c3d4..."}
```

**Mehr:** [Strava: Authentication](https://developers.strava.com/docs/authentication/), [oauth.net: Refresh Tokens](https://oauth.net/2/refresh-tokens/)

### Pagination
**Was ist das?** Große Ergebnislisten liefert eine API nicht auf einmal, sondern in Seiten, wie ein Buch.

**Genauer:** Bei Strava steuerst du das mit `page` und `per_page` (bei Aktivitäten maximal 200). Du fragst Seite für Seite ab, bis eine leere Seite kommt. Andere APIs nutzen statt Seitennummern einen Cursor ("gib mir alles nach Eintrag X"). Das ist stabiler, wenn sich die Daten während des Abrufs ändern.

**Beispiel:** Die `while True`-Schleife in `fetch_activities.py` ist genau das.

**Mehr:** [Strava: Pagination](https://developers.strava.com/docs/#pagination)

### Rate Limits
**Was ist das?** Eine Obergrenze, wie viele Anfragen du in einem Zeitraum stellen darfst. Sie schützt den Server vor Überlastung.

**Genauer:** Strava zählt pro App in zwei Fenstern, 15 Minuten und einem Tag, und hat für Lese-Anfragen ein eigenes, niedrigeres Limit. Die 15-Minuten-Fenster beginnen zur vollen Viertelstunde, der Tag um Mitternacht UTC. Jede Antwort enthält Header mit Limit und aktuellem Verbrauch, jeweils als `15min,Tag`. Wer drüber liegt, bekommt `429 Too Many Requests`.

**Beispiel:**
```python
used_15min, used_day = map(int, response.headers["X-ReadRateLimit-Usage"].split(","))
limit_15min, limit_day = map(int, response.headers["X-ReadRateLimit-Limit"].split(","))
```

**Mehr:** [Strava: Rate Limits](https://developers.strava.com/docs/rate-limits/)

### Transiente Fehler vs. erschöpfte Quota
**Was ist das?** Zwei Arten von Fehlern, die gleich aussehen ("hat nicht geklappt"), aber unterschiedlich behandelt werden müssen.

**Genauer:** Ein transienter Fehler ist ein kurzer Aussetzer: Netz weg, Server überlastet (`500`, `502`, `503`), Timeout. Ein zweiter Versuch Sekunden später klappt oft. Eine erschöpfte Quota (`429`) verschwindet dagegen erst, wenn das Rate-Limit-Fenster vorbei ist, bei Strava also nach bis zu 15 Minuten oder erst am nächsten Tag. Schnelles Wiederholen verbraucht dann nur weitere Anfragen. Dazu kommen dauerhafte Fehler wie `401` oder `404`, bei denen Wiederholen nie hilft.

**Beispiel:**

| Status | Art | Reaktion |
|---|---|---|
| Netzfehler, `5xx` | transient | Retry mit Backoff |
| `429` | Quota erschöpft | bis zum nächsten Fenster warten oder abbrechen |
| `400`, `401`, `404` | dauerhaft | nicht wiederholen, Fehler melden |

**Mehr:** [AWS Builders' Library: Timeouts, retries, and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)

### Retry mit Exponential Backoff
**Was ist das?** Bei einem Fehler nicht sofort aufgeben, sondern es nochmal versuchen und dabei jedes Mal etwas länger warten.

**Genauer:** Die Wartezeit verdoppelt sich: 1, 2, 4, 8 Sekunden. So bekommt ein überlasteter Server Luft. Dazu kommt meist ein zufälliger Anteil (Jitter), damit nicht viele Clients gleichzeitig wieder anklopfen. Nach einer Höchstzahl an Versuchen gibst du auf und meldest den Fehler. Die Bibliothek `tenacity` nimmt dir das ab, einmal selbst schreiben lohnt sich aber zum Verstehen.

**Beispiel:**
```python
for attempt in range(5):
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code < 500:
            break
    except requests.ConnectionError:
        pass
    time.sleep(2**attempt + random.random())  # 1, 2, 4, 8, 16 s plus Jitter
else:
    raise RuntimeError(f"{url} nach 5 Versuchen nicht erreichbar")
```

**Mehr:** [tenacity](https://tenacity.readthedocs.io/)

### Secrets-Handling
**Was ist das?** Der sichere Umgang mit Zugangsdaten wie Passwörtern, API-Keys und Tokens.

**Genauer:** Secrets gehören nie in den Code und nie ins Git-Repo, auch nicht kurz: Was einmal gepusht ist, bleibt in der Historie, und öffentliche Repos werden automatisiert nach Tokens durchsucht. Üblich ist, sie als Umgebungsvariablen zu übergeben, lokal über eine `.env`-Datei, die in `.gitignore` steht. Im Repo liegt nur eine `.env.example` mit leeren Werten. In GitHub Actions nimmst du später Repository Secrets.

**Beispiel:** `.env` (nicht committen) → `load_dotenv()` → `os.environ["STRAVA_CLIENT_SECRET"]`. Genau so macht es `fetch_activities.py`.

**Mehr:** [The Twelve-Factor App: Config](https://12factor.net/config), [GitHub: Using secrets in GitHub Actions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)

### Logging
**Was ist das?** Das Programm schreibt mit, was es tut, damit du später nachvollziehen kannst, was passiert ist.

**Genauer:** Anders als bei `print` hat jede Log-Meldung eine Stufe (`DEBUG`, `INFO`, `WARNING`, `ERROR`), einen Zeitstempel und eine Quelle. Du steuerst, welche Stufen ausgegeben werden und wohin (Konsole, Datei). Wenn die Pipeline nachts allein läuft, ist das Log oft die einzige Spur. Tokens und Secrets gehören nie ins Log.

**Beispiel:**
```python
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)
log.info("Seite %s: %s Aktivitäten", page, len(batch))
```

**Mehr:** [Python: Logging HOWTO](https://docs.python.org/3/howto/logging.html)

### Unit-Tests
**Was ist das?** Kleine automatische Prüfungen, ob ein einzelnes Stück Code das tut, was es soll.

**Genauer:** Ein Unit-Test ruft eine Funktion mit bekannten Eingaben auf und prüft das Ergebnis. Er läuft in Millisekunden und braucht weder Netz noch echte Daten. Damit kannst du Code umbauen, ohne Angst, etwas kaputtzumachen. In Python ist `pytest` der Standard: Funktionen, die mit `test_` beginnen, werden automatisch gefunden.

**Beispiel:**
```python
import pytest

def test_pace_aus_geschwindigkeit():
    assert pace_min_per_km(speed_m_s=3.333) == pytest.approx(5.0, abs=0.01)
```

**Mehr:** [pytest: Get Started](https://docs.pytest.org/en/stable/getting-started.html)

### Mocking
**Was ist das?** Im Test wird ein echtes System, hier die Strava-API, durch eine Attrappe ersetzt, die vorher festgelegte Antworten liefert.

**Genauer:** So testest du Fälle, die du in echt kaum auslösen kannst: einen `429`, einen `500` oder einen Netzabbruch auf Seite 3. Die Tests verbrauchen kein Rate-Limit und laufen auch ohne Internet. `responses` ersetzt Aufrufe der Bibliothek `requests`, `respx` macht dasselbe für `httpx`. Damit der Test nicht wirklich wartet, machst du die Wartezeit im Backoff per Parameter abschaltbar.

**Beispiel:**
```python
import responses

URL = "https://www.strava.com/api/v3/athlete/activities"

@responses.activate
def test_retry_nach_serverfehler():
    responses.get(URL, status=500)                 # 1. Aufruf: Serverfehler
    responses.get(URL, json=[{"id": 1}])           # 2. Aufruf: Seite 1
    responses.get(URL, json=[])                    # 3. Aufruf: leere Seite, fertig

    activities = fetch_all_activities("fake-token")

    assert [a["id"] for a in activities] == [1]
```

**Mehr:** [responses](https://github.com/getsentry/responses), [respx](https://lundberg.github.io/respx/)

---

## Stufe 2: Raw Layer (Bronze)

### Data Lake
**Was ist das?** Ein großer Ablageort für Rohdaten in ihrer ursprünglichen Form, meist einfach Dateien in Ordnern.

**Genauer:** Im Gegensatz zum Data Warehouse (Stufe 4) wird beim Data Lake nichts vorher in Tabellen gepresst. Alles wird so abgelegt, wie es kommt, und später bei Bedarf verarbeitet. In der Cloud ist das Object Storage wie S3, bei dir der Ordner `data/raw/`. Der Vorteil: Rohdaten sind die Wahrheit, aus der du alles neu bauen kannst. Der Nachteil: Ohne Ordnung wird daraus schnell ein "Data Swamp".

**Mehr:** [Wikipedia: Data Lake](https://de.wikipedia.org/wiki/Data_Lake)

### Immutable Raw Data
**Was ist das?** Unveränderliche Rohdaten: Was einmal abgelegt ist, wird nie mehr überschrieben oder bearbeitet.

**Genauer:** Neue Abrufe kommen als neue Dateien dazu. Hat eine spätere Transformation einen Fehler, korrigierst du die Transformation und baust neu, die Rohdaten bleiben unangetastet. Du kannst also jederzeit beantworten: "Was hat die API am 3. Oktober geliefert?" Das ist der Kern des Fertig-Kriteriums von Stufe 2.

**Beispiel:**
```
data/raw/activities/
├── ingested_date=2026-10-17/run_20261017T061500Z_page_001.json
└── ingested_date=2026-10-18/run_20261018T061500Z_page_001.json
```

**Mehr:** [Maxime Beauchemin: Functional Data Engineering](https://maximebeauchemin.medium.com/functional-data-engineering-a-modern-paradigm-for-batch-data-processing-2327ec32c42a)

### Ingestion-Timestamp
**Was ist das?** Der Zeitpunkt, zu dem ein Datensatz bei dir angekommen ist, im Unterschied zum Zeitpunkt, zu dem das Ereignis passiert ist.

**Genauer:** Eine Aktivität hat ein `start_date` (Event Time: wann du gelaufen bist) und bei dir ein `ingested_at` (Ingestion Time: wann du sie abgerufen hast). Mit `ingested_at` findest du die neueste Version eines Datensatzes (Stufe 4), prüfst Freshness (Stufe 10) und weißt, welcher Lauf welche Daten gebracht hat.

**Beispiel:**
```json
{"ingested_at": "2026-10-18T06:15:03Z", "request": {"page": 1, "per_page": 200}, "data": [...]}
```

**Mehr:** [Tyler Akidau: Streaming 101 (Abschnitt Event Time vs. Processing Time)](https://www.oreilly.com/radar/the-world-beyond-batch-streaming-101/)

### Partitionierung
**Was ist das?** Daten werden nach einem Merkmal in getrennte Ordner aufgeteilt, z. B. nach Datum.

**Genauer:** Wer nur die Daten vom 18. Oktober braucht, liest nur einen Ordner statt alles. Die Schreibweise `ordnername=wert` heißt Hive-Partitionierung. DuckDB, Spark und Co. erkennen sie automatisch und machen daraus eine Spalte. Bei kleinen Datenmengen wie deinen Aktivitäten bringt das kaum Tempo, du lernst aber die Konvention. Zu feine Partitionen erzeugen viele winzige Dateien (Small Files Problem), was eher bremst.

**Beispiel:**
```sql
select ingested_date, count(*) as dateien
from read_json_auto('data/raw/activities/*/*.json', hive_partitioning = true)
group by ingested_date;
```

**Mehr:** [DuckDB: Hive Partitioning](https://duckdb.org/docs/stable/data/partitioning/hive_partitioning)

### Schema-on-Read
**Was ist das?** Die Struktur der Daten (welche Spalten, welche Typen) wird erst beim Lesen festgelegt, nicht beim Speichern.

**Genauer:** Das Gegenteil ist Schema-on-Write: Eine Datenbanktabelle lehnt beim Einfügen alles ab, was nicht passt. Im Raw Layer speicherst du das JSON so, wie es kommt, auch wenn Strava morgen ein Feld ergänzt. Erst beim Lesen (DuckDB, dbt) entscheidest du, welche Felder du wie interpretierst. Vorteil: Beim Ablegen geht nichts verloren. Nachteil: Fehler fallen erst später auf, deshalb Stufe 8.

**Mehr:** [DuckDB: JSON lesen und Schema erkennen](https://duckdb.org/docs/stable/data/json/overview)

---

## Stufe 3: Incremental Load

### Full Load vs. Incremental Load
**Was ist das?** Full Load heißt, jedes Mal alles neu zu holen. Incremental Load heißt, nur das zu holen, was seit dem letzten Mal dazugekommen ist.

**Genauer:** Full Load ist einfach und robust, wird aber teuer, wenn die Datenmenge wächst. Incremental Load ist sparsam, braucht aber ein Gedächtnis (State) und hat Tücken: verspätete Daten, Änderungen, Löschungen. In der Praxis kombiniert man oft beides: täglich inkrementell, ab und zu ein Full Refresh zum Abgleich.

**Beispiel:**
```python
params = {"after": watermark - LOOKBACK_SECONDS, "page": page, "per_page": 200}
```

**Mehr:** [dbt: Incremental models](https://docs.getdbt.com/docs/build/incremental-models)

### Watermark und State
**Was ist das?** Ein Watermark ist eine Markierung "bis hierhin habe ich schon alles", z. B. das neueste Startdatum, das du kennst. State ist alles, was sich die Pipeline zwischen zwei Läufen merken muss.

**Genauer:** Beim nächsten Lauf fragst du nur Daten nach dem Watermark ab. Den Watermark kannst du separat speichern (Datei, Tabelle) oder aus den vorhandenen Daten ableiten. Ableiten ist robuster: Stürzt ein Lauf ab, nachdem die Daten gespeichert sind, aber bevor der State aktualisiert ist, passen beide sonst nicht mehr zusammen.

**Beispiel:**
```sql
select epoch(max(start_date::timestamptz)) as watermark
from raw_activities;  -- View über den Raw Layer
```

**Mehr:** [dbt: Incremental models (Abschnitt is_incremental)](https://docs.getdbt.com/docs/build/incremental-models)

### Late-Arriving Data und Lookback-Fenster
**Was ist das?** Late-Arriving Data sind Datensätze, die erst nach dem Watermark bei dir ankommen, obwohl das Ereignis davor lag. Ein Lookback-Fenster fängt sie ab, indem du bei jedem Lauf ein Stück in die Vergangenheit zurückschaust.

**Genauer:** Du läufst am Montag, die Uhr synchronisiert aber erst am Mittwoch. Am Dienstag hast du schon eine Radtour geladen, dein Watermark steht also auf Dienstag. Am Mittwoch fragst du "alles nach Dienstag" ab und der Montagslauf fehlt für immer. Mit 7 Tagen Lookback fragst du "alles nach Watermark minus 7 Tage" ab und findest ihn. Der Preis: Du holst Bekanntes erneut und brauchst deshalb Deduplizierung (Stufe 4).

**Mehr:** [dbt: Microbatch (Option lookback)](https://docs.getdbt.com/docs/build/incremental-microbatch)

### Updates und Deletes erkennen (Change Data Capture)
**Was ist das?** Herausfinden, welche bereits geladenen Datensätze sich in der Quelle geändert haben oder gelöscht wurden. Wird das systematisch gemacht, heißt es Change Data Capture (CDC).

**Genauer:** Ein Watermark auf `start_date` sieht nur neue Aktivitäten. Benennst du einen alten Lauf um oder änderst den Sporttyp, merkt der Incremental Load das nicht, weil sich `start_date` nicht ändert. Gelöschte Aktivitäten tauchen einfach nicht mehr auf, und "nicht mehr da" sieht man nur, wenn man alles vergleicht. Deshalb der wöchentliche Full Refresh: alle IDs holen und mit deinen abgleichen. Datenbanken bieten echtes CDC über ihr Transaktionslog, Strava bietet stattdessen Webhooks (Stufe 11).

**Beispiel:**
```sql
-- IDs, die du hast, die beim Full Refresh aber nicht mehr kamen
select id
from activities
where id not in (select id from full_refresh_ids);
```

**Mehr:** [Wikipedia: Change data capture](https://en.wikipedia.org/wiki/Change_data_capture)

### Backfill
**Was ist das?** Das nachträgliche Laden oder Neuberechnen von Daten für einen vergangenen Zeitraum.

**Genauer:** Typische Anlässe: Du startest eine neue Pipeline und willst die ganze Historie, du hast einen Fehler in einer Transformation behoben, oder eine Quelle war ausgefallen. Ein guter Backfill ist idempotent (mehrmals ausführen schadet nicht), lässt sich auf Zeiträume eingrenzen und nach einem Abbruch fortsetzen. In Stufe 7 wird das wegen des Rate-Limits richtig anspruchsvoll.

**Mehr:** [Dagster: Backfilling data](https://dagster.io/docs/guides/build/partitions-and-backfills/backfilling-data)

---

## Stufe 4: Warehouse laden

### OLAP vs. OLTP
**Was ist das?** Zwei Arten von Datenbanken für unterschiedliche Aufgaben. OLTP (Online Transaction Processing) bedient eine App mit vielen kleinen Lese- und Schreibzugriffen. OLAP (Online Analytical Processing) beantwortet Auswertungsfragen über viele Datensätze.

**Genauer:** Stravas eigene Datenbank ist OLTP: "Speichere diesen Lauf", "zeig mir Aktivität 123". Dein DuckDB ist OLAP: "Wie viele Kilometer pro Woche im letzten Jahr?" OLTP-Systeme (Postgres, MySQL) sind auf einzelne Zeilen optimiert, OLAP-Systeme (DuckDB, BigQuery, Snowflake) auf Abfragen über wenige Spalten, aber Millionen Zeilen.

**Mehr:** [AWS: OLAP vs. OLTP](https://aws.amazon.com/compare/the-difference-between-olap-and-oltp/)

### Columnar Storage
**Was ist das?** Spaltenorientierte Speicherung: Die Werte einer Spalte liegen hintereinander, statt die Werte einer Zeile.

**Genauer:** Für "Summe aller Distanzen" muss eine spaltenorientierte Datenbank nur die Spalte `distance` lesen, nicht Name, Polyline und 50 andere Felder. Gleichartige Werte nebeneinander lassen sich außerdem gut komprimieren. Dafür ist das Ändern einzelner Zeilen teurer. Genau deshalb sind OLAP-Systeme und Parquet spaltenorientiert.

**Beispiel:**
```
Zeilenweise:  [1, "Morgenlauf", 10200]  [2, "Radtour", 45100]  ...
Spaltenweise: id: [1, 2, ...]  name: ["Morgenlauf", "Radtour", ...]  distance: [10200, 45100, ...]
```

**Mehr:** [Wikipedia: Column-oriented DBMS](https://en.wikipedia.org/wiki/Column-oriented_DBMS), [Why DuckDB](https://duckdb.org/why_duckdb)

### Datentypen
**Was ist das?** Die Festlegung, welche Art Wert in einer Spalte steht: ganze Zahl, Kommazahl, Text, Datum, Wahrheitswert.

**Genauer:** JSON kennt kaum Typen, ein Datum ist dort nur Text. Im Warehouse legst du fest, was was ist, und die Datenbank prüft es. Zwei Fallen bei Strava: Activity-IDs sind größer als 2,1 Milliarden und passen nicht in `INTEGER`, du brauchst `BIGINT`. Und Zeitstempel mit Zeitzone (`TIMESTAMPTZ`) sind etwas anderes als ohne (`TIMESTAMP`), siehe Zeitzonen in Stufe 5.

**Beispiel:**
```sql
create table activities (
    id            bigint primary key,
    name          varchar,
    sport_type    varchar,
    distance_m    double,
    moving_time_s integer,
    start_date    timestamptz,
    is_deleted    boolean default false
);
```

**Mehr:** [DuckDB: Data Types](https://duckdb.org/docs/stable/sql/data_types/overview)

### Primary Key
**Was ist das?** Eine Spalte (oder Kombination von Spalten), die jede Zeile eindeutig identifiziert, wie eine Ausweisnummer.

**Genauer:** Bei dir ist das die Activity-ID von Strava. Die Datenbank verhindert dann, dass dieselbe ID zweimal vorkommt. Ein Schlüssel aus der Quelle heißt Natural Key. Manchmal erzeugt man im Warehouse zusätzlich einen eigenen Surrogate Key, etwa wenn mehrere Quellen zusammenkommen (Stufe 11).

**Mehr:** [DuckDB: Constraints](https://duckdb.org/docs/stable/sql/constraints)

### Upsert und MERGE
**Was ist das?** Upsert ist ein Kunstwort aus Update und Insert: Gibt es den Datensatz schon, wird er aktualisiert, sonst neu eingefügt. `MERGE` ist der SQL-Befehl dafür.

**Genauer:** Ohne Upsert müsstest du vorher prüfen, was schon da ist, und dann getrennt `UPDATE` und `INSERT` ausführen. `MERGE` vergleicht eine Quelltabelle (deine Staging-Tabelle) per Key mit der Zieltabelle und regelt alle Fälle in einem Befehl. DuckDB kann `MERGE INTO` ab Version 1.4, davor gibt es `INSERT OR REPLACE`.

**Beispiel:**
```sql
merge into activities as t
using stg_activities as s
on t.id = s.id
when matched then update set name = s.name, sport_type = s.sport_type, distance_m = s.distance_m
when not matched then insert (id, name, sport_type, distance_m) values (s.id, s.name, s.sport_type, s.distance_m);
```

**Mehr:** [DuckDB: MERGE INTO](https://duckdb.org/docs/stable/sql/statements/merge_into)

### Deduplizierung
**Was ist das?** Das Entfernen doppelter Datensätze, sodass jeder nur einmal vorkommt.

**Genauer:** Durch Lookback und Full Refresh liegt dieselbe Aktivität mehrfach im Raw Layer, eventuell in verschiedenen Versionen (vor und nach dem Umbenennen). Vor dem MERGE behältst du pro ID nur die neueste Version, erkennbar am Ingestion-Timestamp. Sonst weiß `MERGE` nicht, welche Zeile gewinnen soll.

**Beispiel:**
```sql
select *
from raw_activities
qualify row_number() over (partition by id order by ingested_at desc) = 1;
```

**Mehr:** [DuckDB: QUALIFY](https://duckdb.org/docs/stable/sql/query_syntax/qualify)

### Idempotenz
**Was ist das?** Eine Operation ist idempotent, wenn es egal ist, ob du sie einmal oder zehnmal ausführst: Das Ergebnis ist dasselbe.

**Genauer:** Das ist eine der wichtigsten Eigenschaften einer Pipeline. Bricht ein Lauf ab, startest du ihn einfach nochmal, ohne zu überlegen, ob dabei Duplikate entstehen. Ein einfaches `INSERT` ist nicht idempotent (zweimal ausgeführt ergibt doppelte Zeilen), ein `MERGE` per Key schon. Genau das prüft das Fertig-Kriterium von Stufe 4.

**Mehr:** [Wikipedia: Idempotenz](https://de.wikipedia.org/wiki/Idempotenz)

### Soft Delete
**Was ist das?** Ein Datensatz wird nicht wirklich gelöscht, sondern nur als gelöscht markiert.

**Genauer:** Statt `DELETE` setzt du `is_deleted = true`, oft zusammen mit `deleted_at`. Vorteil: Du siehst, dass und wann etwas verschwunden ist, und kannst es rückgängig machen, wenn es ein Fehler war (etwa ein kaputter Full Refresh, der nur die Hälfte geliefert hat). Nachteil: Jede Abfrage muss `where not is_deleted` filtern, deshalb macht man das am besten einmal zentral im Staging-Model.

**Mehr:** [dbt: hard_deletes (Umgang mit gelöschten Datensätzen in Snapshots)](https://docs.getdbt.com/reference/resource-configs/hard-deletes)

---

## Stufe 5: Transformation (ELT)

### ETL vs. ELT
**Was ist das?** Zwei Reihenfolgen für dieselben drei Schritte: Extract (holen), Transform (umformen), Load (laden). Bei ETL wird vor dem Laden umgeformt, bei ELT erst danach im Warehouse.

**Genauer:** Früher war Rechenleistung im Warehouse teuer, also wurde vorher in Python oder Spezialtools umgeformt. Heute sind Warehouses schnell und günstig, deshalb lädt man Rohdaten zuerst und transformiert dann mit SQL. Vorteil: Die Rohdaten liegen im Warehouse, Transformationen lassen sich jederzeit neu ausführen, und SQL können viele lesen. dbt ist das Standardwerkzeug für das T in ELT.

**Mehr:** [dbt: ETL vs. ELT](https://www.getdbt.com/blog/etl-vs-elt)

### Medallion-Architektur (Bronze, Silver, Gold)
**Was ist das?** Eine Einteilung der Daten in drei Qualitätsstufen, benannt nach Medaillen.

**Genauer:** Bronze sind die Rohdaten, unverändert (dein Raw Layer). Silver sind bereinigte, typisierte und deduplizierte Daten (`stg_activities`). Gold sind fachlich aufbereitete Tabellen für konkrete Fragen (`weekly_training_volume`). Jede Stufe liest nur aus der vorigen. In dbt heißen dieselben Stufen meist raw, staging und marts.

**Mehr:** [Databricks: Medallion Architecture](https://www.databricks.com/blog/what-is-medallion-architecture)

### dbt
**Was ist das?** dbt (data build tool) ist ein Werkzeug, mit dem du Transformationen als SQL-Dateien schreibst. Es kümmert sich um Reihenfolge, Erstellen der Tabellen, Tests und Dokumentation.

**Genauer:** Jede SQL-Datei ist ein Model und wird zu einer Tabelle oder View. dbt erkennt die Abhängigkeiten zwischen Models und führt sie in der richtigen Reihenfolge aus. Mit `dbt-duckdb` läuft das komplett lokal. Die wichtigsten Befehle: `dbt run` baut die Models, `dbt test` führt die Tests aus, `dbt build` macht beides in Abhängigkeitsreihenfolge.

**Mehr:** [dbt: What is dbt?](https://docs.getdbt.com/docs/introduction), [dbt-duckdb](https://github.com/duckdb/dbt-duckdb)

### dbt: Models, Sources und Refs
**Was ist das?** Die drei Grundbausteine von dbt. Ein Model ist eine SQL-Datei mit einem `select`. Eine Source beschreibt Rohdaten, die nicht von dbt kommen. `ref` verweist von einem Model auf ein anderes.

**Genauer:** Statt Tabellennamen fest hinzuschreiben, nutzt du `{{ source(...) }}` und `{{ ref(...) }}`. Daraus baut dbt den Abhängigkeitsgraphen: `fct_activities` braucht `stg_activities`, also wird `stg_activities` zuerst gebaut. Außerdem zeichnet dbt damit die Lineage (Stufe 10).

**Beispiel:** `models/staging/stg_activities.sql`
```sql
select
    id                      as activity_id,
    name,
    sport_type,
    distance / 1000.0       as distance_km,
    moving_time             as moving_time_s,
    start_date::timestamptz as started_at
from {{ source('strava', 'raw_activities') }}
```

**Mehr:** [dbt: Models](https://docs.getdbt.com/docs/build/models), [dbt: Sources](https://docs.getdbt.com/docs/build/sources), [dbt: ref](https://docs.getdbt.com/reference/dbt-jinja-functions/ref)

### dbt: Materialisierung und Incremental Models
**Was ist das?** Die Materialisierung legt fest, wie dbt ein Model in der Datenbank anlegt: als View, als Tabelle oder inkrementell.

**Genauer:** Eine `view` speichert nur die Abfrage und rechnet bei jedem Zugriff neu. Eine `table` wird bei jedem Lauf komplett neu gebaut. Ein `incremental` Model verarbeitet nur neue Zeilen und fügt sie per `unique_key` ein oder aktualisiert sie. Das ist im Prinzip dein MERGE aus Stufe 4, nur dass dbt das SQL dafür erzeugt. Faustregel: Staging als View, Marts als Tabelle, incremental erst, wenn es spürbar langsam wird oder du es lernen willst.

**Beispiel:**
```sql
{{ config(materialized='incremental', unique_key='activity_id') }}

select ...
from {{ ref('stg_activities') }}
{% if is_incremental() %}
where ingested_at > (select max(ingested_at) from {{ this }})
{% endif %}
```

**Mehr:** [dbt: Materializations](https://docs.getdbt.com/docs/build/materializations), [dbt: Incremental models](https://docs.getdbt.com/docs/build/incremental-models)

### dbt: Tests
**Was ist das?** Automatische Prüfungen deiner Daten (nicht deines Codes), die dbt nach dem Bauen ausführt.

**Genauer:** Eingebaut sind vier: `unique` (keine Duplikate), `not_null` (keine leeren Werte), `accepted_values` (nur erlaubte Werte, z. B. bekannte Sporttypen) und `relationships` (jeder Fremdschlüssel existiert in der Zieltabelle). Schlägt ein Test fehl, baut `dbt build` die nachgelagerten Models nicht mehr. Eigene Tests sind einfach SQL-Abfragen, die fehlerhafte Zeilen zurückgeben (Beispiel in Stufe 8).

**Beispiel:** `models/staging/_staging.yml`
```yaml
models:
  - name: stg_activities
    columns:
      - name: activity_id
        data_tests:
          - unique
          - not_null
```

**Mehr:** [dbt: Data tests](https://docs.getdbt.com/docs/build/data-tests)

### dbt: Snapshots
**Was ist das?** Ein Snapshot hält fest, wie ein Datensatz zu jedem Zeitpunkt aussah, auch wenn die Quelle nur den aktuellen Stand kennt.

**Genauer:** Strava sagt dir nur den heutigen Kilometerstand deiner Schuhe. Ein dbt-Snapshot vergleicht bei jedem Lauf mit dem letzten bekannten Stand und legt bei einer Änderung eine neue Zeile an, mit Gültigkeitszeitraum `dbt_valid_from` und `dbt_valid_to`. Das ist die technische Umsetzung von SCD Typ 2 (nächster Abschnitt). Ein Snapshot sieht nur, was sich zwischen zwei Läufen geändert hat, Historie vor dem ersten Lauf kann er nicht wiederherstellen.

Achtung: Laut Strava-Doku liefert `/athlete` die Detail-Ansicht mit Schuhen, Rädern, Gewicht und FTP nur mit dem Scope `profile:read_all`. Die README fordert bisher `read,activity:read_all` an, für Stufe 5 musst du den Refresh Token also einmal mit erweitertem Scope neu erzeugen.

**Beispiel:** `snapshots/snp_gear.yml`
```yaml
snapshots:
  - name: snp_gear
    relation: source('strava', 'raw_gear')
    config:
      unique_key: id
      strategy: check
      check_cols: [name, distance]
```

**Mehr:** [dbt: Snapshots](https://docs.getdbt.com/docs/build/snapshots), [Strava: Get Authenticated Athlete](https://developers.strava.com/docs/reference/#api-Athletes-getLoggedInAthlete)

### Dimensionsmodellierung und Star Schema
**Was ist das?** Eine bewährte Art, Tabellen für Auswertungen zu organisieren: in der Mitte eine Faktentabelle mit Messwerten, außen herum Dimensionstabellen mit beschreibenden Infos. Aufgezeichnet sieht das aus wie ein Stern.

**Genauer:** Fakten sind Ereignisse mit Zahlen, die man summiert oder mittelt: eine Aktivität mit Distanz, Dauer, Höhenmetern. Dimensionen beantworten "wann, was, womit": Datum (mit Wochentag, Kalenderwoche, Monat), Sporttyp, Gear. Die Faktentabelle enthält Schlüssel auf die Dimensionen. Auswertungen sind dann immer "Fakten summieren, nach Dimension gruppieren". Wichtig ist die Granularität: Eine Zeile in `fct_activities` ist genau eine Aktivität.

**Beispiel:**
```
                   dim_date
                      │
dim_sport_type ── fct_activities ── dim_gear
```

**Mehr:** [Kimball Group: Dimensional Modeling Techniques](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/), [Wikipedia: Star schema](https://en.wikipedia.org/wiki/Star_schema)

### Historisierung (SCD Typ 2)
**Was ist das?** SCD steht für Slowly Changing Dimension, eine Dimension, deren Werte sich gelegentlich ändern. Typ 2 heißt, bei jeder Änderung eine neue Zeile anzulegen, statt die alte zu überschreiben.

**Genauer:** Typ 1 überschreibt einfach, du kennst nur den aktuellen Stand. Typ 2 behält die Geschichte: Jede Version hat ein `valid_from` und `valid_to`, die aktuelle hat `valid_to = null`. So kannst du fragen: "Wie viele Kilometer hatte dieser Schuh am Tag meines Marathons?" oder "Welches Gewicht hatte ich bei dieser Radtour?" für historisch korrekte W/kg. Beim Join mit der Faktentabelle nimmst du die Version, die zum Aktivitätsdatum gültig war.

**Beispiel:**

| gear_id | name | distance_km | valid_from | valid_to |
|---|---|---|---|---|
| g123 | Pegasus | 412 | 2026-09-01 | 2026-10-01 |
| g123 | Pegasus | 498 | 2026-10-01 | null |

**Mehr:** [Wikipedia: Slowly changing dimension](https://en.wikipedia.org/wiki/Slowly_changing_dimension)

### Window Functions
**Was ist das?** SQL-Funktionen, die für jede Zeile über eine Gruppe benachbarter Zeilen rechnen, ohne die Zeilen zusammenzufassen wie `group by`.

**Genauer:** Damit rechnest du gleitende Durchschnitte, laufende Summen, Ränge oder den Vergleich zur Vorwoche. `over (...)` legt das Fenster fest: `partition by` teilt in Gruppen (z. B. pro Sporttyp), `order by` sortiert, `rows between` begrenzt, wie viele Nachbarzeilen dazugehören.

**Beispiel:**
```sql
select
    week,
    km,
    avg(km) over (order by week rows between 3 preceding and current row) as km_avg_4w,
    km - lag(km) over (order by week)                                     as km_vs_vorwoche
from weekly_training_volume;
```

**Mehr:** [DuckDB: Window Functions](https://duckdb.org/docs/stable/sql/functions/window_functions)

### Zeitzonen und Einheiten
**Was ist das?** Zwei Klassiker für falsche Zahlen: Zeiten ohne klare Zeitzone und Werte ohne klare Einheit.

**Genauer:** Strava liefert `start_date` in UTC und `start_date_local` in deiner Ortszeit. Vorsicht: `start_date_local` endet trotzdem auf `Z`, was eigentlich "UTC" bedeutet. Liest du das als UTC ein und rechnest dann in Ortszeit um, verschieben sich alle Aktivitäten um ein bis zwei Stunden. Lies `start_date_local` deshalb als `TIMESTAMP` ohne Zeitzone ein. Für Wochen- und Tagesauswertungen zählt die Ortszeit: Ein Lauf um 00:30 Uhr am Montag gehört in die neue Woche, auch wenn in UTC noch Sonntag war. Die Einheiten bei Strava: Distanz und Höhe in Metern, Zeit in Sekunden, Geschwindigkeit in m/s. Rechne einmal zentral im Staging um und schreib die Einheit in den Spaltennamen (`distance_km`).

**Beispiel:**
```sql
select
    date_trunc('week', start_date_local)       as week,  -- Ortszeit, Woche beginnt am Montag
    distance / 1000.0                          as distance_km,
    1000.0 / nullif(average_speed * 60, 0)     as pace_min_per_km
from stg_activities;
```

**Mehr:** [Strava: SummaryActivity (Felder und Einheiten)](https://developers.strava.com/docs/reference/#api-models-SummaryActivity), [DuckDB: Timestamp Types](https://duckdb.org/docs/stable/sql/data_types/timestamp)

---

## Stufe 6: Orchestrierung

### DAG und Abhängigkeiten
**Was ist das?** DAG steht für Directed Acyclic Graph: ein Ablaufplan aus Schritten mit Pfeilen dazwischen, die zeigen, was worauf wartet. Azyklisch heißt, es gibt keine Kreise, irgendwann ist man fertig.

**Genauer:** Deine Pipeline ist ein DAG. Ein Orchestrator liest diesen Graphen und startet jeden Schritt erst, wenn alle Vorgänger erfolgreich waren. Unabhängige Zweige (unten Aktivitäten und Gear) kann er parallel ausführen. Schlägt ein Schritt fehl, laufen die abhängigen nicht los, und du startest nur ab dem Fehler neu.

**Beispiel:**
```
raw_activities ──> stg_activities ──> fct_activities ──> weekly_training_volume
raw_gear ────────> snp_gear ────────> dim_gear
```

**Mehr:** [Wikipedia: Directed acyclic graph](https://en.wikipedia.org/wiki/Directed_acyclic_graph)

### Scheduling (cron und launchd)
**Was ist das?** Das automatische Starten der Pipeline zu festen Zeiten, z. B. jeden Morgen um 6 Uhr.

**Genauer:** Der Klassiker ist cron: eine Zeile mit fünf Zeitfeldern (Minute, Stunde, Tag, Monat, Wochentag) und dem Befehl. Auf dem Mac gibt es zusätzlich launchd. Für einen Laptop ist der Unterschied wichtig: cron lässt einen Lauf ausfallen, wenn der Rechner zur geplanten Zeit schläft, launchd holt ihn nach dem Aufwachen nach. Orchestratoren wie Dagster haben eigene Schedules mit derselben cron-Schreibweise, sehen aber zusätzlich Abhängigkeiten, Historie und Fehler.

**Beispiel:** Eintrag über `crontab -e`
```
0 6 * * * cd ~/Documents/GitHub/strava-data && .venv/bin/python fetch_activities.py >> logs/cron.log 2>&1
```

**Mehr:** [crontab.guru](https://crontab.guru/), [Apple: Scheduling Timed Jobs](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html), [Dagster: Schedules](https://dagster.io/docs/guides/automate/schedules)

### Retries im Orchestrator
**Was ist das?** Der Orchestrator wiederholt einen fehlgeschlagenen Schritt automatisch, bevor er ihn als gescheitert markiert.

**Genauer:** Das ergänzt die Retries aus Stufe 1, ersetzt sie aber nicht. Der HTTP-Retry fängt kurze Aussetzer einer einzelnen Anfrage ab, der Orchestrator-Retry den ganzen Schritt, etwa wenn das WLAN eine Minute weg war. Weil der Schritt dann komplett neu läuft, muss er idempotent sein (Stufe 4).

**Beispiel:**
```python
@dg.asset(retry_policy=dg.RetryPolicy(max_retries=3, delay=60))
def raw_activities() -> None: ...
```

**Mehr:** [Dagster: Op retries](https://dagster.io/docs/guides/build/ops/op-retries)

### Alerting
**Was ist das?** Eine aktive Benachrichtigung, wenn etwas schiefgeht, statt darauf zu hoffen, dass du es selbst merkst.

**Genauer:** Eine Pipeline, die still ausfällt, ist in der Praxis das häufigste Problem. Mindestens bei fehlgeschlagenen Läufen und bei veralteten Daten (Freshness, Stufe 10) sollte eine Nachricht kommen, per Mail, Slack oder Push aufs Handy. Gute Alerts sind selten und eindeutig, sonst gewöhnt man sich daran, sie zu ignorieren.

**Mehr:** [Dagster: Run status sensors](https://dagster.io/docs/guides/automate/sensors/run-status-sensors), [ntfy (einfache Push-Nachrichten)](https://docs.ntfy.sh/)

### Assets vs. Tasks
**Was ist das?** Zwei Denkweisen für Orchestrierung. Task-basiert (Airflow) beschreibst du Schritte, die nacheinander laufen. Asset-basiert (Dagster) beschreibst du die Daten, die entstehen sollen, und woraus sie gebaut werden.

**Genauer:** Bei Tasks fragst du "Ist Schritt 3 gelaufen?", bei Assets "Ist die Tabelle `weekly_training_volume` aktuell, und woraus wurde sie gebaut?". Assets passen gut zu dbt, weil jedes dbt-Model ein Asset ist. `dagster-dbt` liest deine Models und baut daraus automatisch den Graphen. In der UI siehst du dann für jede Tabelle, wann sie zuletzt gebaut wurde.

**Beispiel:**
```python
import dagster as dg

@dg.asset
def raw_activities() -> None:
    """Holt Aktivitäten von Strava und legt sie im Raw Layer ab."""
    ...

@dg.asset(deps=[raw_activities])
def activities_table() -> None:
    ...
```

**Mehr:** [Dagster: Assets](https://dagster.io/docs/guides/build/assets), [Dagster: dbt-Integration](https://dagster.io/docs/integrations/libraries/dbt), [Airflow: Tasks](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/tasks.html)

### Backfills über Zeiträume (Partitionen)
**Was ist das?** Ein Orchestrator teilt Daten in Partitionen auf, z. B. einen Tag pro Partition, und kann gezielt einzelne Zeiträume neu berechnen.

**Genauer:** Statt "alles neu" sagst du "bau den März neu". Dagster zeigt dir für jede Partition, ob sie existiert, aktuell ist oder fehlgeschlagen ist, und startet Backfills für eine Auswahl. Das ist das Werkzeug zum Backfill-Konzept aus Stufe 3.

**Mehr:** [Dagster: Partitioning assets](https://dagster.io/docs/guides/build/partitions-and-backfills/partitioning-assets)

---

## Stufe 7: Detaildaten und Skalierung

### N+1-Requests
**Was ist das?** Ein Muster, bei dem du eine Liste mit 1 Anfrage holst und dann für jedes der N Elemente eine weitere Anfrage brauchst, zusammen also N+1.

**Genauer:** Die Aktivitätenliste kostet bei 1.000 Aktivitäten etwa 5 Anfragen. Die Streams dazu kosten 1.000, eine pro Aktivität. Bei einem Tageslimit von grob 1.000 Lese-Anfragen ist damit ein ganzer Tag weg. Das Muster kennt man auch aus Datenbanken, wo es Apps ausbremst. Gegenmittel: nur das Nötige holen, Ergebnisse aufheben statt neu holen und über mehrere Tage verteilen.

**Beispiel:**
```
GET /athlete/activities?page=1..5        →     5 Requests
GET /activities/{id}/streams  × 1.000    → 1.000 Requests
```

**Mehr:** [Strava: Get Activity Streams](https://developers.strava.com/docs/reference/#api-Streams-getActivityStreams)

### Request-Budgeting und Priorisierung
**Was ist das?** Das Rate-Limit wie ein Budget verplanen: Wie viele Anfragen gebe ich wofür aus, und was kommt zuerst?

**Genauer:** Reserviere einen festen Teil für den täglichen Sync (z. B. 50 Anfragen), damit neue Aktivitäten immer ankommen, und gib den Rest für den Backfill aus. Priorisiere, was dir am meisten bringt, etwa die neuesten Aktivitäten zuerst oder nur Läufe mit Herzfrequenz. Lies den aktuellen Verbrauch aus den Headern, statt selbst mitzuzählen, denn auch jeder manuelle Testlauf deiner App zählt mit.

**Beispiel:**
```python
DAILY_RESERVE = 50

def remaining_budget(response) -> int:
    used_15min, used_day = map(int, response.headers["X-ReadRateLimit-Usage"].split(","))
    limit_15min, limit_day = map(int, response.headers["X-ReadRateLimit-Limit"].split(","))
    return min(limit_15min - used_15min, limit_day - used_day - DAILY_RESERVE)
```

**Mehr:** [Strava: Rate Limits](https://developers.strava.com/docs/rate-limits/)

### Zeitreihen
**Was ist das?** Messwerte, die in regelmäßigen Abständen über die Zeit aufgezeichnet werden, z. B. jede Sekunde Herzfrequenz, Höhe und Position.

**Genauer:** Strava liefert Streams als parallele Listen: `time` enthält die Sekunden seit dem Start, `heartrate`, `altitude` und `latlng` die Werte dazu. Für Auswertungen wandelst du das in eine lange Tabelle mit einer Zeile pro Messpunkt um. Typische Operationen: auf gröbere Intervalle verdichten (Resampling), Lücken behandeln (Uhr pausiert), gleitende Werte berechnen.

**Beispiel:**
```json
{"time": {"data": [0, 1, 2]}, "heartrate": {"data": [92, 95, 97]}}
```
wird zu

| activity_id | t_s | heartrate |
|---|---|---|
| 123 | 0 | 92 |
| 123 | 1 | 95 |
| 123 | 2 | 97 |

**Mehr:** [Strava: Streams](https://developers.strava.com/docs/reference/#api-Streams), [Wikipedia: Zeitreihenanalyse](https://de.wikipedia.org/wiki/Zeitreihenanalyse)

### Backfill-Strategien
**Was ist das?** Die Planung eines großen Nachlade-Jobs, damit er zuverlässig durchläuft, auch über Tage und mit Unterbrechungen.

**Genauer:** Drei Bausteine: eine Queue (Warteschlange) mit allen noch fehlenden Activity-IDs, ein Checkpoint, der nach jeder erledigten Aktivität festhält, was fertig ist, und eine Reihenfolge. Neueste zuerst bringt schnell nützliche Daten. Die Queue musst du nicht separat speichern: "alle Aktivitäten ohne Streams-Datei" ist die Queue, abgeleitet aus den Daten wie beim Watermark. Dann ist jede fertige Datei automatisch der Checkpoint.

**Beispiel:**
```sql
select a.id
from activities as a
left join stream_files as s on s.activity_id = a.id
where s.activity_id is null and not a.is_deleted
order by a.start_date desc
limit 400;
```

**Mehr:** [Dagster: Backfilling data](https://dagster.io/docs/guides/build/partitions-and-backfills/backfilling-data)

### Datenvolumen
**Was ist das?** Wie viele Daten anfallen, und ab wann das die Technik beeinflusst.

**Genauer:** Deine Aktivitätenliste ist winzig, tausend Aktivitäten sind wenige Megabyte. Streams sind etwas anderes: Ein einstündiger Lauf hat 3.600 Messpunkte mal mehrere Kanäle, tausend Aktivitäten ergeben Millionen Zeilen. Ab da merkst du Unterschiede bei Dateiformat, Kompression und Abfragezeit. Faustregel: erst messen, dann optimieren. Für Datenmengen, die auf einen Laptop passen, braucht es kein Spark.

**Mehr:** [Jordan Tigani: Big Data is Dead](https://motherduck.com/blog/big-data-is-dead/)

### Dateiformate: JSON vs. Parquet
**Was ist das?** JSON ist ein Textformat, das Menschen lesen können. Parquet ist ein binäres, spaltenorientiertes Format für Analysen.

**Genauer:** JSON wiederholt jeden Feldnamen in jedem Datensatz, speichert Zahlen als Text und muss komplett gelesen werden. Parquet speichert Spalten getrennt und komprimiert, kennt Datentypen und enthält Statistiken (Min/Max pro Block), mit denen Abfragen ganze Teile überspringen. Bei Streams ist Parquet typischerweise ein Bruchteil so groß, und Abfragen über eine Spalte sind deutlich schneller. JSON bleibt im Raw Layer trotzdem sinnvoll, weil es genau das ist, was die API geliefert hat.

**Beispiel:**
```sql
copy (select * from read_json_auto('data/raw/streams/*.json'))
to 'data/streams.parquet' (format parquet);
```

**Mehr:** [Apache Parquet: Overview](https://parquet.apache.org/docs/overview/), [DuckDB: Parquet](https://duckdb.org/docs/stable/data/parquet/overview)

---

## Stufe 8: Datenqualität

### Schema-Validierung
**Was ist das?** Automatisch prüfen, ob Daten die erwartete Form haben: alle Pflichtfelder da, richtige Typen, Werte im erlaubten Bereich.

**Genauer:** Je früher ein Fehler auffällt, desto billiger. Validierst du direkt nach dem Abruf in Python, merkst du Probleme, bevor sie in Tabellen und Dashboards landen. Pydantic prüft einzelne Datensätze (gut für API-Antworten), pandera ganze DataFrames.

**Beispiel:**
```python
from datetime import datetime

from pydantic import BaseModel, Field

class Activity(BaseModel):
    id: int
    name: str
    sport_type: str
    distance: float = Field(ge=0)
    moving_time: int = Field(ge=0)
    start_date: datetime

Activity.model_validate(raw_activity)  # wirft ValidationError, wenn etwas nicht passt
```

**Mehr:** [Pydantic: Models](https://pydantic.dev/docs/validation/latest/concepts/models/), [pandera](https://pandera.readthedocs.io/)

### Schema Drift
**Was ist das?** Die Struktur der Quelldaten ändert sich mit der Zeit, ohne dass dir jemand Bescheid sagt.

**Genauer:** Felder kommen dazu, verschwinden, werden umbenannt oder ändern ihren Typ. Ein echtes Beispiel bei Strava: Das Feld `type` wurde durch das genauere `sport_type` abgelöst. Zusätzliche Felder sind meist harmlos, fehlende oder umgedeutete verfälschen still deine Zahlen. Gegenmittel: Schema-Validierung beim Abruf, unbekannte Felder bewusst erkennen (Pydantic mit `extra="allow"` und dann `model_extra` prüfen) und Rohdaten unverändert aufheben, damit du nachträglich reagieren kannst.

**Mehr:** [Strava: Changelog](https://developers.strava.com/docs/changelog/)

### Data Contracts
**Was ist das?** Eine verbindliche Vereinbarung zwischen dem, der Daten liefert, und dem, der sie nutzt: welche Felder, welche Typen, welche Bedeutung, welche Qualität.

**Genauer:** In Firmen ist das eine Absprache zwischen Teams, damit eine Änderung im Quellsystem nicht unbemerkt Dashboards kaputtmacht. Strava schließt mit dir keinen Vertrag, aber du kannst einen innerhalb deiner Pipeline festlegen: "`stg_activities` garantiert diese Spalten mit diesen Typen." dbt erzwingt das mit `contract: {enforced: true}`. Liefert das SQL andere Spalten oder Typen, bricht der Build ab. Dafür müssen alle Spalten im YAML aufgeführt sein.

**Beispiel:**
```yaml
models:
  - name: stg_activities
    config:
      contract:
        enforced: true
    columns:
      - name: activity_id
        data_type: bigint
      - name: distance_km
        data_type: double
      # ... alle weiteren Spalten
```

**Mehr:** [dbt: Model contracts](https://docs.getdbt.com/docs/mesh/govern/model-contracts), [Open Data Contract Standard](https://bitol-io.github.io/open-data-contract-standard/)

### Plausibilitätsprüfungen
**Was ist das?** Prüfungen, ob Werte inhaltlich Sinn ergeben, nicht nur formal korrekt sind.

**Genauer:** Eine Distanz von 0 Metern ist eine gültige Zahl, aber für einen 45-minütigen Lauf unplausibel. Typische Regeln: Pace beim Laufen zwischen 2:30 und 15:00 min/km, Herzfrequenz zwischen 30 und 230, Startdatum nicht in der Zukunft. Unplausibel heißt nicht automatisch falsch (GPS-Aussetzer, Uhr vergessen auszuschalten), deshalb lieber warnen oder in Quarantäne schieben als stillschweigend löschen.

**Beispiel:** `tests/assert_plausible_run_pace.sql` (eigener dbt-Test, jede zurückgegebene Zeile gilt als Fehler)
```sql
select activity_id, pace_min_per_km
from {{ ref('stg_activities') }}
where sport_type = 'Run'
  and pace_min_per_km not between 2.5 and 15
```

**Mehr:** [dbt: Singular data tests](https://docs.getdbt.com/docs/build/data-tests#singular-data-tests), [dbt-expectations](https://github.com/metaplane/dbt-expectations)

### Quarantäne
**Was ist das?** Fehlerhafte Datensätze werden beiseitegelegt statt verarbeitet, damit sie den Rest nicht verfälschen und du sie dir später ansehen kannst.

**Genauer:** Zwei Strategien: Bei schweren Fehlern (ein Pflichtfeld fehlt bei allen Datensätzen) stoppt die Pipeline, denn dann ist etwas grundsätzlich kaputt. Bei einzelnen Ausreißern laufen die guten Datensätze weiter, und die schlechten landen mit Begründung in einer eigenen Tabelle oder einem Ordner. Wichtig ist, dass jemand die Quarantäne anschaut, sonst ist sie nur ein Mülleimer.

**Beispiel:**
```python
valid, quarantined = [], []
for raw in activities:
    try:
        valid.append(Activity.model_validate(raw))
    except ValidationError as error:
        quarantined.append({"data": raw, "error": str(error)})
```

**Mehr:** [dbt: store_failures](https://docs.getdbt.com/reference/resource-configs/store_failures)

---

## Stufe 9: Software-Engineering-Praxis

### Projektstruktur und Packaging
**Was ist das?** Code sinnvoll auf Dateien und Ordner aufteilen und als installierbares Python-Paket beschreiben.

**Genauer:** Ein einzelnes Skript reicht am Anfang, aber mit Extract, Raw Layer, Validierung und Tests wird es unübersichtlich. Üblich ist das src-Layout: Der Code liegt in `src/strava_data/`, die Tests in `tests/`, und eine `pyproject.toml` beschreibt Name, Abhängigkeiten und Werkzeuge. Mit `pip install -e .` ist dein Code dann überall importierbar, auch in den Tests. Auf Dauer ersetzt das die `requirements.txt`.

**Beispiel:**
```
strava-data/
├── pyproject.toml
├── src/strava_data/
│   ├── __init__.py
│   ├── auth.py
│   ├── extract.py
│   └── raw_layer.py
├── tests/
└── dbt/
```

**Mehr:** [Python Packaging: src layout vs. flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/), [Python Packaging: Packaging Python Projects](https://packaging.python.org/en/latest/tutorials/packaging-projects/)

### Type Hints
**Was ist das?** Angaben im Code, welchen Typ Parameter und Rückgabewerte haben, z. B. `-> list[dict]`.

**Genauer:** Python prüft Typen beim Ausführen nicht, aber Werkzeuge wie mypy oder dein Editor tun es vorher und finden so Fehler, bevor der Code läuft. Außerdem sind Typen Dokumentation: Man sieht sofort, was eine Funktion erwartet. `fetch_activities.py` nutzt sie schon.

**Beispiel:**
```python
def fetch_all_activities(access_token: str, after: int | None = None) -> list[dict]:
```

**Mehr:** [Python: typing](https://docs.python.org/3/library/typing.html), [mypy: Getting started](https://mypy.readthedocs.io/en/stable/getting_started.html)

### Integrationstests
**Was ist das?** Tests, die prüfen, ob mehrere Teile zusammen funktionieren, nicht nur jedes für sich.

**Genauer:** Unit-Tests (Stufe 1) prüfen einzelne Funktionen. Ein Integrationstest prüft einen ganzen Ablauf: Beispiel-Rohdateien rein, Raw Layer → DuckDB → `dbt build`, am Ende stimmen die Zahlen im Mart. Solche Tests sind langsamer, finden aber die Fehler an den Übergängen. Die Faustregel "viele Unit-Tests, einige Integrationstests, wenige End-to-End-Tests" heißt Testpyramide.

**Mehr:** [Martin Fowler: The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)

### Fixtures
**Was ist das?** Vorbereitete Testdaten oder Testumgebungen, die mehrere Tests gemeinsam nutzen.

**Genauer:** In pytest ist eine Fixture eine Funktion mit `@pytest.fixture`. Ein Test fordert ihr Ergebnis einfach als Parameter an, z. B. eine Beispielaktivität oder eine leere DuckDB-Datenbank. Weil das Repo öffentlich ist: Fixtures nie aus echten API-Antworten kopieren, ohne Koordinaten (`start_latlng`, `end_latlng`, `map.summary_polyline`) und Tokens zu entfernen.

**Beispiel:**
```python
@pytest.fixture
def activity() -> dict:
    return {
        "id": 1,
        "name": "Testlauf",
        "sport_type": "Run",
        "distance": 10000.0,
        "moving_time": 3000,
        "start_date": "2026-10-18T06:00:00Z",
        "start_latlng": [0.0, 0.0],  # nie echte Koordinaten
    }

def test_distance_km(activity):
    assert to_distance_km(activity) == 10.0
```

**Mehr:** [pytest: How to use fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html)

### Linting, Formatting und pre-commit
**Was ist das?** Ein Linter findet typische Fehler und schlechten Stil im Code, ein Formatter bringt ihn in eine einheitliche Form. pre-commit führt beides automatisch vor jedem Commit aus.

**Genauer:** ruff erledigt Linting und Formatting in einem, sehr schnell. Mit pre-commit lässt sich nichts mehr committen, das die Prüfungen nicht besteht. Dieselben Prüfungen laufen in der CI noch einmal, falls pre-commit irgendwo nicht installiert ist.

**Beispiel:**
```bash
ruff check .        # Fehler und Stilprobleme finden
ruff format .       # Code einheitlich formatieren
pre-commit install  # ab jetzt vor jedem Commit automatisch
```

**Mehr:** [ruff](https://docs.astral.sh/ruff/), [pre-commit](https://pre-commit.com/)

### Continuous Integration (CI)
**Was ist das?** Bei jedem Push prüft ein Server automatisch, ob der Code noch funktioniert: Linting, Tests, eventuell ein Build.

**Genauer:** "Bei mir läuft's" reicht nicht: CI läuft in einer frischen Umgebung und findet so auch vergessene Abhängigkeiten. Bei GitHub heißt das GitHub Actions, ein Workflow ist eine YAML-Datei in `.github/workflows/`. Ein grüner Haken am Commit heißt, dass alle Prüfungen bestanden sind.

**Beispiel:** `.github/workflows/ci.yml`
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt ruff pytest
      - run: ruff check .
      - run: pytest
```

**Mehr:** [GitHub Actions: Building and testing Python](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)

### Docker
**Was ist das?** Ein Werkzeug, das dein Programm samt Python-Version, Bibliotheken und Einstellungen in einen Container packt, der überall gleich läuft.

**Genauer:** Das Dockerfile ist das Rezept: Basis-Image, Abhängigkeiten installieren, Code kopieren, Startbefehl. Daraus baust du ein Image und startest Container. So läuft die Pipeline auf deinem Mac, in der CI und auf einem Server identisch. Daten und Secrets gehören nicht ins Image, sondern werden beim Start als Volume und Umgebungsvariablen übergeben. Eine `.dockerignore` mit `.env` und `data/` verhindert, dass `COPY . .` sie trotzdem einpackt.

**Beispiel:**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "fetch_activities.py"]
```
```bash
docker build -t strava-data .
docker run --env-file .env -v "$PWD/data:/app/data" strava-data
```

**Mehr:** [Docker: Get started](https://docs.docker.com/get-started/)

### Konfiguration per Umgebung
**Was ist das?** Alles, was sich zwischen Umgebungen unterscheidet (Pfade, Datenbank, Log-Level, Secrets), kommt aus Umgebungsvariablen statt aus dem Code.

**Genauer:** So läuft derselbe Code lokal mit `data/`, in der CI mit Testdaten und auf einem Server mit anderem Pfad, ohne dass du etwas änderst. Sinnvolle Standardwerte machen den lokalen Start einfach. Es ist dasselbe Prinzip wie bei den Secrets (Stufe 1), nur für alle Einstellungen.

**Beispiel:**
```python
DATA_DIR = Path(os.environ.get("STRAVA_DATA_DIR", "data"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
```

**Mehr:** [The Twelve-Factor App: Config](https://12factor.net/config)

---

## Stufe 10: Serving und Betrieb

### Semantic Layer und Metriken
**Was ist das?** Eine zentrale Stelle, an der Kennzahlen wie "Wochenkilometer" oder "Durchschnittspace" einmal definiert werden, damit alle Auswertungen dieselbe Definition nutzen.

**Genauer:** Ohne Semantic Layer rechnet jedes Dashboard seine Kennzahlen selbst, und irgendwann zählt eins Spaziergänge mit und das andere nicht. Mit Semantic Layer gibt es genau eine Definition mit Namen, Formel und Filter. Für ein Ein-Personen-Projekt reicht als Einstieg ein gut dokumentiertes Mart-Model. Die dbt Semantic Layer (MetricFlow) zeigt, wie es im Großen aussieht.

**Mehr:** [dbt: Semantic Layer](https://docs.getdbt.com/docs/use-dbt-semantic-layer/dbt-sl)

### BI und Dashboards
**Was ist das?** BI (Business Intelligence) heißt, Daten so aufzubereiten, dass Menschen daraus Entscheidungen ableiten können. Ein Dashboard ist die Ansicht dafür: Diagramme und Kennzahlen auf einer Seite.

**Genauer:** Mit Streamlit baust du Dashboards in Python, sehr flexibel. Mit Evidence baust du sie aus SQL und Markdown, näher an klassischen Berichten. Beide lesen direkt aus DuckDB. Ein gutes Dashboard beantwortet wenige konkrete Fragen ("Wie entwickelt sich mein Wochenumfang?") und zeigt, wie aktuell die Daten sind. Wenn es öffentlich erreichbar ist: keine Karten und Startpunkte (siehe Datenschutz in der Roadmap).

**Beispiel:**
```python
import duckdb
import streamlit as st

df = duckdb.connect("strava.duckdb", read_only=True).sql("select * from weekly_training_volume").df()
st.line_chart(df, x="week", y="km")
```

**Mehr:** [Streamlit: Docs](https://docs.streamlit.io/), [Evidence: Docs](https://docs.evidence.dev/)

### Observability
**Was ist das?** Von außen erkennen können, wie es der Pipeline geht und ob die Daten stimmen, ohne in den Code zu schauen.

**Genauer:** Für Datenpipelines gibt es ein paar typische Signale: Laufzeit (wird ein Schritt plötzlich langsamer?), Row Counts (kamen heute 0 statt der üblichen ein bis zwei neuen Aktivitäten?), Freshness (wann kam zuletzt etwas an?) und Schema (haben sich Spalten geändert?). Am einfachsten schreibst du nach jedem Schritt eine Zeile in eine Tabelle `pipeline_runs` und baust daraus eine Übersicht.

**Beispiel:**
```sql
create table if not exists pipeline_runs (
    run_at      timestamptz,
    step        varchar,
    rows_loaded integer,
    duration_s  double,
    status      varchar
);
```

**Mehr:** [Monte Carlo: What is Data Observability?](https://montecarlo.ai/blog-what-is-data-observability)

### Freshness
**Was ist das?** Wie aktuell die Daten sind, also wie lange der letzte erfolgreiche Ladevorgang her ist.

**Genauer:** Die Falle: Freshness nicht am Startdatum der letzten Aktivität messen. Zwei Ruhetage sind kein Pipeline-Fehler. Miss stattdessen, wann die Pipeline zuletzt erfolgreich gelaufen ist. Wenn das zwei Tage her ist, ist etwas kaputt, genau das prüft das Fertig-Kriterium von Stufe 10. dbt kann Freshness mit `dbt source freshness` auch für Sources prüfen.

**Beispiel:**
```sql
select max(run_at) < now() - interval 2 day as is_stale
from pipeline_runs
where status = 'success';
```

**Mehr:** [dbt: Source freshness](https://docs.getdbt.com/docs/deploy/source-freshness)

### Lineage und Dokumentation
**Was ist das?** Lineage zeigt, woher eine Tabelle ihre Daten hat und was von ihr abhängt. Dokumentation beschreibt, was Tabellen und Spalten bedeuten.

**Genauer:** Sieht eine Zahl im Dashboard seltsam aus, folgst du der Lineage rückwärts bis zur Quelle. Willst du eine Spalte ändern, zeigt sie vorwärts, was alles betroffen ist. dbt erzeugt beides automatisch aus deinen `ref`s und `description`s: `dbt docs generate` und danach `dbt docs serve` öffnen eine Webseite mit Graph und Beschreibungen.

**Mehr:** [dbt: Documentation](https://docs.getdbt.com/docs/build/documentation), [Wikipedia: Data lineage](https://en.wikipedia.org/wiki/Data_lineage)

---

## Stufe 11: Fortgeschritten

### Webhooks
**Was ist das?** Statt regelmäßig zu fragen "gibt's was Neues?" (Polling), meldet sich der Server von selbst, sobald etwas passiert.

**Genauer:** Du gibst Strava eine URL, und bei jeder neuen, geänderten oder gelöschten Aktivität schickt Strava einen `POST` mit der Art des Ereignisses und der Activity-ID. Die eigentlichen Daten holst du dann gezielt. Damit lösen sich Updates und Deletes (Stufe 3) elegant. Der Haken: Die URL muss aus dem Internet erreichbar sein, du brauchst also einen Server oder einen Tunnel. Und Ereignisse gehen verloren, wenn er gerade nicht läuft, deshalb bleibt ein gelegentlicher Abgleich sinnvoll.

**Beispiel:**
```json
{"object_type": "activity", "object_id": 1360128428, "aspect_type": "update", "updates": {"title": "Neuer Name"}, "owner_id": 134815, "event_time": 1516126040, "subscription_id": 120475}
```

**Mehr:** [Strava: Webhook Events API](https://developers.strava.com/docs/webhooks/)

### Event-getriebene Verarbeitung
**Was ist das?** Die Pipeline läuft nicht nach Uhrzeit, sondern reagiert auf Ereignisse: Eine neue Aktivität kommt rein und löst die Verarbeitung aus.

**Genauer:** Vorteil: Die Daten sind Minuten statt einen Tag alt, und es läuft nur etwas, wenn es etwas zu tun gibt. Nachteil: mehr bewegliche Teile (Empfänger, Warteschlange, Fehlerbehandlung pro Ereignis), und Ereignisse können doppelt oder in falscher Reihenfolge kommen, also braucht es wieder Idempotenz. In Dagster heißen ereignisgesteuerte Auslöser Sensors.

**Mehr:** [Martin Fowler: What do you mean by "Event-Driven"?](https://martinfowler.com/articles/201701-event-driven.html), [Dagster: Sensors](https://dagster.io/docs/guides/automate/sensors)

### Streaming-Grundlagen
**Was ist das?** Daten werden fortlaufend verarbeitet, sobald sie entstehen, statt gesammelt in Paketen (Batch).

**Genauer:** Deine Pipeline ist Batch: einmal am Tag alles Neue. Streaming verarbeitet jedes Ereignis einzeln und sofort, mit Werkzeugen wie Kafka oder Flink. Dabei werden Fragen wichtig, die du teilweise schon kennst: Event Time vs. Processing Time (Stufe 2), verspätete Daten (Stufe 3) und Zeitfenster für Aggregationen. Für Trainingsdaten reicht Batch völlig, Streaming lohnt sich, wenn Sekunden zählen.

**Mehr:** [Tyler Akidau: Streaming 101](https://www.oreilly.com/radar/the-world-beyond-batch-streaming-101/)

### Object Storage und Cloud-Warehouse
**Was ist das?** Object Storage (z. B. Amazon S3) ist ein Dateispeicher in der Cloud, praktisch unbegrenzt und günstig. Ein Cloud-Warehouse (BigQuery, Snowflake, MotherDuck) ist eine Analyse-Datenbank, die jemand anderes für dich betreibt.

**Genauer:** Dein Raw Layer würde von `data/raw/` nach `s3://dein-bucket/raw/` umziehen und dein Warehouse von einer lokalen DuckDB-Datei in die Cloud. Vorteil: läuft unabhängig von deinem Laptop, mehrere Prozesse können zugreifen. Nachteil: Kosten, Zugangsverwaltung, Netzwerk. DuckDB kann direkt aus S3 lesen, und MotherDuck ist DuckDB in der Cloud, also der kleinste Schritt dorthin.

**Mehr:** [Wikipedia: Object storage](https://en.wikipedia.org/wiki/Object_storage), [MotherDuck: Docs](https://motherduck.com/docs/), [DuckDB: S3 API](https://duckdb.org/docs/stable/core_extensions/httpfs/s3api)

### Infrastructure as Code (IaC)
**Was ist das?** Cloud-Ressourcen (Speicher, Server, Rechte) werden in Code-Dateien beschrieben und automatisch angelegt, statt sie in einer Weboberfläche zusammenzuklicken.

**Genauer:** Die Dateien liegen im Git-Repo wie der restliche Code: nachvollziehbar, wiederholbar, reviewbar. "Leg mir einen S3-Bucket mit diesen Rechten an" wird zu ein paar Zeilen Terraform, und `terraform apply` sorgt dafür, dass die Realität dem Code entspricht. Das lohnt sich erst, wenn du wirklich Cloud-Ressourcen nutzt.

**Beispiel:**
```hcl
resource "aws_s3_bucket" "raw" {
  bucket = "strava-data-raw"
}
```

**Mehr:** [Terraform: What is Terraform?](https://developer.hashicorp.com/terraform/intro)

### Joins über Datenquellen
**Was ist das?** Daten aus verschiedenen Systemen über ein gemeinsames Merkmal verbinden, z. B. Aktivitäten mit dem Wetter zur selben Zeit am selben Ort.

**Genauer:** Einen gemeinsamen Schlüssel gibt es selten. Wetter und Aktivität verbindest du über Datum, Stunde und Ort. Dabei musst du Zeitzonen angleichen (Open-Meteo liefert auf Wunsch Ortszeit) und festlegen, was bei fehlenden Treffern passiert. Datenschutz: Koordinaten nur gerundet senden und im Repo nichts davon ablegen.

**Beispiel:**
```
https://archive-api.open-meteo.com/v1/archive?latitude=52.52&longitude=13.41&start_date=2026-10-01&end_date=2026-10-01&hourly=temperature_2m,precipitation&timezone=Europe%2FBerlin
```

**Mehr:** [Open-Meteo: Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api)

### Konforme Dimensionen
**Was ist das?** Dimensionen, die über mehrere Faktentabellen und Quellen hinweg gleich definiert sind und gemeinsam genutzt werden.

**Genauer:** Wenn du Wetter und Aktivitäten nach Woche auswerten willst, müssen beide dieselbe `dim_date` nutzen, mit derselben Definition von "Woche" (Montag oder Sonntag als Start?). Sonst passen die Zahlen nicht zusammen, obwohl jede für sich korrekt ist. Konforme Dimensionen machen aus einzelnen Datensammlungen ein zusammenhängendes Warehouse.

**Mehr:** [Kimball Group: Conformed Dimensions](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/conformed-dimension/)

### Entity Resolution
**Was ist das?** Erkennen, dass zwei Datensätze aus verschiedenen Quellen dasselbe Ding beschreiben, obwohl sie keine gemeinsame ID haben.

**Genauer:** Derselbe Lauf liegt zum Beispiel in Strava und in Apple Health oder Garmin, mit leicht unterschiedlicher Startzeit und Distanz. Du definierst Regeln ("Start weniger als 2 Minuten auseinander und Distanz weniger als 3 % verschieden"), vergibst eine gemeinsame ID und legst fest, welche Quelle bei Widersprüchen gewinnt. Ganz ohne Fehltreffer geht das selten, die Kunst ist, sie messbar zu machen.

**Beispiel:**
```sql
select s.activity_id as strava_id, g.activity_id as garmin_id
from strava_activities as s
join garmin_activities as g
  on abs(epoch(s.started_at) - epoch(g.started_at)) < 120
 and abs(s.distance_km - g.distance_km) / s.distance_km < 0.03;
```

**Mehr:** [Wikipedia: Record linkage](https://en.wikipedia.org/wiki/Record_linkage)
