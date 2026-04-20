from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .models import PaperRequest
from .sources import SourceRetrievalError
from .workflow import PaperWorkflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a source-verifiable academic paper draft.")
    parser.add_argument("--input", required=True, help="Absolute path to the JSON request file.")
    parser.add_argument("--output-dir", help="Optional output directory. Defaults to the request value or ./output.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    input_path = Path(args.input).expanduser().resolve()
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    request = PaperRequest.from_dict(payload)
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else (input_path.parent / request.output_dir).resolve()

    try:
        result = PaperWorkflow().generate(request)
    except SourceRetrievalError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    paper_path, sources_path = result.write_to_directory(output_dir)
    print(f"paper: {paper_path}")
    print(f"sources: {sources_path}")


if __name__ == "__main__":
    main()
