from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any
from urllib import error, request

from .models import CommentData, PostData

USER_AGENT = "RedditThreadExtractor/1.0 (+https://example.local)"


class ExtractionError(Exception):
    """Raised when a Reddit thread cannot be extracted."""


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def _token_estimate(text: str) -> int:
    return max(1, len(text) // 4) if text else 0


def _thread_json_url(url: str) -> str:
    clean = url.strip()
    if not clean:
        raise ExtractionError("URL is empty")
    if ".json" in clean:
        return clean
    return clean.rstrip("/") + ".json"


def fetch_thread_json(
    url: str,
    timeout_s: int = 20,
    max_retries: int = 4,
) -> list[Any]:
    target = _thread_json_url(url)
    wait = 1.0

    for attempt in range(max_retries + 1):
        req = request.Request(target, headers={"User-Agent": USER_AGENT})
        try:
            with request.urlopen(req, timeout=timeout_s) as response:
                body = response.read().decode("utf-8")
                payload = json.loads(body)
                if not isinstance(payload, list) or len(payload) < 2:
                    raise ExtractionError("Unexpected Reddit JSON shape (expected 2-item list)")
                return payload
        except error.HTTPError as exc:
            if exc.code in {429, 500, 502, 503, 504} and attempt < max_retries:
                time.sleep(wait)
                wait *= 2
                continue
            raise ExtractionError(f"Request failed with status {exc.code}: {target}") from exc
        except (error.URLError, TimeoutError) as exc:
            if attempt < max_retries:
                time.sleep(wait)
                wait *= 2
                continue
            raise ExtractionError(f"Network error after retries: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise ExtractionError(f"Invalid JSON payload: {exc}") from exc

    raise ExtractionError(f"Failed to fetch thread: {target}")


def _extract_post(payload: list[Any]) -> PostData:
    post_listing = payload[0].get("data", {}).get("children", [])
    if not post_listing:
        raise ExtractionError("Post listing is empty")
    data = post_listing[0].get("data", {})
    return PostData(
        id=str(data.get("id", "")),
        subreddit=str(data.get("subreddit", "")),
        title=str(data.get("title", "")),
        selftext=_normalize_whitespace(str(data.get("selftext", ""))),
        author=str(data.get("author", "")),
        score=int(data.get("score", 0) or 0),
        num_comments=int(data.get("num_comments", 0) or 0),
        created_utc=float(data.get("created_utc", 0) or 0),
        permalink=str(data.get("permalink", "")),
        url=str(data.get("url", "")),
    )


def _should_keep_comment(
    comment_data: dict[str, Any],
    min_score: int,
    min_length: int,
    high_score_keep_short: int,
) -> bool:
    author = str(comment_data.get("author", ""))
    body_raw = str(comment_data.get("body", ""))
    body = _normalize_whitespace(body_raw)
    score = int(comment_data.get("score", 0) or 0)

    if author.lower() == "automoderator":
        return False
    if comment_data.get("stickied") and author.lower().endswith("mod"):
        return False
    if body in {"[deleted]", "[removed]", ""}:
        return False
    if score < min_score:
        return False
    if len(body) < min_length and score < high_score_keep_short:
        return False
    return True


def _walk_comment_tree(
    children: list[dict[str, Any]],
    out: list[CommentData],
    min_score: int,
    max_comments: int,
    min_length: int,
    high_score_keep_short: int,
) -> None:
    for item in children:
        if len(out) >= max_comments:
            return
        if item.get("kind") != "t1":
            continue

        data = item.get("data", {})
        if _should_keep_comment(data, min_score, min_length, high_score_keep_short):
            out.append(
                CommentData(
                    id=str(data.get("id", "")),
                    parent_id=str(data.get("parent_id", "")),
                    depth=int(data.get("depth", 0) or 0),
                    author=str(data.get("author", "")),
                    score=int(data.get("score", 0) or 0),
                    created_utc=float(data.get("created_utc", 0) or 0),
                    body=_normalize_whitespace(str(data.get("body", ""))),
                )
            )

        replies = data.get("replies")
        if isinstance(replies, dict):
            nested = replies.get("data", {}).get("children", [])
            _walk_comment_tree(
                nested,
                out,
                min_score=min_score,
                max_comments=max_comments,
                min_length=min_length,
                high_score_keep_short=high_score_keep_short,
            )


def extract_thread(
    payload: list[Any],
    max_comments: int = 500,
    min_score: int = 1,
    min_length: int = 15,
    high_score_keep_short: int = 20,
    include_metadata: bool = False,
) -> dict[str, Any]:
    post = _extract_post(payload)
    comments_root = payload[1].get("data", {}).get("children", [])

    comments: list[CommentData] = []
    _walk_comment_tree(
        comments_root,
        comments,
        min_score=min_score,
        max_comments=max_comments,
        min_length=min_length,
        high_score_keep_short=high_score_keep_short,
    )

    all_text = post.title + "\n" + post.selftext + "\n" + "\n".join(c.body for c in comments)
    result: dict[str, Any] = {
        "post": post.to_dict(),
        "comments": [c.to_dict() for c in comments],
        "total_comments_kept": len(comments),
        "total_chars": len(all_text),
        "total_tokens_estimate": _token_estimate(all_text),
    }
    if include_metadata:
        result["metadata"] = {
            "filtering": {
                "min_score": min_score,
                "min_length": min_length,
                "high_score_keep_short": high_score_keep_short,
                "remove_automoderator": True,
                "remove_deleted_or_removed": True,
                "remove_empty": True,
                "remove_stickied_moderator": True,
            }
        }
    return result


def render_transcript(thread: dict[str, Any]) -> str:
    post = thread["post"]
    lines = [post.get("title", "").strip()]
    body = _normalize_whitespace(post.get("selftext", ""))
    if body:
        lines.append(body)
    lines.append("")

    for comment in thread.get("comments", []):
        depth = int(comment.get("depth", 0) or 0)
        indent = "  " * max(0, depth)
        score = int(comment.get("score", 0) or 0)
        author = str(comment.get("author", ""))
        text = _normalize_whitespace(str(comment.get("body", "")))
        lines.append(f"{indent}[{score}] (d={depth}) {author}: {text}")

    return "\n".join(lines).strip() + "\n"


def _slugify(value: str, max_len: int = 48) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (cleaned[:max_len]).strip("-") or "untitled"


def _json_filename(thread: dict[str, Any]) -> str:
    post = thread.get("post", {})
    post_id = str(post.get("id", "unknown")).strip() or "unknown"
    subreddit = _slugify(str(post.get("subreddit", "")).strip() or "unknown", max_len=24)
    title_slug = _slugify(str(post.get("title", "")), max_len=60)
    return f"r-{subreddit}__{title_slug}__{post_id}.json"


def save_outputs(thread: dict[str, Any], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / _json_filename(thread)
    json_path.write_text(json.dumps(thread, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return [json_path]
