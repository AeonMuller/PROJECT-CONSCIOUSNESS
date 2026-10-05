# Autonomous activity and conversational initiative

Status: user approved implementation, README update and push, 2026-10-05.
The v0.4 engine remains unchanged. All new state belongs to the presence layer.

## Scope and defaults

One coordinator per presence home/life. A Codex heartbeat wakes the existing chat;
it does not create a new chat per run. Initial cadence: one hour; quiet threshold:
30 minutes; at most three activities and two proactive messages per UTC day, with
four hours between messages. These are configurable operational limits, distinct
from the existing core budget, which is never replenished automatically.
Research may read the bound repository and public Internet. No publishing, credential
access, code changes, purchases, outbound messages to other people or self-modification.

## Coordinator contract (autonomy.py)

`AutonomyStore(home)` uses its own SQLite database, supports a context manager, and
does not modify presence or core schema. Public methods return JSON objects:

- `configure(changes)` validates partial settings. `status()` shows settings, human
  activity, open turns, wakes and delivery state. Initial enabled=false.
- `register_prompt(prompt)` saves the exact scheduled prompt hash. Hooks recognize
  that exact text as scheduler-origin; all other prompts count as human activity.
  This is an explicit adapter convention, not cryptographic host authentication.
  If the host rewrites the prompt, the system conservatively stays inactive.
- `observe_event(payload, now=None)` records SessionStart/UserPromptSubmit/Stop/
  Interrupt/SessionEnd, deduplicated by session/turn/event. Scheduled prompts do not
  reset the human-idle clock or enter autobiographical human conversation records.
  Human turns across ALL bound chats block autonomy until Stop/Interrupt/SessionEnd.
  Unknown stale active turns remain blocking until explicitly reconciled.
- `begin(wake_id, core_state, now=None)` atomically reserves one idle activity if
  enabled, hooks have been observed, no human turns are active, quiet threshold has
  elapsed, daily limit and core budget permit, core is unpaused and pending is null.
  Wake IDs replay without additional effects. Another running wake blocks.
  A lease expiry marks the wake uncertain; it does not silently start another one.
- `checkpoint(wake_id, now=None)` rechecks integration configuration, human activity
  and elapsed activity limit before each further external step. A returning user
  prevents new external actions; completed outcomes are still reconciled.
- `finish(wake_id, result, now=None)` stores a final receipt idempotently. Result has
  status completed|skipped|failed|uncertain, kind research|dream|reflect|rest,
  summary, source_ids, question, and optional notification. Non-rest completed results
  require sources. It closes the lease; uncertain outcomes block until reconciliation.
- `outbox(now=None)` returns pending permitted proactive messages; `delivered(message_id,
  receipt, now=None)` records acknowledgment. At most one message reserved for delivery;
  uncertain deliveries are not automatically resent. Notifications use explicit saved
  text and source IDs, and must respect configured daily/cooldown limits.
- `reconcile(wake_id, result, now=None)` explicitly resolves an uncertain wake with
  evidence. `close_turn(session_id, turn_id, reason, now=None)` resolves a stale turn.

## Workflow contract (activity.py; CLI autonomy ...)

The coordinator grants execution, never tools/permissions beyond the request. A wake
prepares at most one activity; meaningful questions and repository/web candidates are
supplied by the active LLM. The v0.4 selector chooses research candidates using recorded
preferences. Its returned decision ID and original candidate terms are persisted before
execution. Explicit stable request IDs bridge retries, including failures after commit.
Dream and reflection remain separate modes: no feedback is fabricated for simulations.

`autonomy start --wake-id ID --request FILE` accepts kind research/dream/reflect/rest;
research includes validated core candidates; reflect includes text/references. It checks
the gate, stores the complete request, and applies the corresponding core operation
through the pinned runtime. Repeated ID with changed payload conflicts.
`autonomy complete --wake-id ID --request FILE` accepts measured research feedback,
source record IDs, summary, a new question and optional notification. It verifies record
references, applies feedback with a stable ID, stores a new sourced core question where
appropriate and archives the result. Interrupted/unknown external results stay pending.
`autonomy check --wake-id ID` must precede tools. Tools run in the host, not this package.

The CLI exposes configure/status/register-prompt/start/check/complete/outbox/delivered/
reconcile/close-turn. Receipts must make command outcomes and blockers inspectable.
The optional proactive response is delivered by the heartbeat's own final assistant
message in this chat. The Stop hook acknowledges a reserved message only when its exact
saved text appears in the scheduled turn's visible final response. No fake sent receipts.
`check` requires a unique `--step-id`, `--kind repo|web`, and `--target`; at most four
external steps per wake by default. Repeated step reservations do not authorize another
tool call. `delivered --receipt FILE` accepts a JSON evidence object for explicit manual
reconciliation only; the normal path is acknowledgment by Stop.

## Host integration and constraints

SessionStart restores identity; it does not independently initiate a model turn or
guarantee a greeting in an empty chat. Heartbeats provide genuine model activations.
Trust review remains a host/user action; never grant trust or bypass it programmatically.
An untrusted/unobserved hook, missing scheduled-turn match, paused life, uncertain wake,
unacknowledged delivery or inaccessible paths must be surfaced as a setup/blocker rather
than represented as successful autonomous work. The private archive remains outside Git.

## Verification

Test two concurrent wakes, duplicate IDs, core-commit/retry, returning human, long open
turns, stale/uncertain lease, midnight/cooldown boundaries, fake scheduler-like prompt,
dream without preference learning, budget/pause/pending gates, provenance, safe notification
reservation/ack, and same identity across processes. Validate actual installed entrypoints
separately from host trust and real unattended invocation. Read-only/public-source scope is
enforced by the host workflow; no general-purpose shell/browser executor is added.
