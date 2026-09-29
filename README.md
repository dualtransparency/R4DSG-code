# R4DSG

**Relative 4D Scene Graph Memory for Object-Centric Question Answering in Long Egocentric Video**

[Paper](https://arxiv.org/abs/2608.11017) | [Project page](https://dualtransparency.github.io/R4DSG/) | [Input schema](docs/SCHEMA.md) | [Usage](docs/USAGE.md) | [CI](https://github.com/dualtransparency/R4DSG-code/actions/workflows/ci.yml)

R4DSG represents object observations as local 3D relations indexed over time,
associates persistent objects, and writes stable changes between supporting anchors
into retrievable memory. Here, **4D means local 3D information plus time**, not a
globally registered dynamic reconstruction.

## Release scope

This repository is a cleaned, independently tested **cached-observation reference
implementation**. It provides object association, anchor inference, temporal event
writing, memory serialization, question-only retrieval, an optional Qwen-compatible
MCQ client, and a separate evaluator.

It is **not an archival snapshot of the experimental code**. The release uses
documented conservative association rules, fixed-duration observation windows, and
BM25 retrieval. Exact reproduction of the paper's reported scores has not been
validated with this implementation. See [reproducibility scope](docs/REPRODUCIBILITY.md)
before comparing results.

SAM3/SAM3D inference, model weights, dataset videos, benchmark QA, and experiment
caches are not bundled. Use independently obtained, appropriately licensed visual
observations. The offline demo requires no GPU, model download, API key, or network.

## Quick start

Requires Python 3.10 or newer:

```bash
git clone https://github.com/dualtransparency/R4DSG-code.git
cd R4DSG-code
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
r4dsg build --frames examples/frames.json --config examples/config.json --output outputs/memory.json
r4dsg retrieve --memory outputs/memory.json --questions examples/questions.json --top-k 8 --output outputs/retrieval.json
```

The synthetic fixture has four observations, three persistent tracks, two memory
documents, and one confirmed shelf-to-table transition. These are software-test
fixtures, not EgoLife annotations or research results. Inspect the generated JSON
to see the event interval, confirmation time, document text, and ranked retrieval.

## Pipeline

```text
cached visual observations -> persistent tracks -> stable anchor transitions
                           -> local relation summaries + windowed memory
question text              -> BM25 top-k retrieval
retrieved memory + question + MCQ options -> answer model -> predictions
predictions + separately held labels      -> evaluation
```

Memory building has no QA-file input. Retrieval accepts only the question string;
options enter only the final MCQ prompt. Optional causal/intent fields are not part
of the observation or memory schema. Schemas enforce field boundaries, not the
provenance of external text: upstream observations must themselves be generated
independently of evaluation questions and labels.

## Your cached graphs

The preferred input is the strict observation schema in [SCHEMA.md](docs/SCHEMA.md).
A node/edge-cache adapter is also available:

```bash
r4dsg import-graphs --graphs data/frame_graphs.json --manifest data/frame_times.json --output outputs/frames.json
r4dsg build --frames outputs/frames.json --output outputs/memory.json
```

The manifest must supply actual recording times and stream/day identities. The
adapter does not guess timestamps from filenames, infer a shared coordinate frame,
or carry arbitrary graph metadata into memory. Unaligned frame-local positions
cannot establish persistent identity. Supply a validated local coordinate system
or independent visual instance keys in the canonical schema when available.

## No-Transition Obj.-Rel. Memory

```bash
r4dsg build --frames examples/frames.json --config examples/config.json --no-transitions --output outputs/no_transition.json
```

**No-Transition Object-Relation Memory** keeps the same local object observations,
states, 3D metadata, and relation summaries, but omits persistent identities and
anchor-transition events from the memory. The visual front-end is shared; no visual
model is rerun. This is a release-level diagnostic, not a new benchmark result.

## Optional model answering

Use an OpenAI-compatible chat-completions endpoint serving your selected model.
The paper's answer model is Qwen3.5-27B; this repository does not start a model server.
The endpoint must return one uppercase option letter. See [USAGE.md](docs/USAGE.md)
for input formats, endpoint configuration, checkpoints, and evaluation.

```bash
r4dsg answer --memory outputs/memory.json --questions data/questions.json --base-url http://127.0.0.1:8000/v1 --model Qwen/Qwen3.5-27B --send-to-model --output outputs/predictions.json
r4dsg evaluate --predictions outputs/predictions.json --labels data/labels.json --output outputs/metrics.json
```

For authenticated endpoints set `R4DSG_API_KEY` in your environment, never in a
tracked file. The `answer` command sends questions, options, and retrieved memory
to the endpoint. Review dataset terms and privacy requirements before using a
remote service. Only `answer` performs network requests.

## Development

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
ruff check .
ruff format --check .
python -m build
```

Tests cover stable and ambiguous transitions, duplicate objects, stream isolation,
missing geometry, strict schema validation, retrieval field isolation, MCQ protocol,
HTTP error handling, and exact-ID evaluation. Local mock-server tests do not measure
Qwen answer quality. CI runs the CPU tests and offline demo on Python 3.10 and 3.12.
See [local validation results](docs/VALIDATION.md) for the checked release scope.

## Citation and license

```bibtex
@inproceedings{ma2026r4dsg,
  title = {R4DSG: Relative 4D Scene Graph Memory for Object-Centric Question Answering in Long Egocentric Video},
  author = {Ma, Ke and Mao, Yamin and Li, Weiming and Tan, Shuai and Zhong, Yijie and Chen, Hao and Wang, Haofen and Wang, Meng},
  booktitle = {Proceedings of the 34th ACM International Conference on Multimedia},
  year = {2026},
  doi = {10.1145/3767308.3835995}
}
```

Code is MIT-licensed. Dataset, model, and third-party asset rights are separate;
this license does not grant redistribution rights to them. See [LICENSE](LICENSE),
[CITATION.cff](CITATION.cff), [CONTRIBUTING.md](CONTRIBUTING.md), and [SECURITY.md](SECURITY.md).
