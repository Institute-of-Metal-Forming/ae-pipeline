---
name: implement
description: Implement a feature or fix in ae-pipeline by running the coder, tester and reviewer agents in a loop of at most 3 iterations until the reviewer approves. Use when asked to implement a spec from docs/specs/ or a concrete task end to end.
argument-hint: <spec file or task description>
disable-model-invocation: true
---

# Implement loop: coder → tester → reviewer

Task: $ARGUMENTS

You orchestrate. Do not write code or tests yourself; delegate to the `coder`, `tester` and `reviewer` agents and pass information between them. Subagents start without your context, so every prompt must be self-contained.

## 0. Prepare

1. Resolve the task: if `$ARGUMENTS` names a spec (path or number such as `0003`), locate it in `docs/specs/`. If it is a free-text task, find any spec/ADR it relates to.
2. If the task is empty or too vague to give the coder a clear goal, ask the user before starting.
3. Find out which datasets are available (`ls ae_pipeline/data/*.pridb`) and pick one to verify on (the smallest one, unless the task names one). Pass its id (the file stem) to every agent as the `-k` key. If there is none, tell the user that pipeline verification is impossible and ask whether to continue with static checks only.
4. Create a fresh commit using `jj new` on top of the current revision to work in. If the current working copy does not use Jujutsu, note the current revision using `git rev-parse HEAD` so the reviewer can diff against it.

## 1. Loop (iteration `n` = 1..3)

Run the agents **sequentially** (each depends on the previous one), in the foreground.

**a. Coder**
- Iteration 1: start the `coder` agent with the task, the spec/ADR paths, the dataset id for verification, and the instruction to report changed files, affected tasks/products and open questions.
- Iteration ≥ 2: continue the same coder agent (SendMessage to its ID) with the blocker/major review findings and failing checks from the previous iteration, verbatim with `path:line`. Ask it to fix exactly these and nothing else.
- If the coder stops because of a spec conflict or ambiguity, **end the loop** and go to step 2.

**b. Tester**
- Iteration 1: start the `tester` agent with the spec/ADR paths, the dataset id, and the coder's summary of changed files and affected tasks/products.
- Iteration ≥ 2: continue the same tester agent with the coder's latest changes and any review findings about verification or tests. Ask it to re-run the affected tasks and add/adjust tests only where needed.

**c. Reviewer**
- Start a **fresh** `reviewer` agent every iteration (no bias from earlier rounds). Give it: the task, spec/ADR paths, the base revision from step 0, and the tester's report of results, failures and spec gaps.

**d. Decide**
- **Done** if the reviewer's verdict is "approve" or "approve with nits", the affected tasks build on the verification dataset, and `uv run pytest` passes (if `tests/` exists). Leave the loop.
- **Escalate** if the remaining problems are spec gaps or open questions that only the user can answer (e.g. choice of units, thresholds or processing parameters). Leave the loop.
- **Escalate** if the findings of this iteration repeat the previous iteration's (no progress). Leave the loop.
- Otherwise, if `n < 3`, continue with the next iteration using the blocker/major findings and failures. Pass nits only if they are trivial.
- After iteration 3, stop regardless of the outcome.

Between steps, give the user a one-line status (e.g. "Iteration 2: tester found empty waterfall plots, reviewing").

## 2. Report

Finally, verify independently (prefix with `devenv shell --` if the tools are not on `PATH`):

```sh
uvx ruff check . && uvx ruff format --check .
ty check ae_pipeline
uv run pytask build -k <dataset id>   # plus <task name> to narrow further if the full dataset build is too slow
uv run pytest                          # only if tests/ exists
```

Then report to the user:

- outcome: approved / stopped after 3 iterations / escalated (and why)
- number of iterations run
- changed files, grouped into pipeline code and tests
- new or changed products (paths under `ae_pipeline/data/` and `ae_pipeline/plots/`) the user should look at
- final check results (quote failures)
- unresolved findings from the last review, with severity and `path:line`
- open questions and spec gaps for the user, and any suggested ADRs
- generate the commit message based on the changes and the implemented feature spec, following the Commits section of `docs/conventions.md`

Do not commit. Leave the changes in the working copy for the user to inspect.
