# hermes-aec-template

Szablon konfiguracji [Hermes Agent](https://github.com/hermes-agent/hermes-agent) dla inzyniera branzy AEC (architektura, konstrukcje, budownictwo). Zawiera gotowe skille, skrypty i wzorce cronjobow dopasowane do pracy inzyniera: monitoring aktow prawnych, monitoring RSS branzowego, obsluge zakupow, sledzenie czasu pracy oraz orkiestracje coding agentow.

Repozytorium jest publiczne i **sanitized** - wszystkie dane osobiste, tokeny, sciezki i adresy zostaly zastapione placeholderami. Przed uzyciem trzeba je uzupelnic wlasnymi wartosciami (patrz [INSTALL.md](INSTALL.md)).

## Czym jest Hermes

Hermes Agent to autonomiczny agent AI dzialajacy w tle na wlasnym sprzecie (najczesciej Raspberry Pi), pelniacy funkcje osobistego asystenta dostepnego przez Telegram. W odroznieniu od czatu w przegladarce, Hermes:

- dziala 24/7 i reaguje na wiadomosci z Telegrama w dowolnym momencie,
- wykonuje zadania cykliczne (cronjoby) bez udzialu uzytkownika - np. sprawdza nowe akty prawne, kanaly RSS, wzmianki na GitHubie,
- ma dostep do lokalnych narzedzi: systemu plikow, przegladarki (agent-browser), skryptow powloki, API zewnetrznych serwisow,
- korzysta z modeli jezykowych przez OpenRouter (domyslnie tanie modele do zadan biezacych, drozsze/lepsze do zadan zlozonych),
- przechowuje wiedze w istniejacym Obsidian vault uzytkownika (notatki, streszczenia, digesty),
- moze delegowac zadania programistyczne do Claude Code CLI.

Zachowanie agenta opisuje plik `SOUL.md` (zasady dzialania, jezyk, styl odpowiedzi), a konfiguracje techniczna `config.yaml` (model, klucze API, integracje). Skille (`skills/`) to instrukcje w jezyku naturalnym, ktore Hermes sam dobiera do zadania. Skrypty (`scripts/`) to deterministyczne operacje bez udzialu LLM, uruchamiane recznie lub z cronjobow.

## Wymagania wstepne

- **Raspberry Pi 5** (4 GB+ RAM) z zainstalowanym Raspberry Pi OS (64-bit) - lub inny komputer z Linuksem dzialajacy 24/7.
- **Konto OpenRouter** (https://openrouter.ai) z kluczem API i doladowanym budzetem - Hermes korzysta z modeli przez ten routing.
- **Bot Telegram** utworzony przez [@BotFather](https://t.me/BotFather) - potrzebny token bota oraz ID czatu/uzytkownika.
- **Obsidian vault** (istniejacy lub nowy) dostepny lokalnie na tym samym urzadzeniu - Hermes zapisuje w nim notatki bezposrednio na dysku.
- Opcjonalnie: konto GitHub (dla pipeline'u Sokrates), instancja FreshRSS (dla pipeline'u RSS), konto Toggl Track (do time trackingu).

## Szybki start

1. Sklonuj to repozytorium na docelowej maszynie (RPi 5 lub inny host) i zainstaluj Hermes Agent zgodnie z [INSTALL.md](INSTALL.md).
2. Skopiuj szablony konfiguracji i uzupelnij placeholdery:
   ```bash
   cp config/SOUL.md.template ~/.hermes/config/SOUL.md
   cp config/config.yaml.template ~/.hermes/config/config.yaml
   ```
   Uzupelnij wszystkie pola oznaczone `# <-- UZUPELNIJ`.
3. Zainstaluj skille i skrypty do katalogu roboczego Hermesa:
   ```bash
   just install
   just install-scripts
   ```
4. Ustaw zmienne srodowiskowe (klucz OpenRouter, token Telegram, sciezka do vaulta) w `~/.hermes/.env`.
5. Uruchom Hermesa i zweryfikuj polaczenie z Telegramem - patrz sekcja "Pierwsze uruchomienie" w [INSTALL.md](INSTALL.md).

Szczegoly architektury i przeplywu danych opisano w [docs/architektura.md](docs/architektura.md), a pelny opis mozliwosci i wzorcow uzycia w [docs/workflow.md](docs/workflow.md).

## Struktura repozytorium

```
.
├── README.md                    - ten plik
├── INSTALL.md                   - instrukcja instalacji krok po kroku
├── docs/
│   ├── architektura.md          - architektura Hermesa i pipeline'ow
│   └── workflow.md              - co system potrafi i jak z niego korzystac
├── config/
│   ├── SOUL.md.template         - szablon pliku zasad dzialania agenta
│   └── config.yaml.template     - szablon konfiguracji technicznej
├── cron/
│   └── jobs-example.json        - przykladowa konfiguracja cronjobow
├── skills/                      - instrukcje skilli (Sokrates, zakupy, wiedza, routing modeli, ...)
├── scripts/                     - deterministyczne skrypty (watchdogi, digesty, integracje)
├── .gitignore
└── justfile                     - zadania instalacyjne (just install, just check, ...)
```

## Licencja

MIT - patrz naglowki poszczegolnych plikow skilli. Uzywaj, modyfikuj i udostepniaj dowolnie, bez gwarancji.
