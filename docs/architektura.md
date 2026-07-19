# Architektura

Opis architektury Hermes Agent w konfiguracji z tego szablonu: składniki systemu, wzorzec pipeline'ów cronowych oraz działanie skilli i skryptów.

## Przegląd ogólny

Hermes składa się z trzech warstw, które współpracują ze sobą:

```
                    ┌─────────────────────────┐
                    │        Telegram          │
                    │  (kanał wejścia/wyjścia) │
                    └────────────┬─────────────┘
                                 │
                                 ▼
┌───────────────────────────────────────────────────────────┐
│                      Hermes Agent (gateway)                │
│  - odbiera wiadomości z Telegrama                           │
│  - wybiera model (OpenRouter: DeepSeek Flash/Pro, Claude...) │
│  - dobiera i wykonuje skille (skills/)                      │
│  - ma dostęp do narzędzi: pliki, przeglądarka, terminal      │
└───────────────┬───────────────────────────┬─────────────────┘
                │                           │
                ▼                           ▼
      ┌──────────────────┐        ┌────────────────────┐
      │   Cron pipeline   │        │   Narzędzia/tools    │
      │  (watchdog->digest │        │  scripts/ (no_agent) │
      │   ->send, co N min)│        │  agent-browser, gh,  │
      └─────────┬──────────┘        │  Obsidian vault I/O   │
                │                   └──────────┬─────────────┘
                ▼                              │
      ┌──────────────────┐                     │
      │  Zewnętrzne API    │◄────────────────────┘
      │  Sejm, FreshRSS,   │
      │  GitHub, Toggl,    │
      │  Paperless-ngx     │
      └──────────────────┘
```

- **Gateway** — proces Hermesa nasłuchujący na wiadomości z Telegrama (i innych skonfigurowanych kanałów) oraz uruchamiający zaplanowane cronjoby. To on decyduje, który model wywołać i który skill zastosować do danego zadania (patrz skill `model-routing`).
- **Cron pipeline** — wewnętrzny scheduler Hermesa, który uruchamia zdefiniowane zadania (`cron/jobs-example.json`) w regularnych odstępach czasu, niezależnie od tego, czy użytkownik akurat pisze na Telegramie.
- **Tools** — zestaw narzędzi dostępnych agentowi: odczyt/zapis plików (w tym Obsidian vault), wykonywanie poleceń powłoki, sterowanie przeglądarką (`agent-browser`), wywołania API (GitHub CLI `gh`, REST API różnych serwisów).

## Wzorzec pipeline'u: watchdog -> digest -> send

Wszystkie trzy monitorujące pipeline'y w tym szablonie (Sokrates, RSS, Prawo) używają tego samego trójstopniowego wzorca, zaprojektowanego tak, aby minimalizować koszt tokenów LLM:

```
[1] WATCHDOG (no_agent, zero tokenów)
     |  skrypt (Python/Bash) odpytuje źródło danych,
     |  filtruje po słowach kluczowych/regule,
     |  zapisuje trafienia do kolejki (state/*.json)
     v
[2] DIGEST (agent, używa LLM)
     |  agent czyta kolejkę, generuje czytelne podsumowanie
     |  po polsku, zapisuje je do pliku wiadomości
     |  (state/*-message.txt) - i tylko wtedy, gdy są trafienia
     v
[3] SEND (no_agent, zero tokenów)
     |  skrypt odczytuje plik wiadomości, wypisuje go na stdout
     |  (Hermes dostarcza stdout na Telegram), czyści plik
     v
   Telegram (użytkownik)
```

Kluczowe zasady tego wzorca:

- **Watchdog nigdy nie używa LLM.** To zwykły skrypt, który pobiera dane ze źródła (API, RSS, GitHub), filtruje je deterministycznie (lista słów kluczowych, znaczniki „już obsłużone”) i zapisuje wynik do pliku stanu. Koszt: zero tokenów, niezależnie od częstotliwości uruchamiania.
- **Digest korzysta z LLM tylko wtedy, gdy jest cokolwiek do podsumowania.** Jeśli kolejka jest pusta, krok digestu nie generuje kosztu (lub jest pomijany w całości).
- **Send jest zawsze `no_agent`.** To tylko dostarczenie gotowego tekstu — nie ma powodu płacić za model do przepisania pliku na stdout.
- **Cisza jako domyślny stan.** Każdy watchdog kończy się kodem wyjścia 0 i pustym stdout, gdy nie ma nic nowego — Hermes nie wysyła wtedy żadnej wiadomości. Użytkownik dostaje powiadomienie tylko wtedy, gdy naprawdę jest coś nowego.
- **Stan trwały w plikach JSON.** Każdy watchdog pamięta, co już widział (`*-seen.json`, znaczniki czasu, ID przetworzonych elementów), żeby nigdy nie przetwarzać tego samego elementu dwa razy i nigdy nic nie zgubić przy błędzie sieciowym (kod wyjścia != 0 = stan NIE jest modyfikowany).

## Jak działają skille

Skille (`skills/*/SKILL.md`) to pliki markdown z metadanymi (nazwa, opis, wersja) i procedurą w języku naturalnym. Hermes nie wywołuje ich jak funkcji z jawnym API — sam decyduje, który skill pasuje do bieżącego zadania na podstawie pola `description` w nagłówku (frontmatter YAML) oraz kontekstu rozmowy.

Typowa zawartość skilla:
- **Kiedy użyć** (czasem explicite „tylko na wyraźne polecenie”, np. `doc-pipeline`).
- **Procedura krok po kroku** — w jakiej kolejności wykonać działania, jakich narzędzi użyć.
- **Twarde ograniczenia** — czego nigdy nie robić (np. `shopping-auchan`: nigdy nie klikaj „Dodaj do koszyka”, bo to wyzwala blokadę WAF).
- **Format odpowiedzi** — jak i w jakim języku raportować wynik użytkownikowi.

Skille mogą odwoływać się do siebie nawzajem (`related_skills` w metadanych) i do skryptów w `scripts/` (wywoływanych przez agenta poprzez terminal).

## Jak integrują się skrypty

Skrypty w `scripts/` dzielą się na dwie role:

1. **Wywoływane przez cronjoby** (`no_agent`) — watchdogi i kroki „send” opisane wyżej. Uruchamiane bezpośrednio przez scheduler Hermesa, bez udziału modelu językowego.
2. **Wywoływane przez agenta w trakcie wykonywania skilla** — np. `auchan-login.sh` i `auchan-search-add.sh` są uruchamiane przez agenta krok po kroku podczas realizacji skilla `shopping-auchan`, ponieważ wymagają logiki warunkowej i interpretacji wyników (których zwykły skrypt nie podejmie sam).

Każdy skrypt komunikuje wynik przez konwencję stdout/kod wyjścia opisaną w komentarzu na początku pliku (np. `ADDED: <nazwa>` / `NOT_FOUND: <query>` / `ERROR: <szczegoly>`), dzięki czemu zarówno cron, jak i agent mogą jednoznacznie zinterpretować rezultat bez zgadywania.

## Trzy pipeline'y monitorujące

### 1. Sokrates (watchdog GitHuba)

Monitoruje wskazane repozytoria GitHub pod kątem nowych wzmianek `@sokrates` w issue i komentarzach.

```
sokrates-watchdog.sh (co godzinę)
  -> gh api (pobiera nowe issue/komentarze od ostatniego sprawdzenia)
  -> sokrates-filter.py (filtruje wzmianki, pomija już oznaczone jako zrobione,
                          zapisuje zadania do kolejki dla Job 2)
  -> stdout niepusty = Hermes wysyła powiadomienie na Telegram

sokrates-executor.sh (co godzinę, cisza nocna 23:00-08:00)
  -> odczytuje kolejkę zadań i przekazuje agentowi do realizacji
  -> po wykonaniu: sokrates-done.sh oznacza komentarz jako
     "✅ Zrobione przez Sokratesa" (mechanizm anty-pętli - watchdog
     pomija komentarze z tym znacznikiem)
```

To jedyny z trzech pipeline'ów, który ma dwa niezależne zadania cron (watchdog powiadamiający + executor działający autonomicznie) plus mechanizm zapobiegający nieskończonej pętli powiadomień.

### 2. RSS (watchdog FreshRSS)

Monitoruje nieprzeczytane wpisy w lokalnej instancji FreshRSS pod kątem słów kluczowych.

```
rss-watchdog.py (co N minut)
  -> loguje się do FreshRSS (Google Reader-compatible API)
  -> pobiera nieprzeczytane wpisy, dopasowuje do rss-keywords.txt
  -> trafienia -> kolejka (rss-queue.json)
  -> wszystkie pobrane wpisy oznacza jako przeczytane (trafienie czy nie)

[agent digest step] czyta kolejkę -> generuje podsumowanie po polsku
                      -> zapisuje do rss-digest-message.txt

rss-digest-send.sh (no_agent)
  -> wypisuje treść pliku wiadomości na stdout, czyści plik
```

### 3. Prawo (watchdog aktów prawnych)

Monitoruje Dziennik Ustaw i Monitor Polski przez oficjalne API `api.sejm.gov.pl` (ELI) pod kątem aktów związanych ze słowami kluczowymi z branży budowlanej/HVAC.

```
prawo-watchdog.py (raz dziennie)
  -> pobiera listę aktów DU/MP dla bieżącego roku
  -> dla nowych pozycji: pobiera szczegóły, dopasowuje słowa kluczowe
  -> trafienia: pobiera PDF do vaulta (Prawo/PDF/), wysyła do Paperless-ngx
     (REST API, automatyczne tagowanie: ustawa/rozporzadzenie/tekst-jednolity)
  -> wykrywa akty uchylające starsze przepisy -> usuwa nieaktualny PDF
     z vaulta, oznacza dokument w Paperless jako "zastapiony"
  -> trafienia -> kolejka (prawo-queue.json)

[agent digest step] czyta kolejkę -> tworzy notatkę w vault
                      (Prawo/YYYY-MM-DD-digest.md) -> zapisuje
                      podsumowanie do prawo-digest-message.txt

prawo-digest-send.sh (no_agent)
  -> wypisuje treść pliku wiadomości na stdout, czyści plik
```

Ten pipeline jako jedyny dual-writeuje — PDF trafia zarówno do Obsidian vault, jak i do archiwum Paperless-ngx (patrz `docs/workflow.md` po rozróżnienie między tymi dwoma systemami).

Uwaga: nazwy tagów Paperless (`ustawa`, `rozporzadzenie`, `tekst-jednolity`, `zastapiony`) celowo nie zawierają polskich znaków — to literalne wartości używane przez `scripts/prawo/prawo-watchdog.py`.

## Podsumowanie zasad projektowych

- Każde zadanie deterministyczne -> skrypt, nigdy LLM.
- Każdy cronjob domyślnie projektowany jako `no_agent`; wariant z agentem wymaga uzasadnienia.
- Cisza jest poprawnym stanem końcowym — powiadomienie wysyłane jest tylko, gdy jest coś realnie nowego.
- Stan zawsze trwały w plikach JSON w `~/.hermes/state/`, nigdy tylko w pamięci procesu.
