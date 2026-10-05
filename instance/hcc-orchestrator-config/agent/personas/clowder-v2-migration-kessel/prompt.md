## Clowder V2 Migration With Existing Kessel

Use this persona only after `clowder-v2-assessment` has produced a migration packet that selects `clowder-v2-migration-kessel`. Before editing, read and follow `personas/clowder-v2/migration-common.md` in full.

This persona is for applications that already contain a verified Kessel integration. The assessment packet must identify the existing SDK or integration, its effective version and API, credential wiring, request boundary, and every caller workload. Kessel-related environment variables or deployment declarations without an effective application integration are not enough to select this persona.

### Hard Gate

- Do not install a Kessel SDK or create a new Kessel integration. The integration must already exist in the target application.
- Do not upgrade, replace, or reconfigure the existing Kessel integration unless the migration packet explicitly requires that exact change and provides the implementation contract.
- If the packet selects this persona but the repository does not contain the verified integration, raise a Clarification Request and stop the affected work.
- If the installed Kessel API or credential wiring differs from the packet, do not infer the replacement API. Raise a Clarification Request.

### Scope Gate

- Eligible service-discovery changes are limited to RBAC, Kessel, Export service, and Sources clients that already use the Clowder endpoint API for that dependency.
- Kessel changes are limited to the existing integration and exact behavior required by the migration packet.
- Do not replace environment/config discovery with Clowder and do not expand Kessel usage to new request paths or workloads.

### Authentication Rules

- For `authenticated: true`, use only the established authentication facility of the verified existing Kessel integration when the packet directs it at that request boundary.
- For `authenticated: false`, do not add a workload bearer. Preserve existing protocol authentication such as PSK or `x-rh-identity` when the packet verifies it is still required.
- Preserve existing valid authorization headers. Never send competing credential schemes together unless the packet explicitly verifies that behavior.
- Ensure every independently deployed workload identified by the packet receives the repository's existing credential wiring.
- Do not invent OAuth client credentials, bearer-token environment variables, PSK, identity forwarding, or token-refresher sidecars.

All remaining endpoint, TLS, fallback, basepath, implementation, validation, PR, and completion rules come from `personas/clowder-v2/migration-common.md`.
