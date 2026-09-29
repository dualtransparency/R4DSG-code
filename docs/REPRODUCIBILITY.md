# Reproducibility scope

This is a runnable reference implementation of the cached-observation memory
pipeline, not the exact code/configuration used for the submitted experiments.
No paper accuracy, retrieval-grounding, latency, or dataset-coverage claim is
established by running the synthetic software tests.

## Implemented and tested

| Component | Release behavior |
| --- | --- |
| Observation source | Strict visual-only frame schema; optional node/edge adapter |
| Episode/window units | Fixed-duration bins within explicitly named recording streams |
| Identity association | One-to-one same-label geometry matching; optional independent visual instance keys; ties split |
| Geometry compatibility | Same coordinate frame and location required for geometric association |
| Static anchors | Recurring candidate labels with low motion, or recurring explicit anchor candidates with visual instance keys |
| Dominant anchor | Unambiguous observed support relation, otherwise unambiguous nearest simultaneous anchor |
| Event writing | Confirmed change after at least two consecutive supporting observations; uncertain/long-gap associations split |
| Memory writer h(.) | Maps observations, associated tracks and confirmed events to window-level retrievable documents |
| Retrieval | BM25 over generated document text; only the question string enters scoring; default top-k 8 |
| MCQ answering | Options added after retrieval; explicit endpoint/model, temperature zero, strict A-D output |
| Evaluation | Separate label file; exact prediction/label ID agreement; missing subsets produce null, not zero |
| No-Transition Obj.-Rel. Memory | Same observation windows and local relations; no persistent IDs or transition events in memory |

## Default parameters

| Parameter | Default | Unit / meaning |
| --- | --- | --- |
| window_seconds | 60 | Recording seconds |
| max_track_gap | 30 | Maximum unobserved association gap, seconds |
| match_distance | 1.5 | Euclidean distance in the input geometry's unit |
| size_tolerance | 0.5 | Mean normalized dimension difference |
| ambiguity_margin | 0.05 | Minimum winning association or anchor score separation |
| static_motion | 0.1 | Maximum adjacent candidate-anchor displacement |
| anchor_distance | 2.0 | Maximum geometric fallback anchor distance |
| stable_observations | 2 | Consecutive supporting observations before confirmation |

These are release defaults, not recovered experimental settings. They assume a
consistent geometry scale; tune with an independent development split, never with
evaluation answers. An explicit visual instance key bypasses geometric matching,
but still requires label compatibility, the same stream, and a bounded time gap.
BM25 uses k1=1.2, b=0.75; ties use document ID. Documents with zero lexical score
are not returned, so fewer than eight entries are possible. No semantic matching
or embedding model is hidden behind this interface.

## Not established by this release

- Full video-to-memory reproduction with SAM3/SAM3D or an episode captioner.
- Exact semantic-episode segmentation, prompts, sampling, and archival settings.
- Reproduction of paper or rebuttal metrics with the refactored scorer and windows.
- Robust long-term re-identification across missing observations or camera-frame
  changes when no independent identity signal is available.
- Online/streaming performance, calibrated anchor probabilities, or full evidence
  grounding accuracy. A temporal overlap or lexical match is not grounding proof.
- Official AMEGO or EMQA reproduction; such baselines are not distributed here.

## Running a benchmark responsibly

Obtain dataset access separately and retain the original annotation provenance.
Construct observation inputs independently of evaluation questions, answer options,
and labels. Specify the sampling, episode generation, visual prompts, model and
weight revisions, geometric units/alignment, parameter file, question split IDs,
endpoint settings, and this repository's commit ID. Do not assume the refactored
pipeline selects the same benchmark subset; no dataset-specific selection rule is
embedded. Supply the published split explicitly, without redistributing restricted
QA or private media in a pull request.

Report newly measured metrics as new runs. Do not copy the paper's scores into a
run report or state that excluding certain fields proves absence of contamination.
The code interface cannot verify how an external cache was originally produced.

Optional intent/causal-context fields are not part of this release. Their absence
is a scope choice, not an evaluation of the separate exploratory WhyMemory branch.
