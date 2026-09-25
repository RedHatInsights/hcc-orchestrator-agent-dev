---
name: scan-service
description: >
  Read-only analysis of ONE HCC service against a scan focus that is defined in the
  ticket. Clones/reads the repo, greps the hot spots relevant to the stated focus,
  and produces a per-service verdict with file:line evidence plus a findings
  checklist - then posts it to the Jira ticket and stores the durable conclusion in
  memory. NEVER modifies the target repo, pushes, or opens a PR. The focus is
  generic: whatever the ticket asks (a dependency, a pattern, a migration, config,
  a version, an API usage, ...).
when_to_use: >
  When working a scan analysis ticket (labels `needs-investigation` + `scan:<epic>`)
  that targets a single service via a `repo:<name>` label. One service per cycle.
  Load the analyst persona first.
user-invocable: true
allowed-tools:
  - Read
  - Grep
  - Glob
  - "Bash(git clone *)"
  - "Bash(git -C *)"
  - "Bash(git fetch *)"
  - "Bash(grep *)"
  - "Bash(rg *)"
  - "Bash(ls *)"
  - "Bash(find *)"
  - "Bash(cat *)"
  - "Bash(gh api *)"
  - "Bash(python3 .claude/skills/service-registry/registry.py *)"
  - mcp__mcp-atlassian__jira_get_issue
  - mcp__mcp-atlassian__jira_add_comment
  - mcp__mcp-atlassian__jira_update_issue
  - mcp__bot-memory__*
---

# scan-service — per-service read-only analysis

The per-service worker for a decomposed cross-service scan. It carries a reusable
scan *methodology* (evidence discipline, canonical-repo resolution, authoritative-
signal and negative-finding discipline) that is independent of any particular
analysis. **The subject of the scan comes entirely from the ticket** — this skill has
no built-in dimension.

**READ-ONLY, ALWAYS.** This skill's `allowed-tools` exclude `Edit`, `Write`, and all
mutating git (`commit`/`push`) and PR creation. Do not modify the target repo. Do not
open a PR. The only writes are: a Jira comment, a Jira field update on the analysis
ticket, and `memory_store`.

## Inputs (from the ticket)

- The analysis **focus** — the question(s) to answer, taken verbatim from the ticket
  description. This is whatever the requester wants investigated; do not assume a
  dimension. `/plan-scan` copies the epic's focus into each child.
- The **service** — the single `repo:<name>` label on the ticket.

If either the focus or the service is missing or ambiguous, post a Jira comment
asking for clarification and stop — do not guess the focus.

## Steps

1. **Read the focus** from the ticket (`jira_get_issue`). Restate it as concrete,
   answerable questions before you start. If the ticket supplies specific search
   terms, acceptance criteria, or a definition of "done", use them.
2. **Load registry context.** `registry.py resolve <repo> --json` for the stack,
   `upstream`, and `host`. `memory_search` the repo + focus keywords for anything
   already known so you build on it instead of repeating it.
3. **Get the active repo.** Clone shallow into `./repos/<repo>/` from `upstream`
   (read-only; no fork needed). For `host: gitlab` use the gitlab upstream URL.
   **Resolve the canonical *active* repo before trusting anything you find** — scanning
   a dead mirror produces false negatives. Check for archived/EOL/migrated:
   - `gh api repos/<org>/<repo> --jq .archived` (true → archived),
   - a stale last-commit date, or a `"Prepare for archive"`-style HEAD commit.

   If archived/EOL/migrated, the live code is usually on gitlab.cee.redhat.com — scan
   that instead; if it's unreachable from this environment, tag every finding
   "unverified — stale mirror" and emit NO definitive negative. Record `branch@HEAD`
   for reproducibility.
4. **Probe siblings** for multi-repo/variant services before concluding absence
   (e.g. `<svc>-ocp-backend`, service families).
5. **Investigate the focus.** Derive search patterns from the focus + the repo's
   stack (see "Searching by stack" below), grep the hot spots, and read them. Answer
   each question with **file:line evidence**. Cursory by default (grep + read hot
   spots); escalate to a deeper trace only where the cursory result is ambiguous.
   Exclude `vendor/`, `node_modules/`, `.git/`, `__pycache__/`, tests (note a test
   only if it reveals a production pattern).
6. **Authoritative-signal discipline.** Do NOT assert yes/no from a loose keyword
   match — a keyword can be a comment, a variable name, a vendored file, or a false
   cognate (a real miss: "export" matched a Candlepin manifest, not the Export
   service). Anchor each verdict on the *authoritative/structural* signal for the
   question — a manifest/lockfile entry, a config/dependency block, a concrete API
   path, a schema or migration, an actual call site. Treat a bare keyword hit as a
   lead to verify, not as evidence.
7. **Negative-finding discipline.** A "no / n/a / not present" verdict MUST state
   *which* signals you searched and found empty — never a bare "n/a". A negative is
   only valid against the canonical active repo; from an archived/unreachable mirror,
   downgrade it to "unverified".
8. **Emit the per-service result** (format below) as a Jira comment on the analysis
   ticket, and `jira_update_issue` to reflect the verdict/summary.
9. **Persist.** `memory_store` the durable conclusion (category `codebase_pattern`
   or `learning`, with `repo` + `tags`). Update the analysis task record
   (`task_update`) with `last_step: "analysis_posted"` and a structured
   `metadata.findings` block so `/aggregate-scan` can roll it up.
10. Do **not** transition the ticket to done or archive it — analysis tickets stay
    open until the aggregate + human review.

## Searching by stack (generic guidance)

The catalog gives each service a `stack`. Use it to know *where* to look; derive the
*terms* from the ticket's focus, not from any fixed list:

- **Python** (Django/FastAPI) — models, views/routers, settings, `requirements`/
  `Pipfile`/`pyproject.toml`, `clowdapp`/deploy yaml.
- **Go** — `go.mod`, handlers, `internal/`/`pkg/`, config, `clowdapp` yaml.
- **Ruby** (Rails) — models, controllers, policies, `Gemfile`, `config/`.
- **Java** (Quarkus) — `pom.xml`/`build.gradle`, resources, `application.properties`.
- **Node/TS** — `package.json`, `src/`, DB/query layer, `tsconfig.json`.

For dependency/config-style focuses, the authoritative signal is usually the ClowdApp
`dependencies:` block, manifest/lockfiles, and concrete API paths — not a loose
keyword match. Require a concrete signal before asserting yes/no.

## Per-service result format (the Jira comment)

```markdown
### Scan: <focus from the ticket> — <repo>

**Verdict:** <one line — the headline answer to the focus>
**Stack:** <stack>   **Branch@HEAD:** <branch>@<short-sha>

#### Findings
| Question (from focus) | Answer | Evidence (file:line) |
|---|---|---|
| ... | ... | `path/to/file:123` |

#### Checklist
- [ ] <actionable item this service needs for the focus>

#### Signals searched (for any negative)
- <signal> — <found / not found>

#### Suggested follow-up (feeds /generate-impl-tickets)
- <core-hcc | tenant | both>: <short description of the implementation change>
```

Keep the structured `metadata.findings` on the task in sync with this comment so the
aggregate step reads one source of truth.
