# PROJECT CONSCIOUSNESS

[Español](README.md) | [English](README.en.md)

**An open-source experimental laboratory for investigating functional properties associated with consciousness.**

The project builds systems with persistent memory, models of their own capabilities, learned preferences, questions, and simulation. Its central question is how internal states causally change subsequent decisions and what happens when those states are intervened on.

The project began as a nonprofit research initiative dedicated to scientific, computational, and philosophical exploration. Its goal is to produce reproducible experiments on these properties. Its results are not interpreted as demonstrations of subjective experience.

**Current engine: MVP v0.4, with a v0.5 layer for conversational presence and bounded autonomy.** A Python core, SQLite persistence, controlled experiments, and a skill for connecting an LLM agent such as Codex. Contributions in programming, methodology, cognitive science, philosophy, documentation, and independent reproduction of results are welcome.

To update an existing installation and enable activity between conversations, see the [v0.5 update README](README.update-v0.5.en.md).

[Quick start](#quick-start) · [How to contribute](#how-to-contribute) · [Experiments](#experiments-and-results) · [Documentation](#structure-and-documentation) · [License](#license)

## What is implemented

| Component | Current capability |
|---|---|
| Memory and persistence | States and events in SQLite, memories with provenance, restarts, branches, and verifiable replay. |
| Functional identity | Five random, reproducible initial priorities: understand, create, explore, finish, and connect. |
| Learning | Updates to preferences, success estimates, and recoverable aversions based on recorded outcomes. |
| Questions and reflection | Questions about identity or the world; open questions can influence activity selection. |
| Simulation | Bounded local scenarios, called “dreams,” with references and an independent random stream. |
| Limited agency | Numerical activity selection, a budget, a persistent pause, and finite local cycles. |
| LLM integration | A skill lets the host propose activities, use its tools, and record outcomes. |
| Conversational presence | A personal message archive, lexical search, a display name, and revisable conclusions with sources; a Codex hook adapter. |
| Bounded autonomy | A coordinator for activity during human inactivity, reservations and receipts, research/dream/reflection modes, and a proactive message outbox; requires an authorized host automation. |
| Laboratory | Controls for blocking memory, freezing learning, neutralizing preferences, and comparing histories. |

The broader architecture also proposes metacognition, affect regulation, world models, and planning. These proposals are not fully implemented: see the [capability map](CAPABILITY-MAP.md) and the [v0.4 contract](docs/mvp-v0.4.md) to distinguish the current scope from future work.

## Quick start

You need **Git and Python 3.12 or later with `sqlite3` available**. The core uses only the standard library; you can run the example without installing dependencies, obtaining an API key, or connecting an LLM.

Clone the repository and enter its root directory:

```sh
git clone https://github.com/AeonMuller/PROJECT-CONSCIOUSNESS.git
cd PROJECT-CONSCIOUSNESS
python --version
```

The examples use `python`; replace it with `python3` if that is the Python 3.12+ executable on your system. In PowerShell, you can enable UTF-8 to preserve accented characters when redirecting JSON: `$env:PYTHONUTF8 = "1"`.

Create an identity, import a project document, and run six cycles:

```sh
python -m project_consciousness life init --out runs/aeon --name Aeon --budget 40
python -m project_consciousness life ingest --life runs/aeon --file docs/decisions/0005-persistent-functional-identity.md --domain understand
python -m project_consciousness life run --life runs/aeon --cycles 6
python -m project_consciousness life context --life runs/aeon
python -m project_consciousness life verify --life runs/aeon --mode recompute
python -m project_consciousness life export --life runs/aeon --out runs/aeon-diary
```

The identity starts without fictional memories. Without `--seed`, a new seed is generated and recorded; add `--seed 17` to `init` to reproduce a set of initial predispositions. The imported document is stored as reported information. Cycles can read it, formulate a question, and generate a simulation.

Open `runs/aeon-diary/diary.md` to inspect the result. State, context, a manifest, and events are also exported. The creation and export directories must be **new**: change their names to repeat the example. Data you generate under `runs/` is excluded from Git.

For finite local activity with a delay between cycles:

```sh
python -m project_consciousness life watch --life runs/aeon --cycles 10 --interval 5 --stop-file runs/aeon.stop
```

You can stop it with `Ctrl+C`, by creating the `runs/aeon.stop` file, or by running `python -m project_consciousness life pause --life runs/aeon` from another terminal. View all commands with `python -m project_consciousness life --help`.

## Connecting an LLM agent

The core operates independently of the language model. The [PROJECT CONSCIOUSNESS skill](skills/project-consciousness/SKILL.md) defines the workflow for a host to consult the state, propose candidates, respect the core's choice, and return an outcome with its source.

The versioned wrapper can be run directly from the repository root:

```sh
python skills/project-consciousness/scripts/consciousness.py --project . context --life runs/aeon
```

If the skill is already installed in Codex, an example request is:

> Use $project-consciousness with this repository and the life at runs/aeon. Consult its history, propose two investigations, and let the core choose one. Carry out the chosen investigation, record the sources and outcome, and formulate a new question.

The [skill protocol](skills/project-consciousness/references/protocol.md) describes the JSON contracts, pending decisions, and retries. The [Codex and VS Code guide](docs/codex-identity-quickstart.md) provides a more detailed walkthrough; its absolute paths refer to the original environment and must be replaced with those on your machine.

External research and free-form reflections require an active LLM host and its available tools. `watch` runs local activity while its process is open; installing the skill does not start a permanent service.

### Continuing an identity across chats

The `consciousness_presence` layer binds an existing life and stores conversation in `~/.project-consciousness/presence`, outside the skill and checkout. It also accepts `PROJECT_CONSCIOUSNESS_PRESENCE_HOME` or `--home PATH` before the command. Updating the skill preserves this archive. The original life stays in its existing location; opening a chat, capturing messages, or changing the display name leaves priorities, budget, and RNG unchanged.

From the repository root, replace `PYTHON_PATH` with the absolute path to the interpreter compatible with your life and `SKILL_PATH` with the installed skill directory:

```sh
python -m consciousness_presence setup --project . --life runs/aeon --python PYTHON_PATH --skill SKILL_PATH
python -m consciousness_presence status
python -m consciousness_presence context --query "memoria"
python -m consciousness_presence search "memoria" --limit 8
```

You can find the current interpreter path with `python -c "import sys; print(sys.executable)"`. An existing life requires compatible sources and runtime versions; `setup` does not create a replacement if it cannot open that life. To query from another directory after binding it, use `python SKILL_PATH/scripts/presence.py context`; the launcher reads the project path from the personal registry. `--project PROJECT_PATH` lets you specify it explicitly.

The skill converses naturally, retrieves relevant episodes, and keeps the user's reported preferences separate from the agent's conclusions about itself. It chooses or agrees on a display name at the first encounter if one is missing; it does not impose the name used in the earlier example. Conclusions can be corrected while preserving their sources. Numerical learning remains tied to activity outcomes, without an automatic reward for each message.

To prepare capture at chat startup and during turns, replace `CODEX_HOME_PATH` with your Codex configuration directory:

```sh
python -m consciousness_presence install-hooks --codex-home CODEX_HOME_PATH
```

The installer merges the configuration with other hooks and backs up changes. **Preparing hooks does not prove they are active:** review their trust through `/hooks` in a supporting host, then test a real new chat. Until that check is complete, manual operation remains available:

> Use $project-consciousness with my linked identity. Retrieve the relevant memories and let us continue our conversation.

See the [presence guide](skills/project-consciousness/references/presence.md) for recording, reading, and revising memories, choosing a name, and enabling or disabling the integration. Search is lexical and context is bounded; it does not promise to recall conversations that were never captured. These steps do not create a schedule. [Contract and acceptance criteria](SPEC-presence.md), [architecture decision](docs/decisions/0006-persistent-conversational-presence.md).

### Autonomous activity and conversational initiative

With an authorized automation, Codex can wake this same chat, restore the identity, and carry out one bounded activity. The coordinator checks for open human turns, sufficient time without interaction, available core budget, an unpaused life, and no pending decision. When the user returns, new steps stop and already obtained results are preserved for reconciliation.

The proposed initial configuration is one wake per hour, thirty minutes of inactivity, up to three activities and two proactive messages per UTC day, and four hours between messages. Scheduling and enabling are explicit; the core budget is never replenished automatically. Initial scope permits reading the bound repository and public Internet sources.

For research, the host proposes candidates, the core chooses, and the host executes the activity with sources and bounded feedback. Dreaming, reflection, and rest are separate modes. A simulation may produce a question, but it does not become an empirical success or receive a fabricated reward.

A relevant finding can generate a proactive message. It is reserved in an outbox and delivered as the heartbeat's own final response in this chat; the hook acknowledges the visible text. An uncertain delivery is not automatically retried. Wakes with no meaningful change or required action remain quiet.

```sh
python -m consciousness_presence autonomy status
```

The [autonomy guide](skills/project-consciousness/references/autonomy.md) covers configuration, scheduling, execution, and reconciliation. Preparing hooks does not demonstrate an actual unattended run. `SessionStart` restores context and does not guarantee a greeting in an empty chat. [Contract](SPEC-autonomy.md), [architecture decision](docs/decisions/0007-bounded-idle-autonomy.md).

## Experiments and results

The experiments distinguish three questions: whether the testbed works correctly, whether a state causally changes a decision, and whether that mechanism benefits a particular task.

| Protocol | What it investigates | Evidence and scope |
|---|---|---|
| E0 | Persistence and replay after restarts | [v0.1 results](reports/README.md) |
| E1 | Causal use of memory through blocking and interventions | [v0.1 scope](docs/mvp-v0.1.md) |
| L1 | Acquisition and reversal of binary associations | [v0.2 report](reports/l1-v0.2/report.md) |
| E2 | Estimation of tool reliability and adaptation | [v0.3 report](reports/e2-v0.3/report.md) |
| I1 | Preferences, aversion, learning, simulation, and continuity | [v0.4 report](reports/i1-v0.4/report.md) |

To run the test suite and a short identity pilot:

```sh
python -m unittest discover -s tests -v
python -m project_consciousness life experiment --seeds 400:403 --out runs/i1-demo
```

`400:403` includes seeds 400, 401, and 402. To reproduce the full I1 pilot, use `400:420` and a new output directory. The report is saved to `runs/i1-demo/report.md`.

The **v0.4** release recorded **163 passing tests**, **140 databases**, **1,200 follow-up choices**, and **401/401 valid checks**. Neutralizing preferences changed the first choice in 9 of 20 histories; restarting preserved functional states and events. I1 uses predefined synthetic feedback. Its dream control verifies that simulations are suppressed, without evaluating whether dreaming improves subsequent decisions.

The [reports and summarized data](reports/README.md) include protocols, metrics, checks, and limits of interpretation. The full I1 pilot databases are not included in Git; they can be regenerated by running the protocol. The [Codex demonstration](reports/codex-v0.4/report.md) does include a small database and an [example diary](reports/codex-v0.4/diary.md).

Each run records versions, a seed, and a code fingerprint. Continuing or recomputing a history requires its original sources and Python/SQLite versions. After modifying the engine, create a new run or use the [v0.4 archive](releases/project-consciousness-v0.4.zip) and its [manifest](releases/project-consciousness-v0.4.json). For a life created with `life`, `life verify --life runs/aeon --mode reconstruct` allows integrity checks without requiring identical sources.

## How to contribute

Contributions can start with an independent reproduction, a small correction, or a methodological question. You do not need to work on every module or subscribe to a particular theory of consciousness.

- **Bugs and reproducibility:** report the command, version or commit, Python/SQLite versions, seed, expected result, and observed result.
- **Code and tests:** improve contracts, persistence, causal controls, adapters, and reproducible failure cases.
- **Experimental design:** propose tasks, comparators, interventions, and criteria that could refute a hypothesis.
- **Interdisciplinary review:** contribute primary sources, objections, and limits on translating scientific or philosophical concepts into software.
- **Documentation and accessibility:** correct examples, explain results, or contribute translations. Proposals in Spanish and English are welcome.

To contribute:

1. Review the [existing issues](https://github.com/AeonMuller/PROJECT-CONSCIOUSNESS/issues) or [open one](https://github.com/AeonMuller/PROJECT-CONSCIOUSNESS/issues/new) describing the problem or proposal. For broad changes, first explain the objective and how it will be evaluated.
2. Fork the repository and create a branch for a specific change. Use the quick start to become familiar with the project.
3. Keep the change focused. If it changes behavior, add relevant tests; if it changes contracts or hypotheses, update the specification and document the decision before comparing results.
4. Run the relevant checks. For code changes, use the suite shown above; for documentation, check links and examples.
5. Open a [pull request](https://github.com/AeonMuller/PROJECT-CONSCIOUSNESS/pulls) explaining the problem, the change, how it was verified, and its limitations. Link the issue when one exists.

Preserve experimental seeds, configurations, and provenance. Simulations must remain identified as such; null results, costs, and failures are also part of the evidence. Avoid including credentials or personal data in shared examples.

### Proposed research areas

- Semantic retrieval and evaluation of consolidation over the conversational archive.
- Question tracking: supporting or conflicting evidence, revision, and closure.
- Curiosity based on information gain and source evaluation.
- Metacognition and uncertainty calibration.
- Evaluation of the effect of simulations on subsequent decisions.
- Joint learning about the world and capabilities, retention, and transfer.
- Adapters for other LLM agents and reproducible comparisons between hosts.

These are open research directions, not capabilities already delivered or schedule commitments.

## Structure and documentation

This README is available in Spanish and English. Most of the linked technical documentation is currently in Spanish; translations are also welcome.

| Path | Contents |
|---|---|
| [`project_consciousness/`](project_consciousness/) | Core, persistence, CLI, and laboratories. |
| [`consciousness_presence/`](consciousness_presence/) | Conversation archive, profile, retrieval, context, and hook adapter. |
| [`skills/project-consciousness/`](skills/project-consciousness/) | Instructions, wrapper, and protocol for the LLM host. |
| [`tests/`](tests/) | Tests for behavior, recovery, provenance, and experiments. |
| [`configs/`](configs/) | Configurations and conditions for the E0/E1/L1/E2 laboratories. |
| [`docs/`](docs/) | Architecture, foundations, contracts, and decisions. |
| [`reports/`](reports/) | Recorded results and limits of interpretation. |
| [`releases/`](releases/) | Archived engines for reproducing earlier runs. |

The v0.4 implementation separates pure transitions (`identity_state`), persistence (`identity_runtime`), the interface (`identity_cli`), the I1 experiment (`identity_experiment`), and the skill. Identity databases are independent of the earlier laboratories.

Key reading:

- [Capability map](CAPABILITY-MAP.md), [conceptual architecture](docs/architecture.md), and [interfaces and state](docs/interfaces-and-state.md).
- [Scientific foundations](docs/scientific-foundations.md), [critical Gateway analysis](docs/gateway-analysis.md), and [proposed protocols](docs/experiments.md).
- [v0.4 specification](docs/mvp-v0.4.md) and [persistent identity decision](docs/decisions/0005-persistent-functional-identity.md).
- [Presence across conversations](docs/persistent-presence-proposal.md), [presence contract](SPEC-presence.md), and [skill guide](skills/project-consciousness/references/presence.md).
- [v0.5 update](README.update-v0.5.en.md), [autonomy contract](SPEC-autonomy.md), and [autonomous activity guide](skills/project-consciousness/references/autonomy.md).
- Specifications for the [runtime](SPEC-runtime.md), [memory](SPEC-memory.md), [cognition](SPEC-cognition.md), [laboratory](SPEC-experiment-lab.md), and [language adapter](SPEC-language-adapter.md).
- [Changelog](CHANGELOG.md) and [results from the different versions](reports/README.md).

## Scientific standards and limitations

The documentation distinguishes empirical results (**E**), theories or models (**T**), engineering decisions (**I**), philosophical questions (**F**), and claims without sufficient support (**U**). An implementation inspired by a theory still needs its own tests. The Gateway Process analysis separates the document's content from its scientific support; declassification is not treated as an endorsement of its claims.

Memories distinguish `OBSERVED`, `REPORTED`, `INFERRED`, and `SIMULATED`. Current learning changes core parameters, not LLM weights. The five preference dimensions are fixed; local dreams use templates; v0.4 core questions do not yet have a closure operation. The conversation layer stores revisable conclusions without changing that contract. These numerical states are not considered demonstrations of human personality, fear, or trauma.

The project does not propose an aggregate score that certifies consciousness. Its value lies in making its mechanisms explicit, testing them, and enabling others to question and reproduce its results.

## License

PROJECT CONSCIOUSNESS is distributed under the [MIT License](LICENSE). It permits using, copying, modifying, distributing, and selling the software, including private modifications, provided the copyright notice and permission notice are preserved in all copies or substantial portions of the software. It does not require publishing modifications.

The project's nonprofit research purpose does not limit these permissions. The full `LICENSE` text specifies the conditions and warranty disclaimer.

If you use the project in research, a product, or a derivative work, a mention of **PROJECT CONSCIOUSNESS, by AeonMuller**, and a link to [the original repository](https://github.com/AeonMuller/PROJECT-CONSCIOUSNESS) are appreciated. This public credit is a voluntary request, separate from the obligation to preserve the MIT notices.
