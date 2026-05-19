"""
任意サイトの sitemap (index 含む) を辿って URL 一覧を CSV に書き出すユーティリティ。

特徴:
- sitemap.xml と子 sitemap ファイルのみを取得する。記事本体 URL は取得しない。
- リクエスト間にディレイを挟む（既定 1.0 秒）。
- 子 sitemap 取得本数と URL 総数に上限を設けて事故を防ぐ。
- dry-run で sitemap 一覧だけ確認できる。
- 同一 URL は最後の lastmod を残して重複排除し、url 列でソート。

使い方:
    python sitemap_to_csv.py SITEMAP_URL OUTPUT_CSV [options]

例:
    # 標準実行（既定: 1 秒間隔、子 sitemap 最大 200 本）
    python sitemap_to_csv.py https://example.com/sitemap.xml ../data/url_inventory.csv

    # 速めに走らせる（リクエスト間 0.3 秒）
    python sitemap_to_csv.py https://example.com/sitemap.xml ../data/url_inventory.csv --delay 0.3

    # サイズ感だけ把握（fetch するのは index と最初の子 sitemap だけ）
    python sitemap_to_csv.py https://example.com/sitemap.xml /tmp/x.csv --dry-run

    # 大量 URL が懸念される場合は上限を効かせる
    python sitemap_to_csv.py https://example.com/sitemap.xml ../data/url_inventory.csv --max-urls 5000

このスクリプトは MCP サーバではなく、棚卸しの入口として手動で叩く想定。
取得後は GA4 / GSC データと url 列でジョインして「読まれている／読まれていない」を判別する。
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
import urllib.request
from xml.etree import ElementTree as ET

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

USER_AGENT = "ga4-gsc-mcp-sitemap/1.0"


def fetch(url: str, timeout: float = 30.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def crawl(
    sitemap_url: str,
    delay: float,
    max_sitemaps: int,
    max_urls: int,
    dry_run: bool,
) -> tuple[list[dict[str, str]], list[str]]:
    """sitemapを再帰的にたどって (rows, fetched_sitemaps) を返す。"""
    rows: list[dict[str, str]] = []
    fetched: list[str] = []
    visited: set[str] = set()
    queue: list[str] = [sitemap_url]

    def _quota_ok() -> bool:
        if len(fetched) >= max_sitemaps:
            print(f"[stop] max-sitemaps={max_sitemaps} に達したため停止します。", file=sys.stderr)
            return False
        if max_urls > 0 and len(rows) >= max_urls:
            print(f"[stop] max-urls={max_urls} に達したため停止します。", file=sys.stderr)
            return False
        return True

    first = True
    while queue and _quota_ok():
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        if not first:
            time.sleep(delay)
        first = False

        print(f"[fetch] ({len(fetched)+1}) {url}", file=sys.stderr)
        try:
            body = fetch(url)
        except Exception as ex:
            print(f"[warn] {url}: {ex}", file=sys.stderr)
            continue
        fetched.append(url)

        try:
            root = ET.fromstring(body)
        except ET.ParseError as ex:
            print(f"[warn] parse error {url}: {ex}", file=sys.stderr)
            continue

        tag = root.tag.lower()
        if tag.endswith("sitemapindex"):
            children = []
            for s in root.findall("sm:sitemap", NS):
                loc = s.findtext("sm:loc", default="", namespaces=NS).strip()
                if loc:
                    children.append(loc)
            print(f"[info]   index に {len(children)} 件の子sitemapを発見", file=sys.stderr)
            if dry_run:
                # dry-runは index と最初の子1本だけサイズ感を見る
                if children:
                    queue.append(children[0])
                continue
            queue.extend(children)
        elif tag.endswith("urlset"):
            added = 0
            for u in root.findall("sm:url", NS):
                loc = u.findtext("sm:loc", default="", namespaces=NS).strip()
                lastmod = u.findtext("sm:lastmod", default="", namespaces=NS).strip()
                if loc:
                    rows.append({"url": loc, "lastmod": lastmod, "source_sitemap": url})
                    added += 1
                    if max_urls > 0 and len(rows) >= max_urls:
                        break
            print(f"[info]   urlset から {added} 件のURLを取得 (累計 {len(rows)})", file=sys.stderr)
        else:
            print(f"[warn] unknown root tag at {url}: {tag}", file=sys.stderr)

    return rows, fetched


def write_csv(rows: list[dict[str, str]], out_path: str) -> int:
    by_url: dict[str, dict[str, str]] = {}
    for r in rows:
        cur = by_url.get(r["url"])
        if cur is None or r["lastmod"] > cur["lastmod"]:
            by_url[r["url"]] = r
    deduped = list(by_url.values())
    deduped.sort(key=lambda r: r["url"])
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["url", "lastmod", "source_sitemap"])
        w.writeheader()
        w.writerows(deduped)
    return len(deduped)


def main() -> int:
    p = argparse.ArgumentParser(description="sitemap ダンプユーティリティ")
    p.add_argument("sitemap_url", help="入口 sitemap.xml の URL")
    p.add_argument("output_csv", help="出力CSVパス")
    p.add_argument(
        "--delay", type=float, default=1.0,
        help="リクエスト間ディレイ秒（既定 1.0）",
    )
    p.add_argument(
        "--max-sitemaps", type=int, default=200,
        help="取得する子sitemap本数の上限（既定 200）",
    )
    p.add_argument(
        "--max-urls", type=int, default=0,
        help="取得するURL総数の上限。0=無制限（既定 0）",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="index と最初の子sitemap 1本だけ取って終了。CSVは書き出さない。",
    )
    args = p.parse_args()

    print(
        f"[start] sitemap={args.sitemap_url} "
        f"delay={args.delay}s max_sitemaps={args.max_sitemaps} "
        f"max_urls={args.max_urls or '無制限'} dry_run={args.dry_run}",
        file=sys.stderr,
    )

    rows, fetched = crawl(
        sitemap_url=args.sitemap_url,
        delay=args.delay,
        max_sitemaps=args.max_sitemaps,
        max_urls=args.max_urls,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print(
            f"[dry-run done] fetched_sitemaps={len(fetched)} "
            f"sample_urls={len(rows)}",
            file=sys.stderr,
        )
        return 0

    n = write_csv(rows, args.output_csv)
    print(
        f"[done] fetched_sitemaps={len(fetched)} unique_urls={n} -> {args.output_csv}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
