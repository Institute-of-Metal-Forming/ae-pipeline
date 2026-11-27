---
name: review-changes
description: Review a change in ae-pipeline with the reviewer agent, against specs, ADRs and conventions. Defaults to the current Jujutsu working-copy change.
argument-hint: '[revision or revset] [spec/ADR path or task description]'
disable-model-invocation: true
---

# Review a change with the reviewer agent

Arguments: $ARGUMENTS

You orchestrate. Do not review the code yourself; delegate to the `reviewer` agent. It starts without your context, so its prompt must be self-contained.

## 1. Determine the scope

1. **Revision:** if the arguments contain a jj revision or revset (e.g. `@-`, `xuksstkn`, `main..@`), use it. Otherwise use the working-copy change `@`; if `@` is empty (`jj diff --stat -r @` shows nothing), use `@-`. In a plain git checkout without `.jj/`, use the uncommitted changes (`git diff HEAD`).
2. **Overview:** run `jj diff --stat -r <rev>` and `jj log -r <rev> --no-graph` to get the changed files and descriptions. If nothing changed, tell the user and stop.
3. **Reference documents:** if the arguments name a spec, ADR or task, use it. Otherwise look for references in the change descriptions and in the changed files, e.g. a spec number or a `docs/specs/` path. If none is found, review against conventions and ADRs only, and say so in the report.

## 2. Run the reviewer

Start one fresh `reviewer` agent in the foreground. Its prompt contains:

- the revision and the command to see the diff (`jj diff --git -r <rev>`)
- the list of changed files
- the spec/ADR/task paths to check against, or the note that none exist
- if the change touches `docs/` or `.claude/`: also check that it is consistent with the code, with `docs/architecture.md`, existing ADRs and `docs/conventions.md`, and that `.claude/CLAUDE.md` and the agent definitions don't contradict each other
- the instruction to report findings in its standard format with severity, `path:line`, failure scenario and suggested fix, plus check results and a verdict

## 3. Verify and report

1. Spot-check every `blocker` and `major` finding by reading the cited code. Drop findings that turn out to be wrong, and say which ones you dropped and why.
2. Report to the user:
   - the scope that was reviewed (revision, files, reference documents)
   - the verdict
   - the findings, most severe first, each with severity, `path:line`, problem and suggested fix
   - the results of ruff, ty, `pytask collect` and pytest (if run)
3. Do not edit any files. Offer to apply the fixes, or to hand blocker/major findings to the `coder` agent.
