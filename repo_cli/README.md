# Repository CLI

`repoctl` is the repository-development interface. It is intentionally separate from `src/<project>/`, which remains reserved for the project's core implementation, and from `.agents/`, which stores Agent context rather than executable project behavior.

The initial command surface is deliberately small:

```text
repoctl describe --json
repoctl check
```

Project and research workloads remain on the project CLI declared in `PROJECT.yaml`. Template lifecycle commands remain a compatibility surface until they move to the external template CLI.
