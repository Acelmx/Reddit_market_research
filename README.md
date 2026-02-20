# Reddit Thread Extractor

CLI tool to fetch Reddit thread JSON, keep only key fields, and write compact outputs.

## Configuration used for this implementation
- Mode: CLI only
- Default max comments: 500
- Filtering defaults:
  - remove AutoModerator comments
  - remove `[deleted]` / `[removed]`
  - remove empty bodies
  - `min_score=1`
  - remove stickied moderator comments
  - remove very short comments (default `<15` chars) unless score is high (`>=20`)

## Install
```bash
pip install -e .
```

## Usage
Interactive single URL (easiest):
```bash
reddit
```
You will be prompted for a Reddit thread URL and a JSON file will be saved in `Output/`.

Single URL (non-interactive):
```bash
reddit \
  --url "https://www.reddit.com/r/smallbusiness/comments/1r7e6fp/whats_the_best_boring_business_youve_seen_someone/" \
  --out-dir "/absolute/path/to/output" \
  --max-comments 500 \
  --min-score 1
```

Multiple URLs from file:
```bash
reddit \
  --url-file urls.txt \
  --out-dir "/absolute/path/to/output"
```

## CLI flags
- `--url` single Reddit URL
- `--url-file` file of URLs, one per line
- `--out-dir` output directory (default: `Output`)
- `--max-comments` maximum comments to keep
- `--min-score` minimum score threshold
- `--include-metadata` include filter metadata in thin JSON
- `--min-comment-length` short-comment threshold (default 15)
- `--high-score-keep-short` keep short comments when score is at least this value (default 20)
- `--no-prompt` disable interactive URL prompt when no URL options are provided

## Outputs
Per thread, one JSON file:
- `r-<subreddit>__<title-slug>__<post_id>.json`

`thin_json` structure:
- `post`: `{ id, subreddit, title, selftext, author, score, num_comments, created_utc, permalink, url }`
- `comments`: list of `{ id, parent_id, depth, author, score, created_utc, body }`
- derived counts: `total_comments_kept`, `total_chars`, `total_tokens_estimate`

## Notes
- Uses a real `User-Agent`.
- Retries transient errors (`429`, `5xx`) with exponential backoff.
- Handles nested comment trees recursively.
- Handles `replies` values that may be empty strings.
- Continues processing other URLs when one URL fails.
