# Release validation

The following checks were run locally for version 0.1.0. These are software
validation results, not benchmark results or proof of absence of all risks.

| Check | Result |
| --- | --- |
| Python 3.12.4, editable install | 53 tests passed |
| Python 3.10.12, installed wheel, tests from source archive | 53 tests passed |
| Offline CLI build and retrieval | Passed on both environments |
| Synthetic memory | 4 frames, 3 tracks, 2 documents, 1 confirmed transition |
| Local mock HTTP answer client and CLI | Passed; invalid responses leave an incomplete checkpoint |
| Annotation-field isolation | Question-only retrieval invariant to changed options, labels and auxiliary metadata |
| Ruff lint and formatting | Passed |
| Wheel and source archive | Built; contents reviewed; demo fixtures and tests included in source archive |
| Source static security analysis | No findings from Bandit on runtime source |
| Credential scan | No findings from detect-secrets on the tracked release files |
| Known dependency vulnerabilities | None reported by pip-audit in the checked development environment |
| Runtime third-party dependencies | None |
| Local documentation links | All checked links resolve |

The example data are synthetic. Real dataset videos, QA, model weights, experiment
caches and private configurations are excluded. The release is reviewed as a new
repository, without importing a prior experimental repository's history.

Not run: SAM3/SAM3D inference, a live Qwen answer-quality evaluation, complete
dataset inference, paper-score reproduction, or online memory performance tests.
GitHub-hosted CI status, when available, is separate from these local checks.
Dataset/model licensing and the provenance of user-supplied observations must be
reviewed independently. See [REPRODUCIBILITY.md](REPRODUCIBILITY.md).
