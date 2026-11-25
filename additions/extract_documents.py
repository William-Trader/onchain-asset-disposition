"""Recreate the textual inputs from the trustee PDFs and the two dated forum excerpts."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def extract(root):
    for pdf in sorted(root.glob("*.pdf")):
        subprocess.run(
            ["pdftotext", "-layout", str(pdf), str(pdf.with_suffix(".txt"))], check=True
        )
    topic = (root / "forum_topic.json").read_bytes()
    source = json.loads(topic)
    selected = {1: "unsupported token", 3: "I host a frontend mirror on uniswap.ch"}
    posts = []
    for post in source["post_stream"]["posts"]:
        number = post["post_number"]
        if number not in selected:
            continue
        excerpt = selected[number]
        assert excerpt in post["cooked"]
        posts.append(
            dict(
                post_number=number,
                time_utc=post["created_at"],
                username=post["username"],
                excerpt=excerpt,
                link=f"https://gov.uniswap.org/t/13586/{number}",
            )
        )
    assert len(posts) == len(selected)
    record = dict(
        url="https://gov.uniswap.org/t/13586.json",
        download_sha256=hashlib.sha256(topic).hexdigest(),
        forum_title=source["title"],
        posts=posts,
    )
    (root / "forum_evidence.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=HERE / "raw")
    extract(parser.parse_args().raw)
