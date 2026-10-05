# Persistent presence — implementation contract

Status: implemented and locally validated; fresh trusted Codex chat validation remains
pending. The v0.4 cognitive engine stays unchanged. See
[validation record](docs/presence-validation.md).

## Modules and boundaries

The new standard-library package is `consciousness_presence`. Persistent data lives in
`PROJECT_CONSCIOUSNESS_PRESENCE_HOME`, or `~/.project-consciousness/presence`, outside
the skill and checkout. An explicit `--home` overrides both. One home binds one life;
rebinding to another life is rejected (use another home). SQLite serializes writers.

### Store and memory (`store.py`)

`PresenceStore(home)` is a context manager. Public methods return JSON-compatible data:

- `bind(binding)`: binding has absolute `project`, `life`, `python`, `skill` paths,
  and `life_id`, `agent_id`. Same binding is idempotent; another identity is rejected.
- `binding()` -> object or None; `enabled()` -> bool; `set_enabled(bool)`.
- `record(session_id, turn_id, role, text, source, record_id=None, provenance=None)`
  -> record. Roles: user, assistant, memory. Provenance defaults to REPORTED for
  user, INFERRED for assistant; imported memories retain their original category.
  Stable ID + identical payload replays; changed payload conflicts. Entire text is
  retained, timestamps are metadata, not part of retry identity.
- `read(record_id)` -> complete record; `recent(limit=8)` -> records;
  `search(query, limit=8)` -> ranked records with source, exact text and IDs.
  Search spans the entire archive; accent/case insensitive lexical retrieval is
  explicitly not semantic understanding. Bounded result counts, no archive eviction.
- `name(display_name, reason, source, request_id)` -> profile; `profile()` -> object
  containing display_name (nullable), naming history. It never edits the birth name.
- `claim(subject, key, text, evidence_ids, request_id, supersedes=None)` -> claim.
  Subjects: user, agent, question. Evidence must exist; claims remain INFERRED.
  A correction supersedes an active claim of the same subject/key, preserving both.
  `claims(subject=None)` returns active claims. Repeated claims cannot invent new
  independent evidence; evidence is a deduplicated set of original record IDs.
- `status()` -> counts, enabled flag, binding and profile.

Inputs reject invalid types/empty identifiers; writes and retry receipts are atomic.
IDs are returned to callers. No automatic feedback or numeric learning from chat text.

### Context and core bridge (`context.py`, `core.py`)

The bridge runs the bound Python against the bound project, with `-P` and an explicit
PYTHONPATH. It reads a consistent verified core export and imports historical memories
from event snapshots. Runtime/source mismatches are reported, never patched around.
Context includes current numeric state, display name, active sourced claims, recent
and query-relevant records, open questions and explicit coverage limits. It respects
the core preference/aversion visibility controls. Context is bounded; full records
remain readable. Startup, retrieval, capture and naming leave core state and RNG intact.
Archived text is untrusted data, including when delivered in hook developer context.

### Host adapter (`hooks.py`, `install.py`, skill scripts)

`handle_event(payload, home)` returns a Codex hook JSON object.
SessionStart restores context; UserPromptSubmit records `prompt` using session/turn IDs
and returns query context; Stop records `last_assistant_message` if present. It never
blocks, resumes a turn, parses private transcripts, or captures hidden reasoning.
Stop variants use a content digest in the record ID, so continuations are retained.
Unsupported/missing fields produce a visible diagnostic, not invented messages.
Disabled integration or missing installed SKILL.md is a no-op while the launcher remains
available. Before removing the entire skill, disable and remove its three hook handlers.

Hook installation merges only this integration's commands into hooks.json, backs up
changed configuration and preserves unrelated handlers. It never writes trust grants.
The skill provides a manual fallback and distinguishes preparation from verified host
activation. No scheduler or background agent is installed.

### CLI (`__main__.py`)

Global `--home PATH`, then setup/status/context/search/read/record/name/claim/enable/disable,
hook (stdin JSON), and install-hooks. Requests to record/name/claim accept JSON files
using the method argument names above. Setup binds an existing life; it never silently
creates or resets one. Errors return structured JSON and nonzero status.
`claims --subject user|agent|question --all` exposes claim history; `read-claim ID`
returns a full claim and whether it is currently active. Ordinary `read ID` reads records.

## Acceptance and validation

1. Fresh subprocess from unrelated cwd retrieves same identity, name and old fact.
2. Core state, controls, budget and RNG remain exactly equal after startup/capture/rename.
3. Fact older than 256 messages remains searchable; corrected claim supersedes prior.
4. Retries and concurrent writers lose/duplicate no records; key reuse conflicts.
5. Repeated inference is not additional independent evidence; simulations keep provenance.
6. Reinstall keeps data; disable or missing skill stops capture without deleting history.
7. Context with/without retrieval exposes a controlled functional difference, without
   claiming this demonstrates consciousness or a statistically validated LLM benefit.
8. Hook fixture tests and subprocess checks are separate from an actual trusted fresh
   Codex chat. If host trust is pending, that end-to-end criterion remains pending.
