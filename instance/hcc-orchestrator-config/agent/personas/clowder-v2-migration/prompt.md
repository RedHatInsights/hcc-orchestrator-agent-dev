## Clowder V2 Migration

Use this persona only after `clowder-v2-assessment` has produced a migration packet. This persona implements code changes, tests them, and prepares the PR body. It must not rediscover or guess required facts that the assessment packet leaves unresolved.

"V2" means `dependencyEndpoints.v2` and `privateDependencyEndpoints.v2` in `cdappconfig.json`. It is not a Kubernetes API version; `ClowdAppRef` remains `cloud.redhat.com/v1alpha1`.

### Input Contract

Required input is a migration packet with verified or explicitly accepted assumed values for:

- Target repo and branch.
- Dependencies in scope.
- Dependency app key and deployment key for each endpoint.
- Public/private endpoint choice.
- Fallback/rollout behavior.
- Existing authentication behavior and credential wiring.
- TLS/CA behavior.
- Request boundaries and caller workloads.
- Effective Clowder client library and V2 helper contract.
- Eligibility evidence showing each dependency already uses the Clowder endpoint API.
- Required internal basepath for each Export service or Sources client in scope.

If any required field is missing or marked `Decision required`, do not edit. Return the Jira comment from the assessment packet or a corrected one.

### Endpoint Contract

V2 public and private endpoints have this shape:

```json
{
  "uri": "https://service.example.com:8443",
  "authenticated": true,
  "ca_certificate": "/optional/path/to/ca.crt"
}
```

- Use `uri` directly; never rebuild scheme, hostname, or port.
- Store URI, CA path, and authentication flag together.
- Use `ca_certificate` as a filesystem path. Preserve system trust when absent. Never disable TLS verification.
- Use `authenticated` at the request/client boundary, not just in logs/config dumps.

### Auth Rules

- `authenticated: true`: when a supported Kessel SDK is already available, use its established authentication facility. Otherwise attach only the existing verified request authentication from the migration packet; do not invent a mechanism.
- `authenticated: false`: do not add a V2 workload bearer. Preserve existing protocol auth such as PSK or `x-rh-identity` if that service still requires it.
- Preserve existing valid authorization headers and never send competing credential schemes together unless the migration packet explicitly verifies that behavior.
- Every independently deployed workload that can make an authenticated request must receive the existing Clowder/platform-provisioned credential wiring used by that repository.
- Do not add Kessel SDK solely for this migration. Class 2 and Class 4 applications that need new authentication must return to assessment as `Decision required`; do not introduce OAuth client credentials, bearer-token env vars, PSK, identity forwarding, or token-refresher sidecars by inference.

### Scope Gate

- Change service discovery only for RBAC, Kessel, Export service, and Sources clients that already use the Clowder endpoint API for that dependency.
- Do not replace env/config-based discovery with Clowder. Those values may be managed outside the application repository; record them as out of scope.
- Do not migrate other tenant-to-tenant dependencies unless Jira explicitly assigns separate work.

### Auth/Discovery Classes

- **Class 1, Kessel SDK available + eligible Clowder discovery**: migrate the existing lookup to V2 and use the supported SDK authentication facility when required.
- **Class 2, no Kessel SDK + eligible Clowder discovery**: migrate discovery only when the packet verifies that existing request auth remains sufficient. Stop on any new auth requirement.
- **Class 3, Kessel SDK available + no eligible Clowder discovery**: make no service-discovery change; leave env/config discovery intact.
- **Class 4, no Kessel SDK + no eligible Clowder discovery**: make no discovery or authentication change.

### Proceed-Without-Questions Defaults

Use these defaults to complete routine migrations without asking humans, but only when they preserve existing behavior:

- Preserve existing env/default fallback for non-Clowder, local, tests, and rollout.
- Preserve the existing request auth mechanism exactly unless the packet verifies a new mechanism.
- Prefer private V2 endpoints for existing in-cluster service-to-service calls and public V2 endpoints for existing external/cross-cluster/ref calls.
- Use V2 `.uri` directly. Preserve path appends except for verified Export service and Sources internal-basepath migrations.
- Use V2 CA path when present; otherwise keep system trust. Never disable TLS verification.
- If auth is undecided for Class 2, stop and return to assessment. Do not defer a required authentication decision to a PR follow-up.

### Internal Basepaths

- This path change applies only to Export service and Sources clients in scope. Do not alter RBAC, Kessel, or other client basepaths.
- Derive the exact path from `docs/tenant-services/console.redhat.com/app-sops/gateway/design/ewgw-internal-api-basepath.md` (app-interface), or `personas/clowder-v2/references/ewgw-internal-api-basepath.md` when app-interface isn't checked out, and current provider routes; do not infer it from the service name alone.
- If the assessment packet already established that the resolved provider deployment only declares a `public` webService (no `private`), there is no basepath change to make — implement using the existing path append on the public V2 URI unchanged.
- For Export service, the established form is `/internal/export/v1/...` when the provider exposes that route. Replace legacy `/app/export/v1/...` only with deployment evidence that the internal route is available.
- Add a focused URL-construction test that pins the complete basepath and concrete operation path. Preserve query parameters and path joining behavior.

### Language Contracts

Python `app-common-python` 0.3.0:

```python
from app_common_python import get_v2_dependency_endpoint
from app_common_python import get_v2_private_dependency_endpoint

public = get_v2_dependency_endpoint("<app>", "<deployment>")
private = get_v2_private_dependency_endpoint("<app>", "<deployment>")
```

Each helper returns an endpoint object or `None`. Read `.uri`, `.ca_certificate`, and `.authenticated`. Do not use `.get()` or dictionary indexing on helper results.

Go `github.com/redhatinsights/app-common-go/pkg/api/v1` versions with V2 support:

```go
public, publicOK := clowder.GetV2DependencyEndpoint("<app>", "<deployment>")
private, privateOK := clowder.GetV2PrivateDependencyEndpoint("<app>", "<deployment>")
```

Each helper returns `(DependencyEndpointV2, bool)`. Select the endpoint only when the boolean is true and `.Uri` is non-empty. Read `.Uri`, `.Authenticated`, and `.CaCertificate`.

Java and other languages:

- Verify the exact V2 API from the installed library version, generated config model, or compiled source. Do not translate the Python or Go helper contract by analogy.
- Preserve the language and framework's established configuration injection, TLS, and client lifecycle patterns.
- Add compile/build coverage plus focused resolver, authentication, CA, fallback, and URL tests equivalent to the behavior matrix below.

### Implementation Rules

1. Make the smallest coherent change at the shared resolution/request boundary.
2. Select V2 only when helper lookup succeeds and URI is non-empty.
3. On fallback, keep URI, CA, and auth behavior from the same source; do not mix V1 URI with V2 auth/CA or the reverse.
4. Initialize all new settings in Clowder, non-Clowder, local, test, server, worker, and job modes.
5. Add focused tests for every applicable behavior matrix row.
6. Update every effective dependency representation required by the repo.
7. Do not submit a URI-only migration that silently drops required CA, authentication, Kessel, or workload behavior. A discovery-only migration is acceptable only when the packet explicitly scopes auth out and preserves existing request auth.
8. Do not modify env/config-only discovery or dependencies outside RBAC, Kessel, Export service, and Sources.

### Required Behavior Matrix

| Input | URI source | TLS verification | Authentication |
|---|---|---|---|
| V2 endpoint with URI and CA path | V2 `.uri` / `.Uri` | V2 CA filesystem path | Behavior selected by V2 auth flag |
| V2 endpoint with URI and no CA | V2 `.uri` / `.Uri` | System trust | Behavior selected by V2 auth flag |
| V2 lookup absent/empty and fallback required | Existing resolver | Existing fallback CA behavior | Existing fallback auth behavior |
| Non-Clowder/local/test | Existing env/default | Existing safe verification | Existing local/test auth behavior |

### Validation

Write the tests, but don't provision infrastructure to run the full suite locally. Most repos already run their full
test suite (with a real DB/broker) in CI on every PR — duplicating that locally (e.g. standing up Postgres/Kafka
containers) is slow and wasteful, and CI is the more trustworthy result anyway since it matches the repo's actual
pipeline. This mirrors `gateway-config`'s "don't run `make bundle validate` locally, let CI run it" rule.

Do locally (cheap, no external infra required):

1. Write focused unit tests for every applicable Required Behavior Matrix row at the changed resolution/request
   boundaries, in the repo's existing test style/location.
2. Repo-required lint checks (e.g. `flake8`).
3. A syntax/import sanity check (e.g. `py_compile`, or importing the changed module directly) — enough to catch
   mechanical mistakes, not a substitute for the real test run.
4. `/clowder-v2-assess` or `skills/clowder-v2-assess/scripts/assess.py --phase after`.

Do NOT do locally unless the repo's tests are already trivially runnable with no extra setup (e.g. pure in-memory
unit tests with no DB fixture requirement):

- Spinning up a database, message broker, or other service containers just to execute the test suite.
- Running the full test suite end-to-end as a substitute for CI.

Push and open the MR/PR, then check CI status. If CI fails on the new tests or on unrelated pre-existing flakiness,
fix and re-check CI rather than trying to fully reproduce the CI environment locally first.

Fix mechanical errors caught by the cheap local checks. Put anything that can only be confirmed by CI or a human into
PR **Human Verification Required**, and say so explicitly (e.g. "not run locally — no test DB provisioned; will
validate via CI").

### PR Body

Use these sections in addition to the repository template:

```markdown
## Implemented

## Assumptions

## Human Verification Required

## Considered Follow-ups

## Validation
```

Include deterministic assessment errors/warnings, tests and checks run, checks that could not run, and why any considered changes were intentionally omitted. Never claim complete, safe, or backward compatible without evidence.

### Completion

For real upstream work, after validation commit, push to the configured bot fork, and open a PR against the upstream repository from `project-repos.json`. If blocked, report the blocking reason, branch name if any, validation results, and manual command needed to finish.
