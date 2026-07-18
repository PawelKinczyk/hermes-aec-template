---
name: coding-cli-provider-config
description: "Konfiguracja coding agent CLI (Claude Code, Codex, OpenCode) z niestandardowymi providerami API (np. DeepSeek przez Anthropic-compatible API)."
version: 1.0.0
author: Hermes Agent
---

# Coding CLI — konfiguracja niestandardowych providerów API

## Kiedy używać

Gdy użytkownik każe użyć Claude Code / Codex / OpenCode z modelem spoza domyślnego providera (np. DeepSeek zamiast Anthropica).

## Ostrzeżenie — domyślny provider

Domyślnie Claude Code używa modeli Anthropica (Claude Sonnet/Opus/Haiku).  
**NIGDY nie podmieniać providera bez wyraźnego polecenia użytkownika.**

## Wzorzec: zmienne środowiskowe

Większość coding agent CLI wspiera przekierowanie przez zmienne środowiskowe:

| CLI | Zmienna | Wartość |
|-----|---------|---------|
| Claude Code | `ANTHROPIC_BASE_URL` | URL endpointu providera (Anthropic-compatible) |
| Claude Code | `ANTHROPIC_AUTH_TOKEN` | Token API providera |
| Claude Code | `ANTHROPIC_MODEL` / `ANTHROPIC_DEFAULT_*_MODEL` | Mapowanie modeli |
| Claude Code | `CLAUDE_CODE_SUBAGENT_MODEL` | Model dla subagentów |

## Konfiguracja DeepSeek przez Claude Code

Klucz API DeepSeek przechowywany jest w `~/.claude_deepseek_env` (zmienne srodowiskowe).
**UWAGA: NIGDY nie laduj tego pliku globalnie (`source` w .bashrc itp.) — nadpisalby antropiczne API globalnie dla aplikacji.**

Poprawne uzycie: inline `export` jednorazowo, w tej samej komendzie terminala co `claude`:

```bash
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic" && \
export ANTHROPIC_AUTH_TOKEN="sk-..." && \
export ANTHROPIC_MODEL="deepseek-v4-pro[1m]" && \
export ANTHROPIC_DEFAULT_HAIKU_MODEL="deepseek-v4-flash" && \
claude -p "zadanie" --allowedTools "Read,Edit" --max-budget-usd 4.00 --output-format json
```

Zmienne wymagane (minimum):
| Zmienna | Wartosc | Uwagi |
|---------|---------|-------|
| `ANTHROPIC_BASE_URL` | `https://api.deepseek.com/anthropic` | |
| `ANTHROPIC_AUTH_TOKEN` | Klucz API DeepSeek (zaczyna sie od `sk-`, 35 znakow) | Główna zmienna auth |
| `ANTHROPIC_API_KEY` | **Ten sam klucz co powyżej** | **Też wymagana** — niektóre wersje Claude Code sprawdzają AUTH_TOKEN, inne API_KEY; ustaw obie |
| `ANTHROPIC_MODEL` | `deepseek-v4-pro[1m]` (suffix `[1m]` = 1M kontekstu, wymagany przez Claude Code) | |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | `deepseek-v4-flash` (dla subagentow) | |

Jesli uzytkownik NIE podal klucza inline, mozna uzyc `source ~/.claude_deepseek_env &&` zamiast inline export — ALE tylko jako shortcut w sesji, nigdy globalnie.

Oficjalna dokumentacja DeepSeek: `references/deepseek-official-docs.md`

## Koszty DeepSeek vs Anthropic

DeepSeek ~10x tańszy od Anthropica. Budżety empirycznie potwierdzone (sesja 2026-07-17):

| Zadanie | Pliki | Koszt DeepSeek |
|---------|-------|----------------|
| Retagowanie notatek Obsidian | 52 | $1.35-2.33 |
| Download 8 aktow + upload Paperless | 8 | $1.28-3.25 |
| Generowanie masywnego dokumentu | 1 | $5-8 |

Sugerowane budżety: $1-2 (male), $2-4 (srednie), $5-8 (duze).

## Walidacja tokenu DeepSeek

Przed kazdym uzyciem Claude Code z DeepSeekiem, zweryfikuj token:

```bash
# Test: 200 = OK, 401 = klucz wygasl
curl -s -o /dev/null -w "%{http_code}" "https://api.deepseek.com/v1/models" \
  -H "Authorization: Bearer $(grep ANTHROPIC_AUTH_TOKEN ~/.claude_deepseek_env | cut -d'"' -f2)"
```

Gdy klucz wygasl (401), Claude Code NIE zwroci czytelnego bledu — zamiast tego zobaczysz:
```json
{"subtype": "error_during_execution", "total_cost_usd": 0, "usage": {"input_tokens": 0},
 "terminal_reason": "aborted_streaming"}
```
**0 tokenow + 0 kosztu + `aborted_streaming` = wygasly klucz DeepSeek**, NIE problem z siecia.
Nie prolonguj timeoutu — popros uzytkownika o nowy klucz z https://platform.deepseek.com/api_keys.

## Pitfalls

- Preferuj inline `export` przed `claude` (jedna komenda terminala). `source ~/.claude_deepseek_env` w osobnej komendzie NIE dziala — stan env nie przenosi sie miedzy terminal().
- NIGDY nie laduj `~/.claude_deepseek_env` globalnie (`.bashrc`, `.profile`) — nadpisze antropiczne API dla calej aplikacji. Uzytkownik wyraznie tego zabronil: "nie nadpisuje numeru api globalnie dla aplikacji tylko wczytaj api deepseek jednorazowo w terminalu".
- Domyślne ustawienia (bez export) = modele Anthropica.
- Token w pliku env — nie wyświetlać ani nie logować.
- **KRYTYCZNE: potrzebne OBYDWIE zmienne auth.** Niektóre wersje Claude Code sprawdzają `ANTHROPIC_AUTH_TOKEN`, inne `ANTHROPIC_API_KEY`. Sam klucz jest ten sam, ale musi byc wyeksportowany pod OBOMA nazwami. Plik `~/.claude_deepseek_env` powinien zawierac `ANTHROPIC_API_KEY=$ANTHROPIC_AUTH_TOKEN` (eksport obu z tym samym kluczem).
- Gdy Anthropic zwraca 429 (\"Usage credits required\"), przełącz na DeepSeek — nie czekaj na reset. Użytkownik sam sugeruje tę ścieżkę (\"przełącz się na deep seek pro\").
- **KRYTYCZNE: nigdy nie uruchamiaj `claude auth logout` bez jednoznacznego słowa-klucza od użytkownika** (\"wyloguj\", \"logout\", \"wyloguj mnie z konta\", \"odłącz konto\"). Frazy typu \"zresetuj terminal\", \"wyczyść sesję\", \"zresetuj claude\" NIE oznaczają wylogowania — odnoszą się do restartu procesu lub stanu sesji. Wylogowanie to operacja destrukcyjna: usuwa token OAuth i wymaga ponownego logowania przez przeglądarkę. W razie wątpliwości zapytaj użytkownika. Do sprawdzenia stanu używaj `claude auth status --text` (read-only, bezpieczne).
