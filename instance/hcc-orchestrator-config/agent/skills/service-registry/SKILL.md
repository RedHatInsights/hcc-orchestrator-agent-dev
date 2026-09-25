---
name: service-registry
description: >
  Catalog of HCC service repos available as scan targets, with each service's
  primary stack and a coarse group (platform / tenant), resolved against
  project-repos.json. Analysis-agnostic: it says which services exist, not what to
  analyze. The single source of truth for building the target set of a
  cross-service scan. Use at the start of /plan-scan, or to look up one service.
when_to_use: >
  Whenever a cross-service analysis needs its target set - at the start of
  /plan-scan (to enumerate which services get an analysis ticket), or to look up
  one service's stack and repo details before /scan-service.
user-invocable: true
allowed-tools:
  - "Bash(python3 .claude/skills/service-registry/registry.py *)"
  - Read
---

# service-registry — HCC service scan catalog

The seed list for every cross-service scan. It is deliberately **analysis-agnostic**:
it only records which services exist, their primary stack, and a coarse group for
target selection. WHAT to analyze is defined per-ticket, never here.

## List / resolve targets

```bash
# Everything - the default scan set (all services):
python3 .claude/skills/service-registry/registry.py list

# Tenant/consumer services only:
python3 .claude/skills/service-registry/registry.py list --group tenant

# Platform/gateway/authz/pipeline repos only:
python3 .claude/skills/service-registry/registry.py list --group platform

# Machine-readable, for a skill to consume:
python3 .claude/skills/service-registry/registry.py list --group all --json

# One service's row (stack, group, upstream, host):
python3 .claude/skills/service-registry/registry.py resolve advisor-backend --json
```

`--group` accepts `all` (default), `platform` (shared gateway/authz/pipeline/infra),
or `tenant` (customer/consumer-facing services). Each row is resolved against
`project-repos.json` and carries a `status` of `ok` or `MISSING_FROM_PROJECT_REPOS`.

## Rules

- **Treat it as living.** When a service is added, moved, or retired, update
  `registry.json` in the same session.
- **Resolve before scanning.** A target with `status != ok` is not in
  `project-repos.json` — add it there (with `upstream` + `host`) before the bot can
  clone it.
- **GitLab repos** (`host: gitlab`) live on gitlab.cee.redhat.com; some GitHub
  mirrors are archived, so scan the active repo.
- The group is only a convenience for selecting targets. The requesting ticket may
  constrain the set further (explicit service list) or pick a different group.
- Output is a starting point, not a prescription — confirm the target set (or let
  the requesting ticket constrain it) before fanning out analysis tickets.
