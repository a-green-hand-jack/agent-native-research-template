# Archives

`archives/local/` is ignored generated state for compact archive manifests created by
`tools/archive.py`. Large artifact copies belong in external storage roots, not in Git.

A local archive manifest is not automatically durable evidence. Re-run archive verification and,
when needed, promote a compact reviewed decision through the project's normal evidence or report
workflow.
