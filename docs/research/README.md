# Research evidence

`docs/research/` stores durable research evidence. Chat history, agent reasoning, and temporary implementation notes are not repository state.

## Directory contract

- `catalogs/` — paper registries, selection manifests, schemas, and version pins used to define research scope.
- `contracts/` — frozen experiment, data, split, and decision contracts fixed before evaluation.
- `data/` — small versioned research inputs and source snapshots.
- `data_access/` — data-access documentation and acquisition boundaries.
- `frontier/` — canonical machine-readable paper/factor frontier registries used to generate public comparison views.
- `protocols/` — preregistered research protocols and evaluation procedures.
- `results/` — canonical summaries and validated result artifacts.
- `runs/` — immutable run-level evidence bundles.
- `studies/` — standalone company, macro, and hypothesis studies.
- `assets/` — figures and supporting assets.

The root of `docs/research/` contains only this `README.md`. New evidence must be placed by responsibility rather than dropped into the root.

## State discipline

A path should reveal an artifact's role without opening it. Machine-readable artifacts are authoritative where a workflow declares them canonical. Markdown summaries and public views point to those artifacts rather than becoming independent state stores.

Durable continuation belongs in the existing Issue/PR and versioned evidence artifacts. Do not depend on chat memory to reconstruct research state.
