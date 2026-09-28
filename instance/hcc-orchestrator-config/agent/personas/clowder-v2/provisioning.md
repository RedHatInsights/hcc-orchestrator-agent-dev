## ClowdAppRef Provisioning And Cutover

Read this appendix only for tickets that create, modify, cut over, or remove a `ClowdAppRef`.

### Resource Contract

```yaml
apiVersion: cloud.redhat.com/v1alpha1
kind: ClowdAppRef
metadata:
  name: <dependency-app>
  namespace: <namespace>
spec:
  envName: <local-clowd-environment>
  remoteEnvironment:
    port: <remote-public-port>
    privatePort: <remote-private-port>
    tls:
      port: <remote-public-tls-port>
      privatePort: <remote-private-tls-port>
  deployments:
    - name: <deployment>
      hostname: <hostname-without-scheme-or-port>
      webServices:
        public:
          enabled: true
          tls: true
  serves:
    - <consumer-clowdapp-name>
```

Obtain names, environment, hostname, ports, TLS, and authentication requirements from authoritative deployment configuration.

### Rules

- `metadata.name` must equal the dependency string declared by consumers. It becomes the first V2 map key.
- `deployments[].name` becomes the second V2 map key.
- `deployments[].hostname` is a hostname or IP only, not a URL or `host:port`.
- Enable the public and/or private `webServices` entry actually consumed. Do not use deprecated `web: true`.
- `serves` contains consumer `ClowdApp.metadata.name` values, not namespaces, deployment names, or dependency names.
- Avoid duplicate ref names for one environment, including duplicates across namespaces.
- For TLS, set `webServices.<service>.tls: true` and configure both `remoteEnvironment.tls.port` and `.privatePort`. Current Clowder requires both before treating TLS as configured, even for public-only use.
- CRD validation does not enforce service/TLS/port relationships. A valid resource can still emit HTTP or no endpoint.
- H2C-only refs currently do not produce V2 endpoints.
- Do not rely on `status.ready` or `spec.disabled` as cutover gates without verifying deployed Clowder behavior.

### Gradual Cutover

When a local `ClowdApp` and remote `ClowdAppRef` share a dependency name:

1. Create the ref with `serves` omitted or empty; consumers remain local.
2. Add one consumer app name to `serves`.
3. Inspect that consumer's generated `cdappconfig.json`.
4. Verify the V2 URI, TLS, authentication, and live connectivity.
5. If V1 fallback remains, verify its flat endpoint also switched coherently.
6. Continue consumer by consumer.

If only the ref exists, Clowder selects it regardless of `serves`. `serves` is not authorization.

### Verification

```bash
kubectl apply --server-side --dry-run=server -f <manifest>
kubectl get clowdappref <name> -n <namespace> -o yaml
kubectl get secret <consumer> -n <namespace> \
  -o jsonpath='{.data.cdappconfig\.json}' \
  | base64 -d \
  | jq '.dependencyEndpoints.v2["<dependency-app>"]["<deployment>"]'
```

Confirm remote certificates are system-trusted. `ClowdAppRef` provides no custom CA path. After deleting a ref, explicitly trigger or wait for consumer reconciliation and recheck generated configuration because deletion may not immediately enqueue affected consumers.
