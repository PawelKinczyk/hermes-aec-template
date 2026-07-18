# Instalacja

Instrukcja krok po kroku dla instalacji Hermes Agent na Raspberry Pi 5, z konfiguracja pod ten szablon AEC.

## 1. Przygotowanie Raspberry Pi OS

1. Zainstaluj Raspberry Pi OS (64-bit, Lite lub Desktop) na karcie microSD/SSD za pomoca Raspberry Pi Imager. Wlacz SSH i skonfiguruj siec juz na etapie flashowania obrazu.
2. Po pierwszym uruchomieniu zaktualizuj system:
   ```bash
   sudo apt update && sudo apt full-upgrade -y
   sudo reboot
   ```
3. Zainstaluj wymagane pakiety bazowe:
   ```bash
   sudo apt install -y git curl python3 python3-pip python3-venv build-essential
   ```
4. Zainstaluj Node.js (LTS) - wymagany przez Hermes Agent i agent-browser:
   ```bash
   curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
   sudo apt install -y nodejs
   node --version   # oczekiwane v20+
   ```
5. (Opcjonalnie, zalecane) Ustaw statyczny adres IP lub rezerwacje DHCP dla RPi w routerze - Hermes ma dzialac 24/7 i inne uslugi (FreshRSS, Paperless) beda sie do niego odwolywac po adresie lokalnym.

## 2. Instalacja Hermes Agent

1. Zainstaluj Hermes Agent zgodnie z oficjalna dokumentacja projektu (link w `README.md` glownego repo Hermes). Typowo:
   ```bash
   mkdir -p ~/.hermes
   cd ~/.hermes
   git clone <adres-repo-hermes-agent> hermes-agent   # <-- UZUPELNIJ adres repo Hermes Agent
   cd hermes-agent
   npm install
   ```
2. Sklonuj niniejszy szablon obok (lub w dowolnym miejscu, z ktorego bedziesz kopiowac pliki):
   ```bash
   git clone https://github.com/PawelKinczyk/hermes-aec-template.git
   cd hermes-aec-template
   ```
3. Utworz katalogi robocze Hermesa, jesli jeszcze nie istnieja:
   ```bash
   mkdir -p ~/.hermes/config ~/.hermes/state ~/.hermes/scripts ~/.hermes/skills
   ```

## 3. Konfiguracja klucza API OpenRouter

1. Zaloz konto na https://openrouter.ai i doladuj budzet (kilka-kilkanascie USD wystarczy na start).
2. Wygeneruj klucz API w panelu OpenRouter (Keys -> Create Key).
3. Skopiuj szablon konfiguracji i uzupelnij klucz:
   ```bash
   cp config/config.yaml.template ~/.hermes/config/config.yaml
   ```
   W pliku `~/.hermes/config/config.yaml` znajdz pole oznaczone `# <-- SET YOUR TOKEN HERE` w sekcji `model.provider` i wstaw referencje do zmiennej srodowiskowej (klucza nie wpisuj wprost do pliku).
4. Utworz plik `~/.hermes/.env` (nigdy nie commitowany do repo) z kluczem:
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
   Odpowiedz z lista modeli (JSON) oznacza dzialajacy klucz.

## 4. Konfiguracja integracji Telegram

1. W Telegramie otworz rozmowe z [@BotFather](https://t.me/BotFather), wyslij `/newbot` i postepuj wedlug instrukcji (nazwa, unikalny login konczacy sie na `bot`).
2. Zapisz token bota zwrocony przez BotFather.
3. Wyslij dowolna wiadomosc do nowo utworzonego bota, a nastepnie pobierz swoje `chat_id`:
   ```bash
   curl -s "https://api.telegram.org/bot<TWOJ_TOKEN>/getUpdates" | python3 -m json.tool
   ```
   Znajdz pole `message.chat.id` w odpowiedzi.
4. Dodaj oba wpisy do `~/.hermes/.env`:
   ```bash
   cat >> ~/.hermes/.env <<'EOF'
   TELEGRAM_BOT_TOKEN=...                 # <-- UZUPELNIJ
   TELEGRAM_CHAT_ID=...                   # <-- UZUPELNIJ
   EOF
   ```
5. Uzupelnij referencje do tych zmiennych w sekcji `channels.telegram` w `~/.hermes/config/config.yaml`.

## 5. Pierwsze uruchomienie i weryfikacja

1. Wskaz Hermesowi sciezke do Twojego Obsidian vaulta w `~/.hermes/.env`:
   ```bash
   echo 'OBSIDIAN_VAULT_PATH=/home/pi/ObsidianVault' >> ~/.hermes/.env   # <-- UZUPELNIJ
   ```
2. Uruchom Hermesa w trybie pierwszego planu (nie jako usluga), zeby zobaczyc logi startowe:
   ```bash
   cd ~/.hermes/hermes-agent
   npm start
   ```
3. Sprawdz, czy w logu pojawil sie wpis o poprawnym polaczeniu z OpenRouter oraz z Telegram API (bez bledow 401/403).
4. Wyslij testowa wiadomosc do bota na Telegramie (np. "czesc") i sprawdz, czy Hermes odpowiada.
5. Jesli wszystko dziala, zatrzymaj proces (`Ctrl+C`) i skonfiguruj Hermesa jako usluge systemd (lub inny mechanizm autostartu opisany w dokumentacji Hermes Agent), zeby dzialal w tle po restarcie urzadzenia.

## 6. Instalacja skryptow i skilli z tego szablonu

1. Zainstaluj plik `just` (task runner), jesli jeszcze nie masz:
   ```bash
   sudo apt install -y just
   ```
2. Z katalogu `hermes-aec-template` uruchom:
   ```bash
   just install           # kopiuje skills/ do ~/.hermes/skills/
   just install-scripts   # kopiuje scripts/ do ~/.hermes/scripts/ i nadaje prawa wykonywania
   ```
3. Skopiuj i uzupelnij `SOUL.md`:
   ```bash
   cp config/SOUL.md.template ~/.hermes/config/SOUL.md
   ```
   Uzupelnij wszystkie miejsca oznaczone `# <-- UZUPELNIJ` (jezyk, imie uzytkownika, strefa czasowa, preferencje stylu odpowiedzi).
4. Skrypty pipeline'ow (Sokrates, RSS, Prawo) wymagaja wlasnych zmiennych srodowiskowych i placeholderow sciezek/repo - patrz komentarze w `scripts/*/*.sh` i `scripts/*/*.py` oraz przyklad w `cron/jobs-example.json`.
5. Uzupelnij liste sledzonych repozytoriow GitHub, slowa kluczowe RSS oraz slowa kluczowe prawne we wlasnych plikach konfiguracyjnych w `~/.hermes/config/` (np. `rss-keywords.txt`, `prawo-keywords.txt`) - nie ma ich w tym repo, bo sa specyficzne dla Twojej branzy i zainteresowan.
6. Skonfiguruj cronjoby w Hermesie na podstawie `cron/jobs-example.json` (import przez panel/CLI Hermes Agent, zgodnie z jego dokumentacja) - podmien wszystkie placeholdery na wlasne wartosci.
7. Uruchom `just check`, aby upewnic sie, ze w repo nie zostaly przypadkowo prywatne dane przed dalsza praca lub commitem.

Po wykonaniu powyzszych krokow przejdz do [docs/workflow.md](docs/workflow.md), aby poznac dostepne mozliwosci i wzorce uzycia.
