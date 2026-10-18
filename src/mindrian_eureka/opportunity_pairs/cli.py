"""Command-line interface for the local opportunity-pair capability."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .cache import EmbeddingCache, default_cache_path
from .runner import load_input, run_document


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="eureka-rs",
        description="Find local cross-domain opportunity-pair candidates from RS signal disagreement.",
    )
    parser.add_argument("input", help="JSON input bundle containing objective and traceable artifacts")
    parser.add_argument("--encoder", choices=("reference-bert", "sentence-transformers"), default="reference-bert")
    parser.add_argument("--model-path", required=True, help="Local model directory or model ID (download requires --allow-model-download)")
    parser.add_argument("--allow-model-download", action="store_true", help="Allow the model library to fetch model files")
    parser.add_argument("--model-revision", help="Immutable model revision; required when downloading weights")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--job-id", default="local-rs-run")
    parser.add_argument("--cache-path", default=str(default_cache_path()), help="Local SQLite embeddings cache file")
    parser.add_argument("--output", default="-", help="Output JSON path (default: stdout)")
    args = parser.parse_args()
    try:
        document = load_input(args.input)
        result = run_document(
            document, encoder_name=args.encoder, model_path=args.model_path,
            allow_model_download=args.allow_model_download, top_k=args.top_k,
            job_id=args.job_id, model_revision=args.model_revision, cache_path=args.cache_path,
        )
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output == "-":
            sys.stdout.write(rendered)
        else:
            Path(args.output).write_text(rendered, encoding="utf-8")
    except Exception as exc:
        parser.exit(2, f"eureka-rs: {exc}\n")


def clear_cache_main() -> None:
    parser = argparse.ArgumentParser(prog="eureka-rs-cache-clear")
    parser.add_argument("--cache-path", default=str(default_cache_path()))
    args = parser.parse_args()
    cache = EmbeddingCache(args.cache_path)
    removed = cache.clear()
    print(json.dumps({"deleted_embeddings": removed, "cache_path": args.cache_path}))


if __name__ == "__main__":
    main()
