# Workflow — co system potrafi i jak z niego korzystać

Praktyczny przewodnik po możliwościach tego szablonu Hermes Agent: co można zlecić agentowi z poziomu Telegrama, jak działa automatyczne monitorowanie oraz jakie narzędzia są dostępne.

## Co system potrafi

| Obszar | Opis | Skill / skrypt |
|---|---|---|
| Code review i implementacja | Delegowanie zadań programistycznych do Claude Code CLI (przeglądanie diffów, implementacja issue, poprawki po review) | `skills/claude-code` |
| Konfiguracja providerów coding CLI | Podmiana providera modelu dla Claude Code/Codex/OpenCode (np. na tańszy model przez API kompatybilne z Anthropic) | `skills/coding-cli-provider-config` |
| Zapisywanie wiedzy | Zapisywanie stron internetowych, dokumentów i notatek do Obsidian vault z automatyczną klasyfikacją folderu i wyszukiwaniem duplikatów | `skills/knowledge`, `skills/doc-pipeline` |
| Zakupy | Prowadzenie listy zakupów w vault oraz automatyczne przygotowanie listy zamówienia na zakupy.auchan.pl | `skills/shopping`, `skills/shopping-auchan`, `scripts/auchan/` |
| Monitoring RSS | Automatyczne śledzenie kanałów RSS (FreshRSS) pod kątem słów kluczowych z branży | `scripts/rss/` |
| Monitoring prawa budowlanego | Automatyczne śledzenie Dziennika Ustaw i Monitora Polskiego pod kątem aktów istotnych dla branży AEC | `scripts/prawo/` |
| Śledzenie czasu pracy | Start/stop timera, raporty dzienne/tygodniowe przez Toggl Track API | `skills/toggl-track` |
| Dobór modelu | Automatyczny wybór modelu/narzędzia adekwatnego do złożoności zadania (koszt vs jakość) | `skills/model-routing` |
| Reakcja na wzmianki GitHub | Watchdog + executor obsługujący wzmianki `@sokrates` w issue/komentarzach na śledzonych repozytoriach | `scripts/watchdog/` |

## Jak używać wzmianek @sokrates

Pipeline Sokrates pozwala zlecać Hermesowi zadania bezpośrednio z poziomu GitHuba — bez otwierania Telegrama — poprzez wspomnienie `@sokrates` w treści issue lub komentarza w jednym ze śledzonych repozytoriów.

1. **W nowym issue** — wpisz w tytule lub treści `@sokrates`, opisując zadanie (np. „@sokrates zaimplementuj walidację formularza w src/form.ts”).
2. **W komentarzu do istniejącego issue** — dopisz `@sokrates` wraz z prośbą/pytaniem.
3. Watchdog (uruchamiany co godzinę) wykrywa nową wzmiankę i:
   - wysyła powiadomienie na Telegram z treścią issue/komentarza i linkiem,
   - zapisuje zadanie do wewnętrznej kolejki.
4. Executor (również co godzinę, z ciszą nocną 23:00-08:00) odczytuje kolejkę i przekazuje zadanie agentowi do samodzielnej realizacji — możesz więc po prostu poczekać, nie trzeba nic dodatkowo klikać na Telegramie.
5. Po zrealizowaniu zadania agent edytuje oryginalny komentarz/issue, zamieniając `@sokrates` na `✅ Zrobione przez Sokratesa` — to jednocześnie potwierdzenie wykonania i zabezpieczenie przed ponownym przetworzeniem tej samej wzmianki (watchdog pomija komentarze z tym znacznikiem).

Wskazówka: jedna wzmianka = jedno zadanie. Dla wielu niezależnych zadań lepiej utworzyć osobne issue lub komentarze, niż łączyć je w jednej wiadomości.

## Wzorce cronjobów

Cronjoby w Hermesie definiuje się jako obiekty JSON (patrz `cron/jobs-example.json`) z polami takimi jak `name`, `schedule` (wyrażenie cron), `command`/`script`, `no_agent` oraz opcjonalnie `model`/`provider`.

Dwa podstawowe typy zadań:

- **`no_agent: true`** — zadanie uruchamia skrypt bezpośrednio, bez udziału modelu językowego. Domyślny wybór dla każdego nowego cronjoba — jeśli zadanie da się opisać jako deterministyczną operację (pobierz, przefiltruj, zapisz, wyślij), nie potrzebuje LLM.
- **`no_agent: false` (lub pominięte)** — zadanie przekazywane jest agentowi wraz z kontekstem (np. zawartością kolejki) i ma za zadanie wygenerować treść (podsumowanie, notatkę, odpowiedź). Używane tylko na etapie „digest” w każdym z trzech pipeline'ów.

Uwaga dotycząca modelu w cronjobach: jeśli zadanie pomija pola `model`/`provider`, Hermes „zamraża” (snapshotuje) domyślny model globalny w momencie utworzenia zadania. Jeśli później zmienisz domyślny model globalnie, taki cronjob **nie** przełączy się automatycznie — zamiast tego zawiedzie w sposób bezpieczny (nie wykona przebiegu) i wyśle alert z prośbą o jawne przypięcie modelu/providera. Dlatego zalecane jest jawne ustawienie `model`/`provider` w każdym cronjobie typu digest, zamiast polegania na wartości domyślnej.

Wzorzec trzech kroków (watchdog -> digest -> send) opisany jest szczegółowo w [docs/architektura.md](architektura.md) — w praktyce oznacza to zazwyczaj 2-3 osobne wpisy cron per pipeline, uruchamiane jeden po drugim (np. co godzinę watchdog, zaraz po nim digest, zaraz po nim send), tak aby kolejka zapisana przez watchdog zdążyła zostać odczytana przez kolejny krok.

## Dostępne narzędzia i ich przeznaczenie

| Narzędzie | Przeznaczenie |
|---|---|
| Skrypty w `scripts/` | Deterministyczne operacje bez LLM: pobieranie danych z API, filtrowanie, logowanie do serwisów, wysyłka wiadomości |
| `agent-browser` (CLI) | Sterowanie przeglądarką z poziomu terminala — logowanie do serwisów z chronionymi formularzami (np. Auchan), klikanie po referencjach ze snapshotu accessibility tree, gdy standardowe selektory CSS/tekst zawodzą |
| `gh` (GitHub CLI) | Odczyt i edycja issue/komentarzy dla pipeline'u Sokrates |
| Obsidian vault (odczyt/zapis plików) | Trwałe przechowywanie wiedzy: streszczenia stron, digesty prawne, lista zakupów, notatki własne użytkownika |
| Paperless-ngx (REST API) | Archiwum surowych dokumentów PDF z OCR i pełnotekstowym wyszukiwaniem — różne przeznaczenie niż vault (patrz poniżej) |
| Claude Code CLI | Delegowanie złożonych zadań programistycznych (wieloplikowe zmiany, refaktoryzacje, PR-y) |
| Toggl Track API | Start/stop timera, raporty czasu pracy |
| OpenRouter | Routing do modeli językowych (domyślnie tańszy model do zadań bieżących, mocniejszy do zadań złożonych) |

### Vault vs. Paperless vs. digest RSS — trzy różne przeznaczenia

Łatwo pomylić te trzy miejsca przechowywania danych — każde służy innemu celowi:

- **Obsidian vault** — wiedza w wersji przetworzonej: streszczenia, notatki, wikilinki do powiązanych tematów. Jedyne surowe pliki, jakie tam trafiają, to PDF-y aktów prawnych (żeby notatka digestu mogła się do nich odwołać).
- **Paperless-ngx** — archiwum surowych dokumentów z OCR i pełnotekstowym wyszukiwaniem. Właściwe miejsce, gdy potrzeba „znajdź dokładny dokument/frazę”, nigdy do streszczeń.
- **Digest RSS** — z natury efemeryczny: wysłany raz na Telegram, kolejka czyszczona po wysłaniu, nic nie jest zapisywane na trwałe (chyba że użytkownik jawnie poprosi o zapisanie konkretnego linku do vaulta).

## Uwagi końcowe

- Większość odpowiedzi agenta jest po polsku, bez emoji i bez pauzy długiej (em-dash) — zgodnie z zasadami w `SOUL.md`.
- Każdy nowy cronjob projektuj domyślnie jako `no_agent`; wariant z agentem wymaga uzasadnienia, dlaczego skrypt deterministyczny nie wystarczy.
- Przed dodaniem nowego pipeline'u monitorującego rozważ, czy pasuje do wzorca watchdog -> digest -> send opisanego w architekturze — w większości przypadków będzie pasował.
