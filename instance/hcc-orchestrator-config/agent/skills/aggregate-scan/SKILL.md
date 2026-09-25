---
name: aggregate-scan
description: >
  Roll the per-service analysis findings back up to the scan epic as one aggregated
  markdown table plus common-patterns / outliers / follow-ups, and run a
  completeness reconciliation so no target was skipped. Read-only: writes only to
  the epic (comment/description) and memory.
when_to_use: >
  When all (or a chosen subset of) analysis children of a `hcc-scan` epic have
  posted their findings (`last_step: analysis_posted`). Run to produce the
  epic-level summary the humans review before implementation tickets are generated.
user-invocable: true
allowed-tools:
  - Read
  - "Bash(python3 .claude/skills/service-registry/registry.py *)"
  - mcp__mcp-atlassian__jira_get_issue
  - mcp__mcp-atlassian__jira_search
  - mcp__mcp-atlassian__jira_update_issue
  - mcp__mcp-atlassian__jira_add_comment
  - mcp__bot-memory__*
---

# aggregate-scan — roll per-service findings up to the epic

## Steps

1. **Collect the children.** Find the analysis tickets by the `scan:<epic-key>`
   label (`jira_search`) and/or the epic's issue links. For each, read the
   structured findings — prefer the task record's `metadata.findings` (one source
   of truth), falling back to parsing the per-service Jira comment.
2. **Build the aggregate table** and post it to the epic (as a comment, and/or
   update the epic description — the epic is where the human wants the summary):

   ```markdown
   # Scan: <focus>
   Scanned <N> services on <date>. Branch@HEAD per service in the table.

   ## Executive summary
   <2-4 sentences: dominant pattern, outliers, actionable takeaway>

   ## Per-service findings
   | Service | Stack | Branch@HEAD | Verdict | Key evidence |
   |---|---|---|---|---|

   ## Common patterns
   <the point of the scan - what's shared across services>

   ## Outliers / exceptions
   ## Recommended follow-ups (feed /generate-impl-tickets)
   | Target | core-hcc / tenant / both | Change |
   |---|---|---|
   ```
3. **Completeness reconciliation.** Diff the scanned set against the registry
   target set (`registry.py list --group <group>`). Flag any target that has no
   analysis child or no posted findings, and any target missing from
   project-repos.json. List these under "Outliers / follow-ups" — never silently
   drop a service.
4. **Persist.** `memory_store` the cross-service conclusion (the common pattern and
   the outliers for this focus) with `tags`; update the epic task record with
   `last_step: "aggregated"` and a `metadata.followups` list the next step reads.
5. Do **not** create implementation tickets here. Leave the epic for human review;
   `/generate-impl-tickets` runs after sign-off.

## Notes

- Prefer the structured `metadata.findings` from each child over re-reading repos —
  aggregation is read-only and should not re-scan.
- If some children are still unscanned, aggregate what exists and clearly mark the
  gaps rather than waiting for 100%.
