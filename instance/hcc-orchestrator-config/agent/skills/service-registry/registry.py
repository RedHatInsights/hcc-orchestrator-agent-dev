#!/usr/bin/env python3
"""Resolve the HCC service scan target set from the catalog.

Reads registry.json (next to this file) and cross-checks each service against
project-repos.json (searched upward from CWD / this file) so the caller gets a
ready-to-work target list with repo/upstream/host and a resolution status.

The catalog is analysis-agnostic: it only says which services exist, their stack,
and a coarse group. WHAT to analyze is defined per-ticket, not here.

Usage:
    python3 registry.py list [--group all|platform|tenant] [--json]
    python3 registry.py resolve <repo> [--json]

Default group: all. Output is a starting point - confirm or constrain the target set
from the requesting ticket before scanning, and update registry.json when a service is
added/moved.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.join(HERE, "registry.json")


def _find_project_repos():
    """Walk upward from this skill dir and from CWD to find project-repos.json."""
    seen = set()
    for start in (HERE, os.getcwd()):
        d = start
        while d and d not in seen:
            seen.add(d)
            candidate = os.path.join(d, "project-repos.json")
            if os.path.isfile(candidate):
                return candidate
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
    return None


def _load_json(path):
    with open(path) as fh:
        return json.load(fh)


def _group_filter(group):
    group = (group or "all").lower()
    if group == "all":
        return lambda g: True
    return lambda g: g.lower() == group


def _resolve(services, repos):
    rows = []
    for svc in services:
        repo = svc["repo"]
        entry = repos.get(repo)
        if entry is None:
            status = "MISSING_FROM_PROJECT_REPOS"
            upstream = host = None
        else:
            upstream = entry.get("upstream")
            host = entry.get("host", "github")
            status = "ok"
        rows.append(
            {
                "repo": repo,
                "stack": svc["stack"],
                "group": svc["group"],
                "role": svc.get("role", ""),
                "upstream": upstream,
                "host": host,
                "status": status,
            }
        )
    return rows


def cmd_list(args):
    reg = _load_json(REGISTRY_PATH)
    repos_path = _find_project_repos()
    repos = _load_json(repos_path) if repos_path else {}
    keep = _group_filter(args.group)
    services = [s for s in reg["services"] if keep(s["group"])]
    rows = _resolve(services, repos)

    if args.json:
        print(json.dumps({"targets": rows, "project_repos": repos_path}, indent=2))
        return

    print(f"# Scan targets (group={args.group or 'all'})")
    print(f"# project-repos.json: {repos_path or 'NOT FOUND'}")
    print(f"{'REPO':<32} {'STACK':<7} {'GROUP':<11} {'HOST':<7} STATUS")
    for r in rows:
        print(f"{r['repo']:<32} {r['stack']:<7} {r['group']:<11} {(r['host'] or '-'):<7} {r['status']}")
    missing = [r["repo"] for r in rows if r["status"] != "ok"]
    if missing:
        print(f"\n# WARNING: {len(missing)} target(s) missing from project-repos.json: {', '.join(missing)}")


def cmd_resolve(args):
    reg = _load_json(REGISTRY_PATH)
    repos_path = _find_project_repos()
    repos = _load_json(repos_path) if repos_path else {}
    match = next((s for s in reg["services"] if s["repo"] == args.repo), None)
    if match is None:
        print(json.dumps({"error": f"{args.repo} not in registry"}))
        sys.exit(1)
    row = _resolve([match], repos)[0]
    print(json.dumps(row, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list", help="List scan targets by group")
    pl.add_argument("--group", default="all",
                    help="all (default) | platform | tenant")
    pl.add_argument("--json", action="store_true", help="Emit JSON")
    pl.set_defaults(func=cmd_list)

    pr = sub.add_parser("resolve", help="Resolve one repo to its target row")
    pr.add_argument("repo")
    pr.add_argument("--json", action="store_true")
    pr.set_defaults(func=cmd_resolve)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
