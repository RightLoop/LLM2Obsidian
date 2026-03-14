# Real-Vault Quality Tuning Execution Plan

Date: 2026-03-14
Issue: #41

## 1. Goal

This document freezes the execution baseline for the next tuning cycle.

The objective is not to add new product surface area. The objective is to raise the quality of:

- error notes under `21 Errors/`
- concept, pitfall, and contrast nodes under `20 Smart/`
- relation proposals and relink review output under `90 Review/`

The tuning loop must be driven by real outputs from the live vault at:

`C:\Users\Yingb\Documents\Obsidian Vault`

## 2. Why This Exists

Current functionality is operational, but the generated quality is not yet strong enough for long-term use.

Observed problems from the real vault include:

- error notes are too generic and do not preserve the exact reasoning failure of a specific question
- concept nodes read like learner-state templates instead of durable knowledge notes
- relation and review proposals are formally plausible but still noisy
- naming and output shape are not yet stable enough for a clean knowledge base
- output language and style are inconsistent

This plan freezes how we will evaluate and improve the system before continuing broader feature work.

## 3. Concrete Findings From The Real Vault

The plan is based on actual generated artifacts, not synthetic assumptions.

### 3.1 Error Note Quality

Observed in:

- `21 Errors/长度获取错误.md`
- `21 Errors/字符串构造错误.md`

Problems:

- the note captures the topic area, but not the exact reasoning path that failed
- the note does not clearly separate trigger mistake, direct misconception, and corrective rule
- the note is too abstract to act as a high-value mistake journal entry

### 3.2 Concept Node Quality

Observed in:

- `20 Smart/数组名与指针的关系.md`
- `20 Smart/C字符串以' 0'结尾.md`

Problems:

- summaries are template-like
- content describes the learner rather than the concept itself
- reusable explanation quality is low
- node structure is not yet close to evergreen-note quality

### 3.3 Relation / Review Quality

Observed in:

- `90 Review/Review - 长度获取错误 - 20260314-074804.md`
- `90 Review/Review - 字符串构造错误 - 20260314-082153.md`

Problems:

- review proposals still over-link
- some links are structurally valid but low-value
- review patches are too verbose
- relation rationale is not yet compressed into strong, operator-friendly reasoning

### 3.4 Output Consistency Problems

Observed across the vault:

- mixed Chinese and English output
- unstable naming patterns
- output shape varies too much between similar runs
- concept and contrast generation thresholds are still too loose

## 4. Non-Goals

During this tuning cycle, do not prioritize:

- new product surfaces
- new major workflow routes
- frontend redesign beyond quality-supporting fixes
- plugin-side Obsidian integration work
- infrastructure replacement unless it is required for evaluation fidelity

## 5. Core Tuning Strategy

The tuning process will follow one loop only:

1. run the system on a fixed set of real C-language examples
2. inspect generated notes and review artifacts in the real vault
3. score the results against a fixed rubric
4. identify the smallest prompt / rule / post-processing change
5. replay the same examples
6. compare scores and regression failures

No prompt change should be considered successful without replay on the same sample set.

## 6. Sample Set Requirements

We will maintain a fixed regression set of at least 24 real examples.

### 6.1 Coverage Categories

The sample set must cover:

- `sizeof` vs `strlen`
- array vs pointer
- `arr` vs `&arr`
- function parameter decay
- `char *` vs `char[]`
- null terminator handling
- string allocation `len` vs `len + 1`
- pointer lifetime / invalid ownership assumptions
- struct layout / alignment confusion
- pointer arithmetic off-by-one errors

### 6.2 Per-Sample Required Fields

Each sample must record:

- title
- original prompt or question
- code
- user analysis
- expected error title
- expected root cause
- expected related concepts
- forbidden relations or node types if applicable

### 6.3 Storage

The regression set should live in a dedicated tracked fixture directory, not only in the live vault.

Recommended target:

- `tests/fixtures/quality_tuning/`

## 7. Scoring Rubric

Every replayed sample must be scored using the same rubric.

Each category is scored from `1` to `5`.

### 7.1 Error Note Accuracy

Checks:

- does the title reflect the actual mistake
- is the root cause specific enough
- is the incorrect assumption the real one
- is the correction actionable

### 7.2 Knowledge Node Reuse Value

Checks:

- does the concept node explain the concept itself
- is the pitfall note reusable across examples
- is the contrast node justified
- would a human keep this node in the vault

### 7.3 Relation Quality

Checks:

- are the suggested links relevant
- are the relation types correct
- is the top-3 set better than random nearby notes
- does each link earn its place

### 7.4 Review Quality

Checks:

- is the proposal concise
- is the rationale readable
- is the target of the review correct
- can the operator decide quickly

### 7.5 Language And Readability

Checks:

- output language is consistent
- the note reads naturally
- formatting is stable
- mixed-language artifacts are avoided unless intentional

### 7.6 Noise Control

Checks:

- no unnecessary pitfall / contrast nodes
- no redundant near-duplicate nodes
- no inflated relation lists
- no low-value boilerplate

## 8. Quality Gates

The tuning cycle is not complete until these gates are met on the fixed sample set:

- average score for `Error Note Accuracy` >= 4.0
- average score for `Knowledge Node Reuse Value` >= 3.8
- average score for `Relation Quality` >= 3.8
- average score for `Review Quality` >= 4.0
- average score for `Noise Control` >= 4.0
- no blocker regression on the previously fixed UI or bootstrap flow

## 9. Phase Breakdown

### Phase A: Regression Harness

Objective:

- create the fixed sample set
- create a scoring template
- create a replay procedure

Deliverables:

- tracked fixture dataset
- scoring sheet format
- replay script or documented replay workflow

Exit criteria:

- at least 24 samples exist
- each sample has expected outputs recorded

### Phase B: Error Note Tuning

Objective:

- make `21 Errors/` entries specific, compact, and reviewable

Focus areas:

- prompt for error extraction
- schema clarity for root cause vs incorrect assumption
- note template wording

Changes allowed:

- prompt edits
- schema field tightening
- title normalization
- lightweight post-processing rules

Exit criteria:

- error notes clearly distinguish mistake, root cause, and corrective heuristic

### Phase C: Concept / Pitfall / Contrast Node Tuning

Objective:

- make support nodes read like durable knowledge, not placeholders

Focus areas:

- concept-writing prompt
- pitfall-writing prompt
- contrast creation threshold
- support node naming strategy

Changes allowed:

- prompt edits
- novelty filter adjustments
- stricter thresholds for pitfall / contrast creation
- node template edits

Exit criteria:

- concept notes become reusable in isolation
- contrast nodes only appear when truly justified

### Phase D: Relation / Review Tuning

Objective:

- reduce relation noise and improve review usefulness

Focus areas:

- relation miner prompt
- ranking and threshold rules
- top-k limits
- review text compression

Changes allowed:

- prompt edits
- ranking heuristics
- relation confidence thresholds
- review rendering rules

Exit criteria:

- review proposals become shorter and more selective
- top relations feel obviously valuable

### Phase E: Language And Style Unification

Objective:

- unify final output style for the vault

Default policy:

- output language is Simplified Chinese
- code identifiers and technical terms may remain in English when standard

Focus areas:

- prompt language instructions
- node template style
- mixed-language cleanup rules

Exit criteria:

- generated notes no longer switch style unpredictably

### Phase F: Full Replay And Acceptance

Objective:

- rerun the full fixed sample set and compare against baseline scores

Deliverables:

- before/after score table
- representative success cases
- representative remaining failures
- next-cycle backlog

Exit criteria:

- quality gates pass
- no serious regression in UI or workflow stability

## 10. Prompt Engineering Rules

During this cycle, prompt work must follow these constraints:

- one prompt change at a time per target area
- replay the same fixed subset before and after each change
- do not change error extraction, concept writing, and relation mining prompts in one combined blind step
- record why a prompt was changed and what failure it is targeting

Recommended prompt bundles to treat independently:

- error extraction
- weakness diagnosis
- concept node writing
- pitfall node writing
- contrast generation
- relation mining
- review rationale compression

## 11. Post-Processing Rules To Add Or Tighten

Not all quality problems should be solved in prompts.

Required rule work during tuning:

- title normalization for error notes
- language normalization for final output
- top-k cap for review suggestions
- minimum confidence threshold for relation creation
- stricter novelty filter for support nodes
- forbid creating contrast nodes unless two sides are explicit and useful

## 12. Human Review Loop

Every tuning round must keep a human-in-the-loop pass.

Per round:

- pick the 5 best outputs
- pick the 5 worst outputs
- classify why each worst output failed
- decide whether the fix belongs in prompts, templates, routing, or post-processing

This classification must be written down before the next round starts.

## 13. Tracking Format

For each round, record:

- date
- branch
- prompts changed
- rules changed
- sample subset replayed
- score delta
- representative failures
- next action

Recommended output location:

- `output/quality-tuning-rounds/`

## 14. Execution Order

The actual execution order is fixed:

1. build the regression set
2. score the current baseline
3. tune error notes
4. tune concept / pitfall / contrast nodes
5. tune relation and review quality
6. unify language and style
7. rerun full acceptance

Do not skip directly to relation tuning before the error-note baseline is improved.

## 15. Immediate Next Step

The first execution step after freezing this document is:

- create the tracked regression dataset for the real C-language examples already tested in the live vault
- capture current baseline outputs and baseline scores before any prompt changes are applied
