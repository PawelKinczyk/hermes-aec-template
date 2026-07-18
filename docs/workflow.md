# Workflow - co system potrafi i jak z niego korzystac

Praktyczny przewodnik po mozliwosciach tego szablonu Hermes Agent: co mozna zlecic agentowi z poziomu Telegrama, jak dziala automatyczne monitorowanie oraz jakie narzedzia sa dostepne.

## Co system potrafi

| Obszar | Opis | Skill / skrypt |
|---|---|---|
| Code review i implementacja | Delegowanie zadan programistycznych do Claude Code CLI (przegladanie diffow, implementacja issue, poprawki po review) | `skills/claude-code` |
| Konfiguracja providerow coding CLI | Podmiana providera modelu dla Claude Code/Codex/OpenCode (np. na tanszy model przez API kompatybilne z Anthropic) | `skills/coding-cli-provider-config` |
| Zapisywanie wiedzy | Zapisywanie stron internetowych, dokumentow i notatek do Obsidian vault z automatyczna klasyfikacja folderu i wyszukiwaniem duplikatow | `skills/knowledge`, `skills/doc-pipeline` |
| Zakupy | Prowadzenie listy zakupow w vault oraz automatyczne przygotowanie listy zamowienia na zakupy.auchan.pl | `skills/shopping`, `skills/shopping-auchan`, `scripts/auchan/` |
| Monitoring RSS | Automatyczne sledzenie kanalow RSS (FreshRSS) pod katem slow kluczowych z branzy | `scripts/rss/` |
| Monitoring prawa budowlanego | Automatyczne sledzenie Dziennika Ustaw i Monitora Polskiego pod katem aktow istotnych dla branzy AEC | `scripts/prawo/` |
| Sledzenie czasu pracy | Start/stop timera, raporty dzienne/tygodniowe przez Toggl Track API | `skills/toggl-track` |
| Dobor modelu | Automatyczny wybor modelu/narzedzia adekwatnego do zlozonosci zadania (koszt vs jakosc) | `skills/model-routing` |
| Reakcja na wzmianki GitHub | Watchdog + executor obslugujacy wzmianki `@sokrates` w issue/komentarzach na sledzonych repozytoriach | `scripts/watchdog/` |

## Jak uzywac wzmianek @sokrates

Pipeline Sokrates pozwala zlecac Hermesowi zadania bezposrednio z poziomu GitHuba - bez otwierania Telegrama - poprzez wspomnienie `@sokrates` w tresci issue lub komentarza w jednym ze sledzonych repozytoriow.

1. **W nowym issue** - wpisz w tytule lub tresci `@sokrates`, opisujac zadanie (np. "@sokrates zaimplementuj walidacje formularza w src/form.ts").
2. **W komentarzu do istniejacego issue** - dopisz `@sokrates` wraz z prosba/pytaniem.
3. Watchdog (uruchamiany co godzine) wykrywa nowa wzmianke i:
   - wysyla powiadomienie na Telegram z tresci issue/komentarza i linkiem,
   - zapisuje zadanie do wewnetrznej kolejki.
4. Executor (rowniez co godzine, z cisza nocna 23:00-08:00) odczytuje kolejke i przekazuje zadanie agentowi do samodzielnej realizacji - mozesz wiec po prostu poczekac, nie trzeba nic dodatkowo klikac na Telegramie.
5. Po zrealizowaniu zadania agent edytuje oryginalny komentarz/issue, zamieniajac `@sokrates` na `✅ Zrobione przez Sokratesa` - to jednoczesnie potwierdzenie wykonania i zabezpieczenie przed ponownym przetworzeniem tej samej wzmianki (watchdog pomija komentarze z tym znacznikiem).

Wskazowka: jedna wzmianka = jedno zadanie. Dla wielu niezaleznych zadan lepiej utworzyc osobne issue lub komentarze, niz laczyc je w jednej wiadomosci.

## Wzorce cronjobow

Cronjoby w Hermesie definiuje sie jako obiekty JSON (patrz `cron/jobs-example.json`) z polami takimi jak `name`, `schedule` (wyrazenie cron), `command`/`script`, `no_agent` oraz opcjonalnie `model`/`provider`.

Dwa podstawowe typy zadan:

- **`no_agent: true`** - zadanie uruchamia skrypt bezposrednio, bez udzialu modelu jezykowego. Domyslny wybor dla kazdego nowego cronjoba - jesli zadanie da sie opisac jako deterministyczna operacje (pobierz, przefiltruj, zapisz, wyslij), nie potrzebuje LLM.
- **`no_agent: false` (lub pominiete)** - zadanie przekazywane jest agentowi wraz z kontekstem (np. zawartoscia kolejki) i ma za zadanie wygenerowac tresc (podsumowanie, notatke, odpowiedz). Uzywane tylko na etapie "digest" w kazdym z trzech pipeline'ow.

Uwaga dotyczaca modelu w cronjobach: jesli zadanie pomija pola `model`/`provider`, Hermes "zamraza" (snapshotuje) domyslny model globalny w momencie utworzenia zadania. Jesli pozniej zmienisz domyslny model globalnie, taki cronjob **nie** przelaczy sie automatycznie - zamiast tego zawiedzie w sposob bezpieczny (nie wykona przebiegu) i wysle alert z prosba o jawne przypiecie modelu/providera. Dlatego zalecane jest jawne ustawienie `model`/`provider` w kazdym cronjobie typu digest, zamiast polegania na wartosci domyslnej.

Wzorzec trzech krokow (watchdog -> digest -> send) opisany jest szczegolowo w [docs/architektura.md](architektura.md) - w praktyce oznacza to zazwyczaj 2-3 osobne wpisy cron per pipeline, uruchamiane jeden po drugim (np. co godzine watchdog, zaraz po nim digest, zaraz po nim send), tak aby kolejka zapisana przez watchdog zdazyla zostac odczytana przez kolejny krok.

## Dostepne narzedzia i ich przeznaczenie

| Narzedzie | Przeznaczenie |
|---|---|
| Skrypty w `scripts/` | Deterministyczne operacje bez LLM: pobieranie danych z API, filtrowanie, logowanie do serwisow, wysylka wiadomosci |
| `agent-browser` (CLI) | Sterowanie przegladarka z poziomu terminala - logowanie do serwisow z chronionymi formularzami (np. Auchan), klikanie po referencjach ze snapshotu accessibility tree, gdy standardowe selektory CSS/tekst zawodza |
| `gh` (GitHub CLI) | Odczyt i edycja issue/komentarzy dla pipeline'u Sokrates |
| Obsidian vault (odczyt/zapis plikow) | Trwale przechowywanie wiedzy: streszczenia stron, digesty prawne, lista zakupow, notatki wlasne uzytkownika |
| Paperless-ngx (REST API) | Archiwum surowych dokumentow PDF z OCR i pelnotekstowym wyszukiwaniem - rozne przeznaczenie niz vault (patrz ponizej) |
| Claude Code CLI | Delegowanie zlozonych zadan programistycznych (wieloplikowe zmiany, refaktoryzacje, PR-y) |
| Toggl Track API | Start/stop timera, raporty czasu pracy |
| OpenRouter | Routing do modeli jezykowych (domyslnie tanszy model do zadan biezacych, mocniejszy do zadan zlozonych) |

### Vault vs. Paperless vs. digest RSS - trzy rozne przeznaczenia

Latwo pomylic te trzy miejsca przechowywania danych - kazde sluzy innemu celowi:

- **Obsidian vault** - wiedza w wersji przetworzonej: streszczenia, notatki, wikilinki do powiazanych tematow. Jedyne surowe pliki, jakie tam trafiaja, to PDF-y aktow prawnych (zeby notatka digestu mogla sie do nich odwolac).
- **Paperless-ngx** - archiwum surowych dokumentow z OCR i pelnotekstowym wyszukiwaniem. Wlasciwe miejsce, gdy potrzeba "znajdz dokladny dokument/fraze", nigdy do streszczen.
- **Digest RSS** - z natury efemeryczny: wyslany raz na Telegram, kolejka czyszczona po wyslaniu, nic nie jest zapisywane na trwale (chyba ze uzytkownik jawnie poprosi o zapisanie konkretnego linku do vaulta).

## Uwagi koncowe

- Wiekszosc odpowiedzi agenta jest po polsku, bez emoji i bez pauzy dlugiej (em-dash) - zgodnie z zasadami w `SOUL.md`.
- Kazdy nowy cronjob projektuj domyslnie jako `no_agent`; wariant z agentem wymaga uzasadnienia, dlaczego skrypt deterministyczny nie wystarczy.
- Przed dodaniem nowego pipeline'u monitorujacego rozwaz, czy pasuje do wzorca watchdog -> digest -> send opisanego w architekturze - w wiekszosci przypadkow bedzie pasowal.
