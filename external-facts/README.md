# External Facts

This optional directory stores versioned observations about official external sources that affect
experiments or releases. A fact is inert until an experiment specification or `RELEASE.yaml`
references its stable ID. `VERIFIED` facts require a timezone-aware `checked_at`, a later
`valid_until`, an official HTTPS source, and a verification method. Freshness is computed at use
time; expired observations become `STALE` without rewriting history.
