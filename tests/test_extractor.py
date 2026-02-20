import json

from reddit_thread_extractor.extractor import extract_thread, render_transcript, save_outputs


def sample_payload():
    return [
        {
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "abc123",
                            "subreddit": "smallbusiness",
                            "title": "A title",
                            "selftext": "Body text",
                            "author": "op",
                            "score": 50,
                            "num_comments": 3,
                            "created_utc": 1700000000,
                            "permalink": "/r/smallbusiness/comments/abc123/x",
                            "url": "https://reddit.com/r/smallbusiness/comments/abc123/x",
                        }
                    }
                ]
            }
        },
        {
            "data": {
                "children": [
                    {
                        "kind": "t1",
                        "data": {
                            "id": "c1",
                            "parent_id": "t3_abc123",
                            "depth": 0,
                            "author": "user1",
                            "score": 10,
                            "created_utc": 1700000001,
                            "body": "Great idea",
                            "replies": "",
                        },
                    },
                    {
                        "kind": "t1",
                        "data": {
                            "id": "c2",
                            "parent_id": "t3_abc123",
                            "depth": 0,
                            "author": "AutoModerator",
                            "score": 100,
                            "created_utc": 1700000002,
                            "body": "Rules",
                            "replies": "",
                        },
                    },
                    {
                        "kind": "t1",
                        "data": {
                            "id": "c3",
                            "parent_id": "t3_abc123",
                            "depth": 0,
                            "author": "user2",
                            "score": 30,
                            "created_utc": 1700000003,
                            "body": "ok",
                            "replies": {
                                "data": {
                                    "children": [
                                        {
                                            "kind": "t1",
                                            "data": {
                                                "id": "c4",
                                                "parent_id": "t1_c3",
                                                "depth": 1,
                                                "author": "user3",
                                                "score": 3,
                                                "created_utc": 1700000004,
                                                "body": "Nested comment with enough length",
                                                "replies": "",
                                            },
                                        }
                                    ]
                                }
                            },
                        },
                    },
                ]
            }
        },
    ]


def test_extract_thread_filters_and_keeps_nested():
    thread = extract_thread(sample_payload(), min_score=1, min_length=10, high_score_keep_short=20)
    ids = [c["id"] for c in thread["comments"]]
    assert ids == ["c1", "c3", "c4"]
    assert thread["post"]["id"] == "abc123"
    assert thread["total_comments_kept"] == 3


def test_render_transcript_format():
    thread = extract_thread(sample_payload(), min_score=1, min_length=10, high_score_keep_short=20)
    txt = render_transcript(thread)
    assert "A title" in txt
    assert "[10] (d=0) user1: Great idea" in txt
    assert "  [3] (d=1) user3: Nested comment with enough length" in txt


def test_save_outputs_json_only_with_descriptive_filename(tmp_path):
    thread = extract_thread(sample_payload(), min_score=1, min_length=10, high_score_keep_short=20)
    paths = save_outputs(thread, out_dir=tmp_path)

    assert len(paths) == 1
    assert paths[0].name == "r-smallbusiness__a-title__abc123.json"
    parsed = json.loads(paths[0].read_text(encoding="utf-8"))
    assert parsed["post"]["id"] == "abc123"
