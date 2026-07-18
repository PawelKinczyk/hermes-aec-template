---
name: model-routing
description: "Model/tool routing rules for Hermes tasks: DeepSeek V4 Flash (default), delegation to DeepSeek V4 Pro for complex analysis, Claude Code headless for code implementation, plain scripts for deterministic operations."
version: 1.3.0
author: Hermes Agent
metadata:
  hermes:
    tags: [Model-Routing, Cost-Hygiene, DeepSeek, Claude-Code, Delegation]
    related_skills: [claude-code]
---

# Model routing

Rules for choosing the model and tool per task type. Goal: never pay for an
expensive model/tool on a simple task, and never use an LLM where a script
suffices.

## Model switching — known bugs and limitations

Hermes has several model-mismatch issues that can affect routing decisions.
See `references/model-mismatch-known-issues.md` for the full research with
GitHub issue links, error patterns, and affected code paths.

### delegation.model override is ignored (bug, Jul 2026)

Despite the docs stating that `delegation.model` in config.yaml routes
subagents to a different model, **it does not work** — subagents always
inherit the parent's model (Issue #31155). Credential pool rotation
overwrites the delegation model mid-flow. Track the issue for the fix.

### delegation.base_url routes to wrong provider (bug, Jul 2026)

When `delegation.base_url` is set to a different provider (e.g., Anthropic)
while the primary model uses OpenRouter, the subagent's config resolves
correctly but the **actual HTTP request still goes to the parent's
endpoint**, producing 401 (#61195, #20558). Subagents also inherit the
parent's `api_mode` (Anthropic messages vs OpenAI chat completions)
regardless of model change (#20558).

### Per-call model override for delegate_task (implemented on main)

Feature requests #3719 and #47014 add `model`/`provider` parameters to
`delegate_task` directly. Both closed as "sweeper:implemented-on-main".
The tool schema now supports:
```json
{"name": "delegate_task", "arguments": {"goal": "...", "model": "...", "provider": "..."}}
```
Fallback chain: per-call override → config delegation.model → inherit
from parent. Verify availability in your Hermes version before relying
on it.

### /model slash command — memory stale on switch

The `/model [name]` command switches the session model mid-conversation
but does NOT call `load_from_disk()` on MemoryStore (#10880, fixed).
Externally-written memory entries remain invisible until context
compression fires. If you `/model` switch and memory seems stale, force
`/compress` to trigger a refresh.

### OpenRouter — spurious model switching (historical)

Issue #8268 reported Hermes calling OpenRouter models OTHER than the
configured one, causing unexpected costs. #12146 reported agent runs
falling back to OpenRouter despite a different `model.provider` being
set. If you see unexpected model calls on your bill, review which
providers have active credentials via `hermes auth list`.

### Cron job model handling — snapshot + fail-closed

Cron jobs that omit `model`/`provider` **snapshot** the global default
at creation time. If the global default later changes, the job **fails
closed** — it skips the run and sends an alert asking you to pin the
provider/model explicitly (#44585). Per-job model override:
```
cronjob(action="create", ..., model=deepseek/deepseek-v4-pro, provider=openrouter)
```

## Routing table

| Situation | Model / tool | Reasoning |
|---|---|---|
| Conversation, summaries, digests, issue descriptions, notes | DeepSeek V4 Flash (`deepseek/deepseek-v4-flash`) | Default. ~$0.09/0.18 per 1M tok. 79% SWE-bench, 1M ctx. Covers 90% of daily tasks. |
| Multi-step analysis, code review, complex planning | `delegate_task(goal=..., context=..., model="deepseek/deepseek-v4-pro")` or Claude Sonnet 5 | V4 Pro $0.30/0.50 per 1M tok. 80.6% SWE-bench, 90.1% GPQA. For better reasoning per dollar: Claude Sonnet 5 ($2/$10 intro, 96.2% GPQA, 85.2% SWE). |
| Complex coding, architecture planning, repo-scale refactors | `delegate_task(goal=..., context=..., model="deepseek/deepseek-v4-pro")` or Claude Sonnet 5 | V4 Pro: top open-weight SWE at $0.30/0.50. Sonnet 5: 85.2% SWE at $2/$10 intro. Closed-source fallback. Chose V4 Pro when open weights needed, Sonnet 5 when best reasoning per dollar. |
| Code implementation, refactoring, multi-file repo edits | Claude Code headless via `terminal` -- see the `claude-code` skill | DeepSeek backend via ~/.claude_deepseek_env. For multi-file changes too complex for one-shot prompts. |
| Visual analysis (screenshots, diagrams, PDFs) | `delegate_task(goal=..., model="minimax/minimax-m3")` or fallback to `vision_analyze` | MiniMax M3: $0.098/1.21 per 1M tok, AA Index 44, native image/video, 1M ctx. Only open multimodal model worth routing to. |
| Deterministic operations (fetch, filter, write files) | script (`~/.hermes/scripts/`) or `terminal` -- no LLM | Zero token cost. Always prefer over any LLM call. See cronjob `no_agent=true` pattern. |

Note: the default delegation model in `config.yaml` (`delegation.model`) is
`deepseek/deepseek-v4-flash` — that is the fallback when `delegate_task` is
called without a `model` parameter. For the "multi-step analysis" row above,
ALWAYS pass `model="deepseek/deepseek-v4-pro"` explicitly in the call.

See `references/model-pricing-benchmarks.md` for current (July 2026) pricing, benchmarks, and routing decision tree for each model in this table. Refresh every 2-3 months.

## Additional rules

1. Before delegating to Pro (`delegate_task` with
   `model=deepseek/deepseek-v4-pro`) or Claude Sonnet 5, or invoking Claude Code, state one
   sentence of justification for why the task requires it.
2. Use `web_extract` instead of `browser` wherever clicking is not required
   (forms, login, dynamic SPA) — `browser` is slower and more expensive.
3. Design new cron jobs as `no_agent` first (script, zero tokens). The
   `agent` variant requires a justification for why a deterministic script
   cannot do the job.
4. Never load whole Obsidian vault folders into context — always fetch
   specific notes (search via MCP, then read the hits), never a directory
   en masse.

## Claude Code print-mode nuance

Despite the `claude-code` skill describing print mode as "ideal for
automation", Claude Code can still ask clarifying questions in print mode
and stop without executing (`stop_reason: end_turn`, zero work done).
See `references/claude-code-print-mode-pitfalls.md` for symptoms,
prevention (the `EXECUTE immediately` prompt prefix), and recovery steps.

## DeepSeek Claude Code backend

When sourcing `~/.claude_deepseek_env` to route Claude Code through DeepSeek:
- Set BOTH `ANTHROPIC_AUTH_TOKEN` and `ANTHROPIC_API_KEY` (some versions check one, some the other)
- Do NOT pass `--model` CLI flag — model selection is through `ANTHROPIC_MODEL` env var
- Verify the key before running a real task with a quick curl to `/anthropic/v1/messages`
- 401 on the key check = key expired → ask user to regenerate at https://platform.deepseek.com/api_keys

Full configuration and verification: `references/deepseek-claude-code-config.md`.

## Fallback when Claude Code is unavailable

When Claude Code cannot be invoked (DeepSeek key expired, Anthropic credits
exhausted), fall back to `delegate_task` with OpenRouter DeepSeek Pro:

```
delegate_task(goal="...", context="...", model="deepseek/deepseek-v4-pro")
```

For large writing/research tasks, split into 2-3 parallel subagents via
`tasks=[...]` for speed. Subagents write to separate temp files; merge them
after all complete.

**Pitfall — batch mode model:** when using `tasks=[...]` (batch delegation),
there is no per-task `model` field in the API. All subagents run on the global
`delegation.model` from config (default: Flash). If Pro-level analysis is
needed per task, use single-task `delegate_task(goal=..., model="deepseek/deepseek-v4-pro")`
instead, or dispatch 2-3 single-task calls sequentially with explicit model.

## Cost log

Every Claude Code headless invocation and every delegation to Pro must
ultimately be recorded in `~/.hermes/state/claude-code-costs.jsonl`
(entry format specified in the `claude-code` skill; `cost_usd` comes from
`total_cost_usd` in the Claude Code JSON response).
