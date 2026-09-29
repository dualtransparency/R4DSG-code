"""Command-line entry points; no implicit visual inference or network requests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from r4dsg import __version__
from r4dsg.adapter import import_graphs
from r4dsg.evaluation import evaluate
from r4dsg.io import read_json, write_json
from r4dsg.memory import Config, build_memory
from r4dsg.qa import ChatClient, Query, build_mcq_prompt, options_from_row
from r4dsg.retrieval import Index
from r4dsg.schema import parse_frames


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="R4DSG cached-observation memory pipeline")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    import_cmd = commands.add_parser(
        "import-graphs", help="Project a node/edge cache using explicit timestamps"
    )
    import_cmd.add_argument("--graphs", required=True)
    import_cmd.add_argument("--manifest", required=True)
    import_cmd.add_argument("--output", required=True)
    build = commands.add_parser("build", help="Build memory from observation-only frames")
    build.add_argument("--frames", required=True)
    build.add_argument("--config")
    build.add_argument("--no-transitions", action="store_true")
    build.add_argument("--output", required=True)
    for name in ("retrieve", "answer"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--memory", required=True)
        cmd.add_argument("--questions", required=True)
        cmd.add_argument("--top-k", type=int, default=8)
        cmd.add_argument("--output", required=True)
        if name == "answer":
            cmd.add_argument("--base-url", required=True)
            cmd.add_argument("--model", required=True)
            cmd.add_argument(
                "--send-to-model",
                action="store_true",
                help="Explicitly consent to sending questions, options and retrieved memory to the endpoint",
            )
    evaluation = commands.add_parser("evaluate")
    evaluation.add_argument("--predictions", required=True)
    evaluation.add_argument("--labels", required=True)
    evaluation.add_argument("--output", required=True)
    for command in commands.choices.values():
        command.add_argument(
            "--overwrite", action="store_true", help="Replace an existing output file"
        )
    return root


def run(args: argparse.Namespace) -> None:
    output = Path(args.output).resolve()
    for name in (
        "graphs",
        "manifest",
        "frames",
        "config",
        "memory",
        "questions",
        "predictions",
        "labels",
    ):
        value = getattr(args, name, None)
        if value and Path(value).resolve() == output:
            raise ValueError("Output must not overwrite an input file")
    if output.exists() and not args.overwrite:
        raise ValueError("Output exists; choose a new path or pass --overwrite")
    if args.command == "import-graphs":
        result = import_graphs(read_json(args.graphs), read_json(args.manifest))
    elif args.command == "build":
        cfg = Config(**read_json(args.config)) if args.config else Config()
        result = build_memory(
            parse_frames(read_json(args.frames)), cfg, transitions=not args.no_transitions
        )
    elif args.command in {"retrieve", "answer"}:
        memory = read_json(args.memory)
        if memory.get("schema_version") != 1:
            raise ValueError("Unsupported memory schema version")
        documents = memory["documents"]
        index = Index(documents)
        by_id = {doc["doc_id"]: doc for doc in documents}
        rows = read_json(args.questions)
        queries = [Query.from_row(row) for row in rows]
        if len({q.id for q in queries}) != len(queries):
            raise ValueError("Duplicate question IDs")
        client = None
        if args.command == "answer":
            if not args.send_to_model:
                raise ValueError("answer requires --send-to-model; prompts leave this process")
            client = ChatClient(args.base_url, args.model)
        result = []
        for query, row in zip(queries, rows):
            hits = index.search(query.question, args.top_k)
            prediction = {"id": query.id, "retrieved": hits}
            if client:
                prompt = build_mcq_prompt(
                    query, options_from_row(row), [by_id[h["doc_id"]] for h in hits]
                )
                prediction["prediction"] = client.answer(prompt)
                prediction["model"] = args.model
            result.append(prediction)
            if client:
                # A failed remote call leaves an explicitly incomplete checkpoint.
                write_json(args.output, result)
    else:
        result = evaluate(read_json(args.predictions), read_json(args.labels))
    write_json(args.output, result)
    if args.command == "evaluate":
        print(json.dumps(result, indent=2))
    else:
        print("Completed " + args.command)


def main() -> None:
    root = parser()
    args = root.parse_args()
    try:
        run(args)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as error:
        # Do not echo user data or server payloads through exception details.
        root.exit(
            2,
            f"{args.command} failed ({type(error).__name__}); validate schema, paths and command arguments. See docs/USAGE.md.\n",
        )
