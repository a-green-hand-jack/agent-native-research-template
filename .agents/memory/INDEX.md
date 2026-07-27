# Project Memory Index

This directory contains accepted, durable project facts. Template-owned runtime notes, session
journals, task-agent handoffs, and unverified candidates belong under `.agents/runtime/`.
Tool-owned workflow state remains in its own ignored path, such as `.omx/`.

## Topics

No durable topics have been promoted yet.

## Promotion Rule

Promote a candidate only when it is project-specific, likely to matter across sessions, supported
by code or evidence, and not already represented by a contract, test, evaluation, guide, or
existing memory topic.

Each topic should state its scope, source, confidence, review status, and what it supersedes.
