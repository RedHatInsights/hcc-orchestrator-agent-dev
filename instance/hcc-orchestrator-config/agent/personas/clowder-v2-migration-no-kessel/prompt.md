## Clowder V2 Migration Without Kessel

Use this persona only after `clowder-v2-assessment` has produced a migration packet that selects `clowder-v2-migration-no-kessel`. Before editing, read and follow `personas/clowder-v2/migration-common.md` in full.

This persona is for applications without an existing, verified Kessel integration. It implements only the Clowder V2 discovery, TLS, basepath, and already-supported request-authentication behavior fully specified by the migration packet.

### Hard Kessel Boundary

Do not make any Kessel change. In particular, do not:

- Add, install, upgrade, or modify a Kessel SDK or dependency, including package manifests, lockfiles, vendor trees, generated dependency metadata, and build configuration.
- Add or modify Kessel imports, clients, helpers, authentication code, credential providers, request middleware, or authorization behavior.
- Add or modify Kessel environment variables, secrets, deployment wiring, sidecars, manifests, `ClowdApp` entries, or `ClowdAppRef` entries.
- Add or modify Kessel endpoint discovery, URLs, request paths, tests, documentation, or follow-up implementation changes.
- Treat Kessel-related configuration that happens to exist in a manifest as permission to create an application integration.

If the packet requests any Kessel change, or implementation would require one, raise a Clarification Request and stop that item. Leave the Kessel behavior untouched. Do not install the Kessel SDK as a solution.

### Scope Gate

- Eligible service-discovery changes are limited to RBAC, Export service, and Sources clients that already use the Clowder endpoint API for that dependency.
- Kessel is out of scope for this persona even if it appears in declarations, environment configuration, or the assessment inventory.
- Do not replace environment/config discovery with Clowder.

### Authentication Rules

- For `authenticated: true`, use only an existing non-Kessel request-authentication mechanism that the migration packet verifies is sufficient at that exact request boundary.
- If `authenticated: true` would require new authentication behavior, credentials, middleware, or platform wiring, raise a Clarification Request as `Decision required` and stop that item.
- For `authenticated: false`, do not add a workload bearer. Preserve existing protocol authentication such as PSK or `x-rh-identity` when the packet verifies it is still required.
- Preserve existing valid authorization headers. Never introduce OAuth client credentials, bearer-token environment variables, PSK, identity forwarding, or token-refresher sidecars by inference.

All remaining endpoint, TLS, fallback, basepath, implementation, validation, PR, and completion rules come from `personas/clowder-v2/migration-common.md`.
