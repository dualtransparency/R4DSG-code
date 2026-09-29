# Usage and troubleshooting

## Commands

Run `r4dsg --help` or `r4dsg COMMAND --help`. All outputs are explicit paths. Parent
directories are created, and JSON is replaced atomically with owner-only file
permissions. Existing output paths require explicit `--overwrite`; an output may
never replace an input file. Choose a fresh path for each run. Run identifiers and
output retention are your responsibility.

The observation schema and parameters are described in [SCHEMA.md](SCHEMA.md) and
[REPRODUCIBILITY.md](REPRODUCIBILITY.md). A JSON parameter file may specify any
subset of the documented fields. Unspecified parameters take release defaults;
unknown or invalid values cause an error. The full resolved configuration is
stored in memory output.

## Question and label files

Retrieval requires a JSON array of `id` and `question` records; numeric IDs and the
alias `ID` are accepted. A benchmark row may contain other fields, but the query
projection reads only ID and question. The answer command additionally requires
either an `options` object with exactly A/B/C/D or four `choice_a` through
`choice_d` strings. It never reads ground truth.

Minimal format illustration using software-test data, not a dataset annotation:

```json
[{"id": "toy", "question": "Where is the cup?",
  "options": {"A": "table", "B": "shelf", "C": "box", "D": "floor"}}]
```

Keep evaluation labels separately as `id`, `answer` (one uppercase A-D letter),
and optional `type` (`when`, `why`, or another value). If type is absent, only a
leading when/why question word is used to form those subsets. This is not a
dataset-specific categorizer. Preserve official question types during conversion.
Evaluation checks exact ID agreement, rejects duplicates or incomplete predictions,
and reports counts alongside unrounded percentage accuracy.

## Model endpoint

Only the `answer` command contacts a server, and it requires `--send-to-model`.
Point `--base-url` at the API prefix, for example a local `/v1` endpoint, not the
full `/chat/completions` route. HTTPS is required except for literal loopback
hosts. Redirects and credentials embedded in URLs are refused.

Configure the server for direct, non-reasoning MCQ output. The client requests
temperature 0 and a short completion; it accepts only a single uppercase letter.
Free-form explanations are not heuristically converted into predictions. Model
names, availability, permissions, cost, and output format are endpoint-dependent.
A local mock verifies the HTTP protocol in tests; an actual Qwen inference run is
not required for the offline demo and is not implied by passing tests.

For an API key, set `R4DSG_API_KEY` using your normal secret manager or an untracked
environment variable. Do not include tokens in command-line URLs, issue reports,
example configurations, or repository files. Remote prompts can contain personal
observation text; choose local inference when external transmission is disallowed.

Each successful model call checkpoints its prediction and ranked document IDs,
time spans, scores, and model name. There are no automatic retries or automatic
resume, so request count and partial-run behavior are explicit. A failure leaves
the completed prefix on disk. The evaluator refuses to score an incomplete run.
Use a fresh output filename before rerunning to avoid mistaking an old file for a
new result. API error bodies and credentials are never copied to error messages.

## Common failures

- Schema errors: confirm every required field, finite seconds, positive sizes,
  valid local references, no extra fields, and unique per-stream frame times.
- Import errors: use a complete timestamp manifest matching exactly the graph
  frame IDs. Filenames alone are not trustworthy recording-time metadata.
- No transitions: check coordinate alignment, independent visual identities,
  recurring anchors, time gaps, and stability. Empty event output is preferable
  to associating incompatible coordinate systems or ambiguous objects.
- No retrieval hits: this release uses lexical retrieval without hidden query
  expansion; use the actual question and inspect observation-derived terminology.
- Endpoint errors: check server/model availability, authentication, output format,
  and the network-consent flag. No paid API calls occur during tests.
- Evaluation errors: ensure prediction IDs exactly match labels and answers are
  already encoded as A-D. No answer text is guessed or matched to options.
- Unexpected pytest plugin failures: remove inherited `PYTHONPATH` for the test
  command if another environment (for example ROS) adds incompatible plugins.

## Privacy and licensing

No videos, real questions, experiment logs, author-machine configurations, or
model weights are supplied. The bundled frames and retrieval queries are entirely
synthetic. Do not commit generated outputs just because software tests pass;
the original dataset and model licenses still govern your own files.
