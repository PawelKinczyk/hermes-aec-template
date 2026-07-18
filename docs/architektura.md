# Architektura

Opis architektury Hermes Agent w konfiguracji z tego szablonu: skladniki systemu, wzorzec pipeline'ow cronowych oraz dzialanie skilli i skryptow.

## Przeglad ogolny

Hermes sklada sie z trzech warstw, ktore wspolpracuja ze soba:

```
                    ┌─────────────────────────┐
                    │        Telegram          │
                    │  (kanal wejscia/wyjscia) │
                    └────────────┬─────────────┘
                                 │
                                 ▼
┌───────────────────────────────────────────────────────────┐
│                      Hermes Agent (gateway)                │
│  - odbiera wiadomosci z Telegrama                           │
│  - wybiera model (OpenRouter: DeepSeek Flash/Pro, Claude...) │
│  - dobiera i wykonuje skille (skills/)                      │
│  - ma dostep do narzedzi: pliki, przegladarka, terminal      │
└───────────────┬───────────────────────────┬─────────────────┘
                │                           │
                ▼                           ▼
      ┌──────────────────┐        ┌────────────────────┐
      │   Cron pipeline   │        │   Narzedzia/tools    │
      │  (watchdog->digest │        │  scripts/ (no_agent) │
      │   ->send, co N min)│        │  agent-browser, gh,  │
      └─────────┬──────────┘        │  Obsidian vault I/O   │
                │                   └──────────┬─────────────┘
                ▼                              │
      ┌──────────────────┐                     │
      │  Zewnetrzne API    │◄────────────────────┘
      │  Sejm, FreshRSS,   │
      │  GitHub, Toggl,    │
      │  Paperless-ngx     │
      └──────────────────┘
```

- **Gateway** - proces Hermesa nasluchujacy na wiadomosci z Telegrama (i innych skonfigurowanych kanalow) oraz uruchamiajacy zaplanowane cronjoby. To on decyduje, ktory model wywolac i ktory skill zastosowac do danego zadania (patrz skill `model-routing`).
- **Cron pipeline** - wewnetrzny scheduler Hermesa, ktory uruchamia zdefiniowane zadania (`cron/jobs-example.json`) w regularnych odstepach czasu, niezaleznie od tego, czy uzytkownik akurat pisze na Telegramie.
- **Tools** - zestaw narzedzi dostepnych agentowi: odczyt/zapis plikow (w tym Obsidian vault), wykonywanie polecen powloki, sterowanie przegladarka (`agent-browser`), wywolania API (GitHub CLI `gh`, REST API roznych serwisow).

## Wzorzec pipeline'u: watchdog -> digest -> send

Wszystkie trzy monitorujace pipeline'y w tym szablonie (Sokrates, RSS, Prawo) uzywaja tego samego trojstopniowego wzorca, zaprojektowanego tak, aby minimalizowac koszt tokenow LLM:

```
[1] WATCHDOG (no_agent, zero tokenow)
     |  skrypt (Python/Bash) odpytuje zrodlo danych,
     |  filtruje po sfowach kluczowych/regule,
     |  zapisuje trafienia do kolejki (state/*.json)
     v
[2] DIGEST (agent, uzywa LLM)
     |  agent czyta kolejke, generuje czytelne podsumowanie
     |  po polsku, zapisuje je do pliku wiadomosci
     |  (state/*-message.txt) - i tylko wtedy, gdy sa trafienia
     v
[3] SEND (no_agent, zero tokenow)
     |  skrypt odczytuje plik wiadomosci, wypisuje go na stdout
     |  (Hermes dostarcza stdout na Telegram), czysci plik
     v
   Telegram (uzytkownik)
```

Kluczowe zasady tego wzorca:

- **Watchdog nigdy nie uzywa LLM.** To zwykly skrypt, ktory pobiera dane ze zrodla (API, RSS, GitHub), filtruje je deterministycznie (lista slow kluczowych, znaczniki "juz obsluzone") i zapisuje wynik do pliku stanu. Koszt: zero tokenow, niezaleznie od czestotliwosci uruchamiania.
- **Digest korzysta z LLM tylko wtedy, gdy jest cokolwiek do podsumowania.** Jesli kolejka jest pusta, krok digestu nie generuje kosztu (lub jest pomijany w calosci).
- **Send jest zawsze `no_agent`.** To tylko dostarczenie gotowego tekstu - nie ma powodu placic za model do przepisania pliku na stdout.
- **Cisza jako domyslny stan.** Kazdy watchdog konczy sie kodem wyjscia 0 i pustym stdout, gdy nie ma nic nowego - Hermes nie wysyla wtedy zadnej wiadomosci. Uzytkownik dostaje powiadomienie tylko wtedy, gdy naprawde jest cos nowego.
- **Stan trwaly w plikach JSON.** Kazdy watchdog pamieta, co juz widzial (`*-seen.json`, znaczniki czasu, ID przetworzonych elementow), zeby nigdy nie przetwarzac tego samego elementu dwa razy i nigdy nic nie zgubic przy bledzie sieciowym (kod wyjscia != 0 = stan NIE jest modyfikowany).

## Jak dzialaja skille

Skille (`skills/*/SKILL.md`) to pliki markdown z metadanymi (nazwa, opis, wersja) i procedura w jezyku naturalnym. Hermes nie wywoluje ich jak funkcji z jawnym API - sam decyduje, ktory skill pasuje do biezacego zadania na podstawie pola `description` w naglowku (frontmatter YAML) oraz kontekstu rozmowy.

Typowa zawartosc skilla:
- **Kiedy uzyc** (czasem explicite "tylko na wyrazne polecenie", np. `doc-pipeline`).
- **Procedura krok po kroku** - w jakiej kolejnosci wykonac dzialania, jakich narzedzi uzyc.
- **Twarde ograniczenia** - czego nigdy nie robic (np. `shopping-auchan`: nigdy nie klikaj "Dodaj do koszyka", bo to wyzwala blokade WAF).
- **Format odpowiedzi** - jak i w jakim jezyku raportowac wynik uzytkownikowi.

Skille moga odwolywac sie do siebie nawzajem (`related_skills` w metadanych) i do skryptow w `scripts/` (wywolywanych przez agenta poprzez terminal).

## Jak integruja sie skrypty

Skrypty w `scripts/` dziela sie na dwie role:

1. **Wywolywane przez cronjoby** (`no_agent`) - watchdogi i kroki "send" opisane wyzej. Uruchamiane bezposrednio przez scheduler Hermesa, bez udzialu modelu jezykowego.
2. **Wywolywane przez agenta w trakcie wykonywania skilla** - np. `auchan-login.sh` i `auchan-search-add.sh` sa uruchamiane przez agenta krok po kroku podczas realizacji skilla `shopping-auchan`, poniewaz wymagaja logiki warunkowej i interpretacji wynikow (ktorych zwykly skrypt nie podejmie sam).

Kazdy skrypt komunikuje wynik przez konwencje stdout/kod wyjscia opisana w komentarzu na poczatku pliku (np. `ADDED: <nazwa>` / `NOT_FOUND: <query>` / `ERROR: <szczegoly>`), dzieki czemu zarowno cron, jak i agent moga jednoznacznie zinterpretowac rezultat bez zgadywania.

## Trzy pipeline'y monitorujace

### 1. Sokrates (watchdog GitHuba)

Monitoruje wskazane repozytoria GitHub pod katem nowych wzmianek `@sokrates` w issue i komentarzach.

```
sokrates-watchdog.sh (co godzine)
  -> gh api (pobiera nowe issue/komentarze od ostatniego sprawdzenia)
  -> sokrates-filter.py (filtruje wzmianki, pomija juz oznaczone jako zrobione,
                          zapisuje zadania do kolejki dla Job 2)
  -> stdout niepusty = Hermes wysyla powiadomienie na Telegram

sokrates-executor.sh (co godzine, cisza nocna 23:00-08:00)
  -> odczytuje kolejke zadan i przekazuje agentowi do realizacji
  -> po wykonaniu: sokrates-done.sh oznacza komentarz jako
     "✅ Zrobione przez Sokratesa" (mechanizm anty-petli - watchdog
     pomija komentarze z tym znacznikiem)
```

To jedyny z trzech pipeline'ow, ktory ma dwa niezalezne zadania cron (watchdog powiadamiajacy + executor dzialajacy autonomicznie) plus mechanizm zapobiegajacy nieskonczonej petli powiadomien.

### 2. RSS (watchdog FreshRSS)

Monitoruje nieprzeczytane wpisy w lokalnej instancji FreshRSS pod katem slow kluczowych.

```
rss-watchdog.py (co N minut)
  -> loguje sie do FreshRSS (Google Reader-compatible API)
  -> pobiera nieprzeczytane wpisy, dopasowuje do rss-keywords.txt
  -> trafienia -> kolejka (rss-queue.json)
  -> wszystkie pobrane wpisy oznacza jako przeczytane (trafienie czy nie)

[agent digest step] czyta kolejke -> generuje podsumowanie po polsku
                      -> zapisuje do rss-digest-message.txt

rss-digest-send.sh (no_agent)
  -> wypisuje tresc pliku wiadomosci na stdout, czysci plik
```

### 3. Prawo (watchdog aktow prawnych)

Monitoruje Dziennik Ustaw i Monitor Polski przez oficjalne API `api.sejm.gov.pl` (ELI) pod katem aktow zwiazanych ze slowami kluczowymi z branzy budowlanej/HVAC.

```
prawo-watchdog.py (raz dziennie)
  -> pobiera liste aktow DU/MP dla biezacego roku
  -> dla nowych pozycji: pobiera szczegoly, dopasowuje slowa kluczowe
  -> trafienia: pobiera PDF do vaulta (Prawo/PDF/), wysyla do Paperless-ngx
     (REST API, automatyczne tagowanie: ustawa/rozporzadzenie/tekst-jednolity)
  -> wykrywa akty uchylajace starsze przepisy -> usuwa nieaktualny PDF
     z vaulta, oznacza dokument w Paperless jako "zastapiony"
  -> trafienia -> kolejka (prawo-queue.json)

[agent digest step] czyta kolejke -> tworzy notatke w vault
                      (Prawo/YYYY-MM-DD-digest.md) -> zapisuje
                      podsumowanie do prawo-digest-message.txt

prawo-digest-send.sh (no_agent)
  -> wypisuje tresc pliku wiadomosci na stdout, czysci plik
```

Ten pipeline jako jedyny dual-writeuje - PDF trafia zarowno do Obsidian vault, jak i do archiwum Paperless-ngx (patrz `docs/workflow.md` po rozroznienie miedzy tymi dwoma systemami).

## Podsumowanie zasad projektowych

- Kazde zadanie deterministyczne -> skrypt, nigdy LLM.
- Kazdy cronjob domyslnie projektowany jako `no_agent`; wariant z agentem wymaga uzasadnienia.
- Cisza jest poprawnym stanem koncowym - powiadomienie wysylane jest tylko, gdy jest cos realnie nowego.
- Stan zawsze trwaly w plikach JSON w `~/.hermes/state/`, nigdy tylko w pamieci procesu.
