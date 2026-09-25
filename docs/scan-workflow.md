# HCC cross-service scan workflow

This instance can run a **cross-service analysis** — a scan whose subject is defined
per-ticket by whoever files it — as a decomposed, Jira-driven, human-gated pipeline,
then turn the findings into implementation tickets that flow through Rehor's normal
implement→PR loop.

It is generic tooling: the skills carry a reusable scan *methodology* (target
selection, evidence discipline, canonical-repo resolution, aggregation), but **no
built-in analysis dimension**. The requester writes the focus in the epic — a
dependency, a code pattern, a migration, a config, a version, an API usage, anything.

It ports the methodology of the local `/tenant-services` skill into Rehor's runtime
model. Key difference: `/tenant-services` fans out N parallel subagents in one
session; Rehor works **one ticket → one repo → one persona per cycle** (the `Task`
subagent tool is not in the runtime allow-list), so breadth comes from the *loop*
(many analysis tickets across cycles), not from in-cycle parallelism.

## Components (all under `instance/hcc-orchestrator-config/agent/`)

| Kind | Name | Role |
|---|---|---|
| skill | `service-registry` | Analysis-agnostic catalog of service repos (stack, group=platform/tenant), resolved against `project-repos.json`. `registry.json` + `registry.py`. |
| skill | `scan-service` | **Read-only** per-service analysis; the focus comes from the ticket. |
| skill | `plan-scan` | Decompose a `hcc-scan` epic → one analysis child per service. |
| skill | `aggregate-scan` | Roll per-service findings up to the epic as a table + patterns + reconciliation. |
| skill | `generate-impl-tickets` | After human approval, findings → `hcc-impl` tickets (core-hcc / tenant / both). |
| persona | `analyst` | Read-only auditor. Used for `needs-investigation` scan tickets. Dimension-agnostic. |
| persona | `backend` | HCC-aware implementer (Go/Python/Ruby/Java/Node). Used for `hcc-impl` tickets. |
| persona | `frontend` | Core-HCC console UI implementer (secondary). |

## The four stages (human-gated)

```
Epic  labels: hcc-ai-orchestrator + hcc-scan   (summary + description state the focus)
  │  /plan-scan
  ├─ needs-investigation repo:advisor-backend  ┐  worked 1/cycle by `analyst`
  ├─ needs-investigation repo:patchman-engine  │  via /scan-service (read-only):
  ├─ …                                          ┘  Jira comment + memory + metadata.findings
  │  /aggregate-scan  → epic-level markdown table + patterns + gaps
  │  ── human reviews, adds `impl-approved` ──
  │  /generate-impl-tickets
  ├─ hcc-impl repo:advisor-backend  ┐  normal implement→PR loop,
  └─ …                              ┘  backend/frontend persona

(every ticket above also carries hcc-ai-orchestrator, the bot pickup label)
```

## How a scan runs (generic)

**1. Set up the scan (what a human does once).**
- Create an epic in the bot's Jira project. In the **summary + description, state the
  focus** — the exact question(s) you want answered for each service. Be specific:
  the description becomes the brief every per-service analysis follows. Include search
  terms or a definition of "done" if you have them.
- Label it `hcc-ai-orchestrator` (the bot pickup label — required) **and** `hcc-scan`
  (the scan marker). Optionally constrain the target set with a `group:platform` /
  `group:tenant` label, **or** a `Services: <repo, repo, ...>` line in the description
  (which takes precedence). Default is all services.
- That's it — the bot picks it up on its schedule.

**2. Plan (bot, one cycle).** `/plan-scan` reads the epic, copies the focus verbatim,
resolves the target set:
```
python3 .claude/skills/service-registry/registry.py list --group all --json
```
and creates one `[analysis] <focus> — <repo>` child per service (`hcc-ai-orchestrator`,
`needs-investigation`, `repo:<name>`, `scan:<EPIC-KEY>`), linked to the epic, then
posts the plan. (If it would create more than ~20 children it confirms scope first.)
`/plan-scan` is **additive**: widen the epic's `Services:`/`group:` scope and re-trigger
the epic, and it back-fills children only for the newly in-scope services — one epic can
grow from a small proof to all ~37 without a new epic, and re-running never duplicates.

**3. Analyze (bot, one service per cycle).** For each child, the `analyst` persona
runs `/scan-service`: it reads the focus from the ticket, clones the active repo
read-only, derives stack-appropriate searches from the focus, and answers each
question with `file:line` evidence (plus negative-finding discipline). It posts the
per-service verdict + checklist to the child ticket and stores `metadata.findings`.

**4. Aggregate (bot, one cycle).** `/aggregate-scan` rolls the children into an
epic-level table (service · stack · branch@HEAD · verdict · evidence), the common
pattern, outliers, and a follow-ups table, and reconciles against the registry so no
target is skipped.

**5. Implementation tickets (bot, after human sign-off).** A human reviews the epic
and adds `impl-approved`. `/generate-impl-tickets` then creates `hcc-impl` tickets
(labelled `hcc-ai-orchestrator` + `hcc-impl` + `repo:<name>`) with acceptance criteria,
linked to the analysis tickets. These have **no** `needs-investigation` label, so the
normal loop implements them with the `backend`/`frontend` persona.

## Persona questions answered

- **Do we need backend/frontend/planner for read-only analysis?** No. Analysis uses
  only the `analyst` persona. `backend`/`frontend` are the handoff target for the
  *output* implementation tickets, not part of the scan. No `planner` persona —
  ticket generation is a deterministic, human-gated skill.
- **What tags the output tickets for execution?** `hcc-ai-orchestrator` + `hcc-impl` +
  `repo:<name>` (and a `[core-hcc]`/`[tenant]` scope marker). Persona is auto-selected
  from the target repo's stack. Same instance or another bot can pick them up.

## Read-only enforcement — status & the framework ask

Read-only is enforced two ways today, and one way we recommend adding:

1. **Skill `allowed-tools`** — `scan-service` excludes `Edit`/`Write`/push/PR; the
   SDK narrows tools to this set while the skill runs.
2. **Persona instruction** — `analyst` forbids all mutation.
3. **(Recommended, not yet possible from the instance)** A `PreToolUse` deny-hook
   that blocks `Edit`/`Write`/mutating `Bash` for `needs-investigation` cycles.
   Verified in the runtime: `apply_merged_config` (`bot/merge.py`) merges only
   personas, `project-repos.json`, skills, and `mcp.json` from an instance — **not**
   `.claude/settings.json`/hooks. So a config-only instance cannot ship a hook today.
   The ask to the framework team: either merge instance project-settings hooks, or
   add a `readonly` cycle mode keyed off the `needs-investigation` label. Until then,
   (1)+(2) are strong but not airtight.

## In-cycle parallelism (optional future ask)

If broad scans in a single cycle become desirable, ask the framework team to add
`Task` to `ALLOWED_TOOLS` (`bot/config.py`), which would let a coordinator cycle fan
out read-only Explore subagents like `/tenant-services` does. The decomposed approach
here does not require it.

## Maintenance

`registry.json` is living but analysis-agnostic — update it only when a service is
added, moved, or retired. It is not where analysis dimensions live; those come from
each epic. If a recurring analysis becomes common, capture its brief as a reusable
snippet in the epic template rather than baking a dimension into the skills.
