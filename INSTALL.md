# Instalacja

Instrukcja krok po kroku dla instalacji Hermes Agent na Raspberry Pi 5, z konfiguracją pod ten szablon AEC.

## 1. Przygotowanie Raspberry Pi OS

1. Zainstaluj Raspberry Pi OS (64-bit, Lite lub Desktop) na karcie microSD/SSD za pomocą Raspberry Pi Imager. Włącz SSH i skonfiguruj sieć już na etapie flashowania obrazu.
2. Po pierwszym uruchomieniu zaktualizuj system:
   ```bash
   sudo apt update && sudo apt full-upgrade -y
   sudo reboot
   ```
3. Zainstaluj wymagane pakiety bazowe:
   ```bash
   sudo apt install -y git curl python3 python3-pip python3-venv build-essential
   ```
4. Zainstaluj Node.js (LTS) — wymagany przez Hermes Agent i agent-browser:
   ```bash
   curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
   sudo apt install -y nodejs
   node --version   # oczekiwane v20+
   ```
5. (Opcjonalnie, zalecane) Ustaw statyczny adres IP lub rezerwację DHCP dla RPi w routerze — Hermes ma działać 24/7 i inne usługi (FreshRSS, Paperless) będą się do niego odwoływać po adresie lokalnym.

## 2. Instalacja Hermes Agent

1. Zainstaluj Hermes Agent zgodnie z oficjalną dokumentacją projektu (link w `README.md` głównego repo Hermes). Typowo:
   ```bash
   mkdir -p ~/.hermes
   cd ~/.hermes
   git clone <adres-repo-hermes-agent> hermes-agent   # <-- UZUPELNIJ adres repo Hermes Agent
   cd hermes-agent
   npm install
   ```
2. Sklonuj niniejszy szablon obok (lub w dowolnym miejscu, z którego będziesz kopiować pliki):
   ```bash
   git clone https://github.com/PawelKinczyk/hermes-aec-template.git
   cd hermes-aec-template
   ```
3. Utwórz katalogi robocze Hermesa, jeśli jeszcze nie istnieją:
   ```bash
   mkdir -p ~/.hermes/config ~/.hermes/state ~/.hermes/scripts ~/.hermes/skills
   ```

## 3. Konfiguracja klucza API OpenRouter

1. Załóż konto na https://openrouter.ai i doładuj budżet (kilka–kilkanaście USD wystarczy na start).
2. Wygeneruj klucz API w panelu OpenRouter (Keys -> Create Key).
3. Skopiuj szablon konfiguracji i uzupełnij klucz:
   ```bash
   cp config/config.yaml.template ~/.hermes/config/config.yaml
   ```
   W pliku `~/.hermes/config/config.yaml` znajdź pole oznaczone `# <-- SET YOUR TOKEN HERE` w sekcji `model.provider` i wstaw referencję do zmiennej środowiskowej (klucza nie wpisuj wprost do pliku).
4. Utwórz plik `~/.hermes/.env` (nigdy nie commitowany do repo) z kluczem:
   ```bash
   cat >> ~/.hermes/.env <<'EOF'
   OPENROUTER_API_KEY=sk-or-...          # <-- UZUPELNIJ
   EOF
   chmod 600 ~/.hermes/.env
   ```
5. Zweryfikuj klucz:
   ```bash
   curl -s https://openrouter.ai/api/v1/models \
     -H "Authorization: Bearer $(grep OPENROUTER_API_KEY ~/.hermes/.env | cut -d= -f2)" \
     | head -c 200
   ```
   Odpowiedź z listą modeli (JSON) oznacza działający klucz.

## 4. Konfiguracja integracji Telegram

1. W Telegramie otwórz rozmowę z [@BotFather](https://t.me/BotFather), wyślij `/newbot` i postępuj według instrukcji (nazwa, unikalny login kończący się na `bot`).
2. Zapisz token bota zwrócony przez BotFather.
3. Wyślij dowolną wiadomość do nowo utworzonego bota, a następnie pobierz swoje `chat_id`:
   ```bash
   curl -s "https://api.telegram.org/bot<TWOJ_TOKEN>/getUpdates" | python3 -m json.tool
   ```
   Znajdź pole `message.chat.id` w odpowiedzi.
4. Dodaj oba wpisy do `~/.hermes/.env`:
   ```bash
   cat >> ~/.hermes/.env <<'EOF'
   TELEGRAM_BOT_TOKEN=...                 # <-- UZUPELNIJ
   TELEGRAM_CHAT_ID=...                   # <-- UZUPELNIJ
   EOF
   ```
5. Uzupełnij referencje do tych zmiennych w sekcji `channels.telegram` w `~/.hermes/config/config.yaml`.

## 5. Pierwsze uruchomienie i weryfikacja

1. Wskaż Hermesowi ścieżkę do Twojego Obsidian vaulta w `~/.hermes/.env`:
   ```bash
   echo 'OBSIDIAN_VAULT_PATH=/home/pi/ObsidianVault' >> ~/.hermes/.env   # <-- UZUPELNIJ
   ```
2. Uruchom Hermesa w trybie pierwszego planu (nie jako usługa), żeby zobaczyć logi startowe:
   ```bash
   cd ~/.hermes/hermes-agent
   npm start
   ```
3. Sprawdź, czy w logu pojawił się wpis o poprawnym połączeniu z OpenRouter oraz z Telegram API (bez błędów 401/403).
4. Wyślij testową wiadomość do bota na Telegramie (np. „cześć”) i sprawdź, czy Hermes odpowiada.
5. Jeśli wszystko działa, zatrzymaj proces (`Ctrl+C`) i skonfiguruj Hermesa jako usługę systemd (lub inny mechanizm autostartu opisany w dokumentacji Hermes Agent), żeby działał w tle po restarcie urządzenia.

## 6. Instalacja skryptów i skilli z tego szablonu

1. Zainstaluj plik `just` (task runner), jeśli jeszcze nie masz:
   ```bash
   sudo apt install -y just
   ```
2. Z katalogu `hermes-aec-template` uruchom:
   ```bash
   just install           # kopiuje skills/ do ~/.hermes/skills/
   just install-scripts   # kopiuje scripts/ do ~/.hermes/scripts/ i nadaje prawa wykonywania
   ```
3. Skopiuj i uzupełnij `SOUL.md`:
   ```bash
   cp config/SOUL.md.template ~/.hermes/config/SOUL.md
   ```
   Uzupełnij wszystkie miejsca oznaczone `# <-- UZUPELNIJ` (język, imię użytkownika, strefa czasowa, preferencje stylu odpowiedzi).
4. Skrypty pipeline'ów (Sokrates, RSS, Prawo) wymagają własnych zmiennych środowiskowych i placeholderów ścieżek/repo — patrz komentarze w `scripts/*/*.sh` i `scripts/*/*.py` oraz przykład w `cron/jobs-example.json`.
5. Uzupełnij listę śledzonych repozytoriów GitHub, słowa kluczowe RSS oraz słowa kluczowe prawne we własnych plikach konfiguracyjnych w `~/.hermes/config/` (np. `rss-keywords.txt`, `prawo-keywords.txt`) — nie ma ich w tym repo, bo są specyficzne dla Twojej branży i zainteresowań.
6. Skonfiguruj cronjoby w Hermesie na podstawie `cron/jobs-example.json` (import przez panel/CLI Hermes Agent, zgodnie z jego dokumentacją) — podmień wszystkie placeholdery na własne wartości.
7. Uruchom `just check`, aby upewnić się, że w repo nie zostały przypadkowo prywatne dane przed dalszą pracą lub commitem.

Po wykonaniu powyższych kroków przejdź do [docs/workflow.md](docs/workflow.md), aby poznać dostępne możliwości i wzorce użycia.
