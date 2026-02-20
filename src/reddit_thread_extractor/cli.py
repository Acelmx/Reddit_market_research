from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .extractor import ExtractionError, extract_thread, fetch_thread_json, save_outputs


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract compact Reddit thread data")
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--url", help="Single Reddit thread URL")
    group.add_argument("--url-file", help="File with Reddit URLs, one per line")

    parser.add_argument("--out-dir", default="Output", help="Output directory path (default: Output)")
    parser.add_argument("--max-comments", type=int, default=500)
    parser.add_argument("--min-score", type=int, default=1)
    parser.add_argument("--include-metadata", action="store_true", default=False)
    parser.add_argument("--min-comment-length", type=int, default=15)
    parser.add_argument("--high-score-keep-short", type=int, default=20)
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        default=False,
        help="Do not prompt for URL when neither --url nor --url-file is provided",
    )
    return parser.parse_args()


def _load_urls(args: argparse.Namespace) -> list[str]:
    if args.url:
        return [args.url.strip()]
    if args.url_file:
        lines = Path(args.url_file).read_text(encoding="utf-8").splitlines()
        return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    if args.no_prompt:
        return []
    entered = input("Reddit thread URL: ").strip()
    return [entered] if entered else []


def main() -> int:
    args = _parse_args()
    out_dir = Path(args.out_dir)
    urls = _load_urls(args)
    if not urls:
        print("No URLs provided", file=sys.stderr)
        return 2

    had_error = False
    for url in urls:
        try:
            payload = fetch_thread_json(url)
            thread = extract_thread(
                payload,
                max_comments=args.max_comments,
                min_score=args.min_score,
                min_length=args.min_comment_length,
                high_score_keep_short=args.high_score_keep_short,
                include_metadata=args.include_metadata,
            )
            paths = save_outputs(thread, out_dir=out_dir)
            print(f"OK {url} -> {', '.join(str(p) for p in paths)}")
        except (ExtractionError, OSError, ValueError) as exc:
            had_error = True
            print(f"ERROR {url}: {exc}", file=sys.stderr)

    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
