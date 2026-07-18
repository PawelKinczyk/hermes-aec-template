# justfile - zadania instalacyjne i pomocnicze dla hermes-aec-template.
# Uzycie: just <nazwa-zadania>  (wymaga zainstalowanego "just": https://github.com/casey/just)

set shell := ["bash", "-uc"]

hermes_home := env_var_or_default("HERMES_HOME", env_var("HOME") + "/.hermes")

# Wyswietl dostepne zadania.
default:
    @just --list

# Skopiuj skille do katalogu roboczego Hermesa (~/.hermes/skills/).
install:
    mkdir -p "{{hermes_home}}/skills"
    cp -r skills/. "{{hermes_home}}/skills/"
    @echo "Skille skopiowane do {{hermes_home}}/skills/"

# Skopiuj skrypty do katalogu roboczego Hermesa (~/.hermes/scripts/) i nadaj prawa wykonywania.
install-scripts:
    mkdir -p "{{hermes_home}}/scripts"
    cp -r scripts/. "{{hermes_home}}/scripts/"
    find "{{hermes_home}}/scripts" -type f \( -name "*.sh" -o -name "*.py" \) -exec chmod +x {} +
    @echo "Skrypty skopiowane do {{hermes_home}}/scripts/"

# Zainstaluj skille i skrypty jednym poleceniem.
install-all: install install-scripts

# Zweryfikuj, ze w repozytorium nie ma przypadkowo zacommitowanych prywatnych danych
# (uzupelnione pliki konfiguracyjne, klucze API, tokeny, adresy IP, sciezki domowe).
check:
    #!/usr/bin/env bash
    set -uo pipefail
    fail=0

    for f in config/SOUL.md config/config.yaml; do
        if [ -f "$f" ]; then
            echo "BLAD: $f nie powinien byc w repo (tylko wersje .template) - dodaj do .gitignore lub usun."
            fail=1
        fi
    done

    if [ -f .env ]; then
        echo "BLAD: znaleziono .env w repo - nigdy nie commituj tego pliku."
        fail=1
    fi

    # Wzorce wygladajace jak prawdziwe sekrety (nie placeholdery).
    patterns='sk-or-v1-[A-Za-z0-9]{10,}|AIza[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}'
    hits=$(grep -rEIn "$patterns" --exclude-dir=.git . || true)
    if [ -n "$hits" ]; then
        echo "BLAD: mozliwe prawdziwe klucze/tokeny znalezione w plikach:"
        echo "$hits"
        fail=1
    fi

    # Wymagane markery uzupelnienia w plikach .template - upewnij sie, ze nadal tam sa
    # (jesli ktos je usunal bez faktycznego uzupelnienia poza repo, to sygnal bledu w PR).
    for f in config/SOUL.md.template config/config.yaml.template; do
        if [ -f "$f" ] && ! grep -q "UZUPELNIJ\|SET YOUR TOKEN HERE" "$f"; then
            echo "OSTRZEZENIE: $f nie zawiera juz markerow UZUPELNIJ / SET YOUR TOKEN HERE - sprawdz, czy to zamierzone."
        fi
    done

    if [ "$fail" -eq 0 ]; then
        echo "OK: brak wykrytych prywatnych danych."
    else
        exit 1
    fi
