"""
fetch_serp.py — seo-growth-hacker Skill の唯一の外部 Web 取得経路

設計:
- Claude 側に HTML/DOM を**渡さない**。本ファイル内で fetch → 抽出 → サニタイズまで完結し、
  JSON のみを出力する(信頼境界)。
- SERP 一覧取得は Google HTML スクレイピング(ユーザー選択)。
- 本文側 (各 URL の H2/H3 抽出) は httpx + selectolax。

詳細仕様:
- .claude/skills/seo-growth-hacker/references/serp-fallback.md (CLI/JSONスキーマ)
- .claude/skills/seo-growth-hacker/references/security-model.md (サニタイズ層)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urlparse

import httpx
from selectolax.parser import HTMLParser


# --- 既知ペイロード(security-model.md レイヤー2 と同期させること) -------------

_PAYLOAD_SUBSTRINGS: tuple[str, ...] = (
    "ignore previous",
    "ignore above",
    "system:",
    "assistant:",
    "<|im_start|>",
    "<|im_end|>",
    ".env",
    "environment variable",
    "api key",
    "secret_key",
    "powershell",
    "bash -c",
    "curl ",
    "wget ",
)

_PAYLOAD_REGEXES: tuple[re.Pattern[str], ...] = (
    re.compile(r"send\s+to[^a-z]{0,20}https?://", re.IGNORECASE),
)

# 不可視文字: ゼロ幅・Bidi 制御
_INVISIBLE_CHARS_RE = re.compile(
    "["
    "​"  # ZERO WIDTH SPACE
    "‌"  # ZERO WIDTH NON-JOINER
    "‍"  # ZERO WIDTH JOINER
    "﻿"  # BOM / ZERO WIDTH NO-BREAK SPACE
    "‎"  # LEFT-TO-RIGHT MARK
    "‏"  # RIGHT-TO-LEFT MARK
    "‪-‮"  # Bidi 制御
    "]"
)

_HEADING_MAX_LEN = 200


# --- データ構造 -----------------------------------------------------------------

@dataclass
class FetchResult:
    rank: int
    url: str
    title: str | None = None
    h2: list[str] = field(default_factory=list)
    h3: list[str] = field(default_factory=list)
    fetch_error: bool = False
    blocked_count: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "url": self.url,
            "title": self.title,
            "headings": {"h2": self.h2, "h3": self.h3},
            "fetch_error": self.fetch_error,
            "blocked_count": self.blocked_count,
            "notes": self.notes,
        }


# --- サニタイズ -----------------------------------------------------------------

def sanitize_text(text: str) -> str:
    """単一テキストノードのサニタイズ(タグ削除はパース側で実施済み前提)"""
    text = _INVISIBLE_CHARS_RE.sub("", text)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"<[^>]*>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > _HEADING_MAX_LEN:
        text = text[:_HEADING_MAX_LEN]
    return text


def count_payload_hits(headings: Iterable[str]) -> int:
    """見出し配列に対してペイロード検知件数を返す"""
    hits = 0
    for h in headings:
        lo = h.lower()
        if any(p in lo for p in _PAYLOAD_SUBSTRINGS):
            hits += 1
            continue
        if any(rx.search(h) for rx in _PAYLOAD_REGEXES):
            hits += 1
    return hits


# --- Google SERP スクレイピング -------------------------------------------------

# Google 検索結果の <a> をどう選別するかはここに集約(セレクタが変わったらここだけ直す)
_GOOGLE_INTERNAL_HOSTS = (
    "google.",
    "youtube.com",
    "googleusercontent.com",
    "googleadservices.",
    "gstatic.com",
    "schema.org",
    "webcache.googleusercontent.com",
    "translate.google.",
    "support.google.",
    "policies.google.",
    "accounts.google.",
    "maps.google.",
)


def _extract_serp_urls_from_google_html(html: str, top_n: int) -> list[str]:
    """Google 検索結果ページ HTML から上位 N 件の URL を抽出"""
    tree = HTMLParser(html)
    urls: list[str] = []
    seen: set[str] = set()

    for a in tree.css("a"):
        href = a.attributes.get("href")
        if not href:
            continue

        candidate: str | None = None
        if href.startswith("/url?"):
            qs = parse_qs(urlparse(href).query)
            q = qs.get("q", [None])[0]
            if q and q.startswith("http"):
                candidate = q
        elif href.startswith("http://") or href.startswith("https://"):
            candidate = href

        if not candidate:
            continue

        host = urlparse(candidate).netloc.lower()
        if not host:
            continue
        if any(internal in host for internal in _GOOGLE_INTERNAL_HOSTS):
            continue
        if candidate in seen:
            continue

        seen.add(candidate)
        urls.append(candidate)
        if len(urls) >= top_n:
            break

    return urls


def fetch_google_serp(
    keyword: str,
    top_n: int,
    user_agent: str,
    timeout: float,
) -> list[str]:
    """Google 検索結果ページを取得して上位 URL を返す"""
    params = {
        "q": keyword,
        "hl": "ja",
        "gl": "jp",
        "num": str(min(top_n + 5, 20)),
    }
    headers = {
        "User-Agent": user_agent,
        "Accept-Language": "ja,en;q=0.7",
    }
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers=headers,
    ) as client:
        resp = client.get("https://www.google.com/search", params=params)
        resp.raise_for_status()
        return _extract_serp_urls_from_google_html(resp.text, top_n)


# --- 各ページの本文取得と H2/H3 抽出 -------------------------------------------

def _strip_noise(tree: HTMLParser) -> None:
    """script/style/noscript/template/iframe ノードを除去"""
    for tag in ("script", "style", "noscript", "template", "iframe"):
        for node in tree.css(tag):
            node.decompose()


def _extract_headings(tree: HTMLParser, selector: str) -> list[str]:
    out: list[str] = []
    for node in tree.css(selector):
        # nav/header/footer/aside 配下の見出しはノイズが多いので除外
        parent = node.parent
        skip = False
        while parent is not None:
            tag = (parent.tag or "").lower()
            if tag in ("nav", "header", "footer", "aside"):
                skip = True
                break
            parent = parent.parent
        if skip:
            continue
        text = sanitize_text(node.text(separator=" "))
        if text:
            out.append(text)
    return out


def fetch_page_headings(
    url: str,
    user_agent: str,
    timeout: float,
) -> tuple[str | None, list[str], list[str], list[str]]:
    """1 ページを取得し (title, h2[], h3[], notes[]) を返す。
    通信/パース失敗時は例外を投げる(呼び出し側で notes に詰める)。
    """
    notes: list[str] = []
    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": user_agent,
                "Accept-Language": "ja,en;q=0.7",
            },
        ) as client:
            resp = client.get(url)
            if resp.status_code >= 400:
                raise RuntimeError(f"http_{resp.status_code}")
            html = resp.text
    except httpx.TimeoutException:
        notes.append("timeout")
        raise

    tree = HTMLParser(html)
    _strip_noise(tree)

    title_node = tree.css_first("title")
    title = sanitize_text(title_node.text(separator=" ")) if title_node else None
    if title == "":
        title = None

    h2 = _extract_headings(tree, "h2")
    h3 = _extract_headings(tree, "h3")
    return title, h2, h3, notes


# --- メイン ---------------------------------------------------------------------

_DEFAULT_UA = "ictGrowthHacker-SerpFetcher/1.0 (+seo-growth-hacker Skill; respects robots; contact via repo)"


def _should_exclude(url: str, exclude_hosts: list[str]) -> bool:
    host = urlparse(url).netloc.lower()
    return any(h.lower() in host for h in exclude_hosts)


def run(
    keyword: str,
    top_n: int,
    out_path: Path,
    user_agent: str,
    timeout: float,
    exclude_hosts: list[str],
    run_id: str | None,
) -> int:
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. Google SERP から上位 URL を取得
    try:
        candidate_urls = fetch_google_serp(
            keyword=keyword,
            top_n=top_n + len(exclude_hosts) + 5,
            user_agent=user_agent,
            timeout=timeout,
        )
    except httpx.HTTPError as e:
        print(
            f"[fetch_serp] FATAL: Google SERP取得に失敗 ({type(e).__name__}: {e})",
            file=sys.stderr,
        )
        return 2

    # 2. 除外ホストフィルタ
    filtered = [u for u in candidate_urls if not _should_exclude(u, exclude_hosts)]
    target_urls = filtered[:top_n]

    if not target_urls:
        _write_output(out_path, run_id, keyword, fetched_at, top_n, [])
        print(
            f"[fetch_serp] WARN: '{keyword}' で有効なSERP結果が0件でした",
            file=sys.stderr,
        )
        return 0

    # 3. 各 URL を順次取得
    results: list[FetchResult] = []
    for rank, url in enumerate(target_urls, start=1):
        fr = FetchResult(rank=rank, url=url)
        try:
            title, h2, h3, notes = fetch_page_headings(
                url=url,
                user_agent=user_agent,
                timeout=timeout,
            )
            fr.title = title
            fr.h2 = h2
            fr.h3 = h3
            fr.notes.extend(notes)
        except httpx.TimeoutException:
            fr.fetch_error = True
            fr.notes.append("timeout")
        except (httpx.HTTPError, RuntimeError) as e:
            fr.fetch_error = True
            msg = str(e) if isinstance(e, RuntimeError) else type(e).__name__
            fr.notes.append(f"fetch_error:{msg}")
        else:
            # 4. URL 単位ペイロード検知
            total_hits = count_payload_hits(fr.h2) + count_payload_hits(fr.h3)
            if total_hits > 0:
                fr.blocked_count = total_hits
                fr.h2 = []
                fr.h3 = []
                fr.notes.append("injection_suspected")

        results.append(fr)
        time.sleep(0.5)

    _write_output(out_path, run_id, keyword, fetched_at, top_n, results)

    if all(r.fetch_error for r in results):
        print(
            f"[fetch_serp] WARN: 全 {len(results)} 件で取得失敗",
            file=sys.stderr,
        )
        return 3

    return 0


def _write_output(
    out_path: Path,
    run_id: str | None,
    keyword: str,
    fetched_at: str,
    top_n: int,
    results: list[FetchResult],
) -> None:
    payload = {
        "run_id": run_id,
        "keyword": keyword,
        "fetched_at": fetched_at,
        "top_n": top_n,
        "results": [r.to_dict() for r in results],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _infer_run_id(out_path: Path) -> str | None:
    # `.seo/runs/{run_id}/03-serp.json` 形式なら親ディレクトリ名を run_id とする
    parent = out_path.parent
    if parent.parent.name == "runs":
        return parent.name
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SERP 取得 + サニタイズ済み H2/H3 抽出 (seo-growth-hacker Skill 用)"
    )
    parser.add_argument("--keyword", required=True, help="検索キーワード(UTF-8)")
    parser.add_argument("--top-n", type=int, default=8, help="上位 N 件(既定 8、上限 10)")
    parser.add_argument("--out", required=True, help="出力 JSON パス")
    parser.add_argument(
        "--user-agent",
        default=_DEFAULT_UA,
        help="HTTP User-Agent (既定: Bot UA を明示)",
    )
    parser.add_argument("--timeout", type=float, default=15.0, help="HTTP タイムアウト秒")
    parser.add_argument(
        "--exclude-host",
        action="append",
        default=[],
        help="分析対象から除外するホスト(部分一致、複数指定可)",
    )
    parser.add_argument("--run-id", default=None, help="run_id を明示(省略時は出力パスから推定)")
    args = parser.parse_args(argv)

    if args.top_n < 1 or args.top_n > 10:
        print("[fetch_serp] FATAL: --top-n は 1〜10 の範囲", file=sys.stderr)
        return 2

    out_path = Path(args.out)
    run_id = args.run_id or _infer_run_id(out_path)

    return run(
        keyword=args.keyword,
        top_n=args.top_n,
        out_path=out_path,
        user_agent=args.user_agent,
        timeout=args.timeout,
        exclude_hosts=args.exclude_host,
        run_id=run_id,
    )


if __name__ == "__main__":
    sys.exit(main())
