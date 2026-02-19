from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class PostData:
    id: str
    subreddit: str
    title: str
    selftext: str
    author: str
    score: int
    num_comments: int
    created_utc: float
    permalink: str
    url: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subreddit": self.subreddit,
            "title": self.title,
            "selftext": self.selftext,
            "author": self.author,
            "score": self.score,
            "num_comments": self.num_comments,
            "created_utc": self.created_utc,
            "permalink": self.permalink,
            "url": self.url,
        }


@dataclass(slots=True)
class CommentData:
    id: str
    parent_id: str
    depth: int
    author: str
    score: int
    created_utc: float
    body: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "depth": self.depth,
            "author": self.author,
            "score": self.score,
            "created_utc": self.created_utc,
            "body": self.body,
        }
