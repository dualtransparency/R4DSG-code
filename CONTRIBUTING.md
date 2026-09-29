# Contributing

Use an isolated Python environment and install the development extra described in
the README. Before submitting a change, run pytest, Ruff lint/format checks, and a
wheel/source build. Include a small synthetic regression test for behavioral
changes and document any altered thresholds, input semantics, or evaluation scope.

Keep observation construction, question retrieval, answer generation, and evaluation
separate. Do not add evaluation-label-dependent features to memory or retrieval.
Do not describe adapted baselines as official reproductions or claim paper-score
reproduction without a documented, independently rerunnable experiment.

Never attach real participant videos, QA, access keys, deployment configuration,
private logs, or unlicensed model assets. Reduce bugs to synthetic data. Tests must
not contact a paid model endpoint or download large vision models.

Contributions are made under the repository's MIT license. Contributors must have
the right to submit their changes and retain third-party notices where applicable.
