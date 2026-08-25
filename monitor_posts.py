#!/usr/bin/env python3
"""監控陳昱傑骨科診所官網的新文章，輸出成 Markdown 週報。

Facebook 粉專 (facebook.com/orthoblessing) 從 2018 年起封鎖未登入讀取，
未經 App Review 無法用 Graph API 讀取他人粉專貼文，因此改抓官網 RSS，
內容與粉專高度重疊。

用法：
    python3 monitor_posts.py              # 過去 7 天
    python3 monitor_posts.py --days 14
    python3 monitor_posts.py --json       # 輸出 JSON 供程式串接
"""

import argparse
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

FEED_URL = "https://orthoblessing.com.tw/feed/"
CONTENT_NS = {"content": "http://purl.org/rss/1.0/modules/content/"}
TAIPEI = timezone(timedelta(hours=8))
MAX_PAGES = 10  # 保險上限，避免站方分頁行為異常時無限抓取


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "orthoblessing-monitor/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def strip_html(raw):
    text = re.sub(r"<[^>]+>", " ", html.unescape(raw))
    return re.sub(r"\s+", " ", text).strip()


def parse_page(xml_bytes):
    """把一頁 RSS 轉成文章 dict 清單。"""
    channel = ET.fromstring(xml_bytes)
    posts = []
    for item in channel.findall("./channel/item"):
        body = item.findtext("content:encoded", "", CONTENT_NS) or item.findtext("description", "")
        posts.append(
            {
                "title": (item.findtext("title") or "").strip(),
                "link": (item.findtext("link") or "").strip(),
                "published": parsedate_to_datetime(item.findtext("pubDate")),
                "categories": [c.text for c in item.findall("category") if c.text],
                "text": strip_html(body),
            }
        )
    return posts


def collect(days):
    """往回翻頁直到超出時間範圍，回傳範圍內的文章（新到舊）。"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    found, seen_links = [], set()

    for page in range(1, MAX_PAGES + 1):
        url = FEED_URL if page == 1 else f"{FEED_URL}?paged={page}"
        posts = parse_page(fetch(url))
        if not posts:
            break

        for post in posts:
            if post["published"] >= cutoff and post["link"] not in seen_links:
                seen_links.add(post["link"])
                found.append(post)

        # 這頁最舊的一篇已超出範圍，代表更舊的頁面都不用翻了
        if min(p["published"] for p in posts) < cutoff:
            break

    found.sort(key=lambda p: p["published"], reverse=True)
    return found, cutoff


def excerpt(text, limit=200):
    """取正文開頭當摘要，濾掉每篇結尾固定的訂閱／簽名區塊。"""
    boilerplate = ["居家復健方案免費送", "立即訂閱", "歡迎來找我", "這篇文章最早發佈於"]
    cut = len(text)
    for marker in boilerplate:
        pos = text.find(marker)
        if pos != -1:
            cut = min(cut, pos)
    body = text[:cut].strip() or text
    return body[:limit] + ("…" if len(body) > limit else "")


def render_markdown(posts, cutoff, days):
    now = datetime.now(TAIPEI)
    lines = [
        "# 陳昱傑骨科診所｜近期文章監控",
        "",
        f"- 產生時間：{now:%Y-%m-%d %H:%M} (UTC+8)",
        f"- 監控區間：過去 {days} 天（{cutoff.astimezone(TAIPEI):%Y-%m-%d} 起）",
        f"- 來源：{FEED_URL}",
        f"- 新文章：**{len(posts)} 篇**",
        "",
    ]

    if not posts:
        lines.append("這段期間沒有新文章。")
        return "\n".join(lines)

    for post in posts:
        lines += [
            f"## {post['title']}",
            "",
            f"*{post['published'].astimezone(TAIPEI):%Y-%m-%d %H:%M}*"
            + (f" ｜ {'、'.join(post['categories'])}" if post["categories"] else ""),
            "",
            excerpt(post["text"]),
            "",
            f"[閱讀全文]({post['link']})",
            "",
        ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="監控診所官網新文章")
    parser.add_argument("--days", type=int, default=7, help="回溯天數（預設 7）")
    parser.add_argument("--json", action="store_true", help="輸出 JSON 而非 Markdown")
    args = parser.parse_args()

    try:
        posts, cutoff = collect(args.days)
    except Exception as exc:
        print(f"抓取失敗：{exc}", file=sys.stderr)
        return 1

    if args.json:
        print(
            json.dumps(
                [
                    {
                        "title": p["title"],
                        "link": p["link"],
                        "published": p["published"].astimezone(TAIPEI).isoformat(),
                        "categories": p["categories"],
                        "text": p["text"],
                    }
                    for p in posts
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(render_markdown(posts, cutoff, args.days))
    return 0


if __name__ == "__main__":
    sys.exit(main())
