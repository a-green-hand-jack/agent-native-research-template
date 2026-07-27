# Infrastructure

Keep committed infrastructure descriptions logical and non-secret.

- `profiles/` describes executor and resource capabilities.
- Experiment specs reference profile IDs rather than private host paths.
- Put local values in ignored environment files or a secret manager.
- Do not commit SSH aliases, credentials, tokens, private hostnames, or personal absolute paths.

Add a new executor or storage mapping only when a real second execution target appears.

