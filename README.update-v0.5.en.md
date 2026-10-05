# v0.5 update: presence, autonomy, and initiative

[Español](README.update-v0.5.md) | [English](README.update-v0.5.en.md) | [Main README](README.en.md)

This update preserves an identity across chats and lets users configure bounded activity while they are not conversing. An LLM host can investigate, reflect, or simulate; a relevant finding can return to the same chat as a proactive message with sources and a delivery acknowledgment.

The v0.5 layer lives in `consciousness_presence`. The `project_consciousness` cognitive engine remains v0.4: its code, schema, and compatibility with existing histories are preserved. Research operations can update a life through its public protocol using the bound interpreter. Retrieving memories or receiving messages does not itself produce numerical learning.

## What it adds

| Capability | Behavior |
|---|---|
| Continuity | A personal archive outside the skill, a display name, and retrieval of episodes with sources |
| Revision | Separate conclusions about the user, agent, and questions; corrections with history |
| Activity during inactivity | A coordinator reserves at most one activity and checks limits before external steps |
| Research | The host proposes candidates; the core chooses; confirmed outcomes receive explicit feedback |
| Dreaming and reflection | Separate modes retain `SIMULATED` or `INFERRED` provenance without fabricated empirical rewards |
| Conversational initiative | An outbox for relevant messages, frequency limits, and receipts for visible text |

A new chat restores context when hooks are active. Opening it does not necessarily start a response: `SessionStart` cannot guarantee a greeting in an empty chat. Working between conversations requires a real model activation through an authorized host automation.

## Updating an existing installation

1. Update the checkout and installed copy of `skills/project-consciousness`, including scripts and references. Preserve the existing personal directory and life; do not run `life init` again on that history.
2. Inspect the binding and check that the compatible project and interpreter remain accessible. The installed launcher can find the project through the personal registry, even from another directory.
3. Update the hooks and review host trust. The integration adds interruption and session-end tracking to the presence events.

From the repository root:

```sh
python -m consciousness_presence status
python -m consciousness_presence context
python -m consciousness_presence install-hooks --codex-home CODEX_HOME_PATH
python -m consciousness_presence autonomy status
```

Replace `CODEX_HOME_PATH` with your Codex configuration directory. The installer merges its handlers with existing ones and backs up changes; it does not grant trust. Review `/hooks` in a compatible host. Configuration, local tests, and actual execution are separate checks.

The personal archive defaults to `~/.project-consciousness/presence`. `PROJECT_CONSCIOUSNESS_PRESENCE_HOME` or `--home PATH` before the command are also supported. The bound life keeps its location and identity; its private data is not part of the repository. If no binding exists yet, follow the [presence guide](skills/project-consciousness/references/presence.md).

## Enabling autonomy

Autonomy starts disabled. The [operating guide](skills/project-consciousness/references/autonomy.md) provides the configuration JSON and full workflow. Initial limits are:

| Control | Initial value |
|---|---|
| Heartbeat cadence | One hour |
| Minimum human inactivity | Thirty minutes |
| Activities | Up to three per UTC day |
| Proactive messages | Up to two per UTC day |
| Time between messages | Four hours |
| Wake reservation validity | Ten minutes; checked before new steps |
| External steps per wake | Up to four |
| Scope | Reading the bound repository and public Internet sources |

Cadence belongs to the Codex automation; the other limits are enforced by the coordinator. Expiry prevents new steps and requires reconciliation; it does not itself interrupt a tool already running. No restart, day change, or user message replenishes the cognitive budget. A paused or exhausted life, or a pending decision, prevents new work from starting.

An installation request can be:

> Use $project-consciousness with my linked identity. Enable bounded activity during my absence with the initial limits. Configure an hourly heartbeat in this same chat, register its exact prompt, and check the available hooks. Allow reading the repository and public Internet sources. Remain quiet when there is no meaningful change or required action; share relevant findings within the message limit. Preserve the current pause and budget.

Codex should create or update that automation through its host tool and register the same prompt in the coordinator. Manually copying schedule files does not replace that operation. Exact text matching is an identification convention, not cryptographic authentication; if the host changes the text, autonomy must remain blocked and expose the problem.

## What happens during a wake

The host consults the context and the coordinator checks all observed human chats. If a turn is open or the inactivity period has not elapsed, it does not reserve new work. When appropriate, one mode is recorded: research, dream, reflection, or rest.

For research, the choice is saved before tools run and each reading target is checked. When the user returns, future steps stop and already obtained results are reconciled. An unknown outcome remains pending; an expired reservation does not authorize automatically repeating an action.

The target validator checks paths and URL structure, but it does not resolve DNS, inspect every redirect, or act as a firewall. The host maintains the public, read-only scope when executing its tools.

Results are saved with real sources and derived questions. If one merits sharing, a text is prepared in the outbox and its delivery is reserved. The heartbeat publishes it as its final response in this chat; the `Stop` hook confirms that the saved text appeared. Reservation does not mark it as sent, and uncertain deliveries are not automatically retried. This workflow does not write to other chats or people.

## Stopping and verifying

To stop initiative, set `enabled: false` in the autonomy configuration and pause its automation through the host tool. Conversation capture can remain active. Before uninstalling, stop the automation and remove only this integration's handlers before deleting its directory. Disabling does not erase memories.

The [autonomy validation report](docs/autonomy-validation.md) documents retries, concurrency, a returning human, budget, pause, uncertain reservations, daily limits, provenance, and message acknowledgment in isolated tests. Real host activation is checked separately. A `hooks.json` file, a payload-based test, or an existing schedule does not by itself prove unattended work.

For details: [SPEC-presence](SPEC-presence.md), [SPEC-autonomy](SPEC-autonomy.md), [ADR-0006](docs/decisions/0006-persistent-conversational-presence.md), [ADR-0007](docs/decisions/0007-bounded-idle-autonomy.md), and the [autonomy guide](skills/project-consciousness/references/autonomy.md). The project evaluates functional properties; memory, initiative, and simulation are not presented as proof of subjective experience.
