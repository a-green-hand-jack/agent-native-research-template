# Downstream Agent Home Projection

The source template's root `AGENTS.md` and `.agents/` belong to development of the template itself. They are never copied into an initialized project.

Initialization removes the source Agent context and creates a fresh downstream-owned Agent home from `template/downstream/`:

```text
AGENTS.md
.agents/
├── system/manifest.yaml
├── knowledge/
├── skills/
├── memory/
└── runtime/
```

The projected home follows four rules:

1. The functional project is primary and works without `.agents/`.
2. Repeatable mechanics are exposed through the project's canonical CLI.
3. `.agents/` stores project-specific identity, knowledge, skills, memory, and ignored runtime coordination; it does not implement project behavior.
4. Generic Agent procedures and template-maintainer governance remain with their owning runtime or upstream package.

After initialization every projected Agent path is downstream-owned. Template updates must not overwrite downstream knowledge, memory, or project-specific skills.
