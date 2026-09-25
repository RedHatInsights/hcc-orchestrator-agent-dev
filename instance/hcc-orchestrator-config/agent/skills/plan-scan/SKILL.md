---
name: plan-scan
description: >
  Decompose a cross-service scan epic into one read-only analysis child ticket per
  target service. Resolves the target set from the service-registry, creates a
  Jira sub-ticket per service (labelled `hcc-ai-orchestrator` + `needs-investigation`
  + `repo:<name>` + `scan:<epic-key>`), links each to the epic, and records the plan.
  This is the fan-out step that lets the bot work a broad scan one-service-per-cycle
  across the loop.
when_to_use: >
  When a scan-coordinator epic (labels `hcc-ai-orchestrator` + `hcc-scan`) is picked
  up and has no analysis children yet. Run once per epic to create the per-service
  analysis tickets.
user-invocable: true
allowed-tools:
  - Read
  - "Bash(python3 .claude/skills/service-registry/registry.py *)"
  - mcp__mcp-atlassian__jira_get_issue
  - mcp__mcp-atlassian__jira_download_attachments
  - mcp__mcp-atlassian__jira_create_issue
  - mcp__mcp-atlassian__jira_create_issue_link
  - mcp__mcp-atlassian__jira_update_issue
  - mcp__mcp-atlassian__jira_add_comment
  - mcp__bot-memory__*
---

# plan-scan — decompose a scan epic into per-service analysis tickets

## Preconditions

- The epic carries `hcc-ai-orchestrator` (bot pickup) + `hcc-scan` (scan marker) and
  states the **scan focus** in its summary / description. The focus is whatever the
  requester wants analyzed — this skill makes no assumption about the dimension.
- The epic optionally constrains the target set, two ways:
  - a **`group:platform`** or **`group:tenant`** label on the epic, or
  - a **`Services:` line** in the epic description — comma-separated registry repo
    names, e.g. `Services: advisor-backend, patchman-engine, ros-backend`.

  Precedence: if a `Services:` line is present, use it (intersected with the
  registry) and ignore any `group:` label. If only a `group:` label is present, use
  that group. If neither is present, default group: **`all`**.

Idempotency: first `jira_get_issue` the epic and list existing child links. If
analysis children already exist, do NOT recreate them — comment the current plan
status and stop.

## Steps

1. **Determine focus + target set.** Read the epic (`jira_get_issue`). Copy its focus
   verbatim (do not reinterpret it). If the epic has **attachments** (a spec, a target
   list, a reference doc), pull them with `jira_download_attachments` and `Read` them —
   they are part of the brief, and each analysis child's description should point to
   the relevant one. (Pasted Google Doc / external URLs are not fetchable — the bot has
   no web access; only ticket text and attachments are usable.) Determine the target
   set with the precedence above:
   - **`Services:` line present** → those repos (validate each against the registry;
     flag any unknown name in the plan comment).
   - **else `group:` label** → `registry.py list --group <platform|tenant> --json`.
   - **else** → `registry.py list --group all --json`.

   Drop any target whose `status != ok` (missing from project-repos.json); list
   those in the plan comment as blocked-until-added.
2. **Create one analysis child per target** with `jira_create_issue`:
   - **Summary:** `[analysis] <focus> — <repo>`
   - **Description:** the focus copied from the epic (the questions to answer), plus
     the instruction: *read-only; use /scan-service; do not modify the repo or open a
     PR.*
   - **Labels:**
     - `hcc-ai-orchestrator` — bot pickup label (required or the bot never picks it up).
     - `needs-investigation` — routes to read-only investigation (the analyst persona
       via `/scan-service`), never the implement loop.
     - `repo:<name>` — the single target repo.
     - `scan:<epic-key>` — stable scan id so `/aggregate-scan` can find the whole set.
   - **Issue type:** child of the epic (Story or Sub-task per project config).
3. **Link each child to the epic** (`jira_create_issue_link`, or set parent/epic
   link per project convention).
4. **Post the plan** as a comment on the epic: the focus, the N services being
   scanned (table), any blocked/missing services, and the `scan:<epic-key>` label
   the aggregate step will use.
5. **Record the plan** — `task_add` the epic with `metadata.scan = {focus, group,
   targets: [...], scan_label}` and `last_step: "planned"`, and `memory_store` the
   plan summary.

## Notes

- Do **not** implement anything here and do **not** create implementation tickets —
  that's `/generate-impl-tickets`, run only after analysis + human review.
- Keep the child count sane: one ticket per service. The registry currently holds
  ~37 services (≈21 platform, ≈16 tenant). The default group is `all` — if that would
  create more than ~20 children, post the proposed target list as an epic comment and
  wait for confirmation (or a narrowing `group:`/service list) before creating them.
- The analysis children are worked one-per-cycle by the analyst persona via
  `/scan-service`; `/aggregate-scan` rolls their results back to this epic.
