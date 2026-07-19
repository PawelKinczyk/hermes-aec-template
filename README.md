# hermes-aec-template

Szablon konfiguracji [Hermes Agent](https://github.com/hermes-agent/hermes-agent) dla inżyniera branży AEC (architektura, konstrukcje, budownictwo). Zawiera gotowe skille, skrypty i wzorce cronjobów dopasowane do pracy inżyniera: monitoring aktów prawnych, monitoring RSS branżowego, obsługę zakupów, śledzenie czasu pracy oraz orkiestrację coding agentów.

Repozytorium jest publiczne i **sanitized** — wszystkie dane osobiste, tokeny, ścieżki i adresy zostały zastąpione placeholderami. Przed użyciem trzeba je uzupełnić własnymi wartościami (patrz [INSTALL.md](INSTALL.md)).

## Czym jest Hermes

Hermes Agent to autonomiczny agent AI działający w tle na własnym sprzęcie (najczęściej Raspberry Pi), pełniący funkcję osobistego asystenta dostępnego przez Telegram. W odróżnieniu od czatu w przeglądarce, Hermes:

- działa 24/7 i reaguje na wiadomości z Telegrama w dowolnym momencie,
- wykonuje zadania cykliczne (cronjoby) bez udziału użytkownika — np. sprawdza nowe akty prawne, kanały RSS, wzmianki na GitHubie,
- ma dostęp do lokalnych narzędzi: systemu plików, przeglądarki (agent-browser), skryptów powłoki, API zewnętrznych serwisów,
- korzysta z modeli językowych przez OpenRouter (domyślnie tanie modele do zadań bieżących, droższe/lepsze do zadań złożonych),
- przechowuje wiedzę w istniejącym Obsidian vault użytkownika (notatki, streszczenia, digesty),
- może delegować zadania programistyczne do Claude Code CLI.

Zachowanie agenta opisuje plik `SOUL.md` (zasady działania, język, styl odpowiedzi), a konfigurację techniczną `config.yaml` (model, klucze API, integracje). Skille (`skills/`) to instrukcje w języku naturalnym, które Hermes sam dobiera do zadania. Skrypty (`scripts/`) to deterministyczne operacje bez udziału LLM, uruchamiane ręcznie lub z cronjobów.

## Wymagania wstępne

- **Raspberry Pi 5** (4 GB+ RAM) z zainstalowanym Raspberry Pi OS (64-bit) — lub inny komputer z Linuksem działający 24/7.
- **Konto OpenRouter** (https://openrouter.ai) z kluczem API i doładowanym budżetem — Hermes korzysta z modeli przez ten routing.
- **Bot Telegram** utworzony przez [@BotFather](https://t.me/BotFather) — potrzebny token bota oraz ID czatu/użytkownika.
- **Obsidian vault** (istniejący lub nowy) dostępny lokalnie na tym samym urządzeniu — Hermes zapisuje w nim notatki bezpośrednio na dysku.
- Opcjonalnie: konto GitHub (dla pipeline'u Sokrates), instancja FreshRSS (dla pipeline'u RSS), konto Toggl Track (do time trackingu).

## Szybki start

1. Sklonuj to repozytorium na docelowej maszynie (RPi 5 lub inny host) i zainstaluj Hermes Agent zgodnie z [INSTALL.md](INSTALL.md).
2. Skopiuj szablony konfiguracji i uzupełnij placeholdery:
   ```bash
   cp config/SOUL.md.template ~/.hermes/config/SOUL.md
   cp config/config.yaml.template ~/.hermes/config/config.yaml
   ```
   Uzupełnij wszystkie pola oznaczone `# <-- UZUPELNIJ`.
3. Zainstaluj skille i skrypty do katalogu roboczego Hermesa:
   ```bash
   just install
   just install-scripts
   ```
4. Ustaw zmienne środowiskowe (klucz OpenRouter, token Telegram, ścieżka do vaulta) w `~/.hermes/.env`.
5. Uruchom Hermesa i zweryfikuj połączenie z Telegramem — patrz sekcja „Pierwsze uruchomienie” w [INSTALL.md](INSTALL.md).

Szczegóły architektury i przepływu danych opisano w [docs/architektura.md](docs/architektura.md), a pełny opis możliwości i wzorców użycia w [docs/workflow.md](docs/workflow.md).

## Struktura repozytorium

```
.
├── README.md                    - ten plik
├── INSTALL.md                   - instrukcja instalacji krok po kroku
├── docs/
│   ├── architektura.md          - architektura Hermesa i pipeline'ów
│   └── workflow.md              - co system potrafi i jak z niego korzystać
├── config/
│   ├── SOUL.md.template         - szablon pliku zasad działania agenta
│   └── config.yaml.template     - szablon konfiguracji technicznej
├── cron/
│   └── jobs-example.json        - przykładowa konfiguracja cronjobów
├── skills/                      - instrukcje skilli (Sokrates, zakupy, wiedza, routing modeli, ...)
├── scripts/                     - deterministyczne skrypty (watchdogi, digesty, integracje)
├── .gitignore
└── justfile                     - zadania instalacyjne (just install, just check, ...)
```

## Licencja

MIT — patrz nagłówki poszczególnych plików skilli. Używaj, modyfikuj i udostępniaj dowolnie, bez gwarancji.
