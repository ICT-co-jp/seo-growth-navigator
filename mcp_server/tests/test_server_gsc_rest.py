"""server.py の Search Console REST 呼び出しをネットワーク無しで確認する。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_MCP_SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_MCP_SERVER))

import server  # noqa: E402


class _DummyResponse:
    status_code = 200
    text = ""

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {
            "rows": [
                {
                    "keys": ["検索語"],
                    "clicks": 3,
                    "impressions": 120,
                    "ctr": 0.025,
                    "position": 7.1234,
                }
            ]
        }


class _DummySession:
    def __init__(self) -> None:
        self.url: str | None = None
        self.body: dict[str, Any] | None = None
        self.timeout: int | None = None

    def post(self, url: str, json: dict[str, Any], timeout: int) -> _DummyResponse:
        self.url = url
        self.body = json
        self.timeout = timeout
        return _DummyResponse()


def test_gsc_query_posts_to_direct_rest_endpoint() -> None:
    session = _DummySession()
    old_site_url = server.GSC_SITE_URL
    old_gsc = server._gsc
    try:
        server.GSC_SITE_URL = "https://example.com/"
        server._gsc = lambda: session  # type: ignore[method-assign]

        result = server._gsc_query({"dimensions": ["query"], "rowLimit": 1})
    finally:
        server.GSC_SITE_URL = old_site_url
        server._gsc = old_gsc  # type: ignore[method-assign]

    assert session.url == (
        "https://searchconsole.googleapis.com/webmasters/v3/sites/"
        "https%3A%2F%2Fexample.com%2F/searchAnalytics/query"
    )
    assert session.body == {"dimensions": ["query"], "rowLimit": 1}
    assert session.timeout == 30
    assert result == {
        "row_count": 1,
        "rows": [
            {
                "query": "検索語",
                "clicks": 3,
                "impressions": 120,
                "ctr": 0.025,
                "position": 7.123,
            }
        ],
    }


def _run() -> int:
    tests = [(k, v) for k, v in globals().items() if k.startswith("test_") and callable(v)]
    failed: list[str] = []
    for name, fn in tests:
        try:
            fn()
        except AssertionError as e:
            failed.append(f"{name}: {e}")
        except Exception as e:
            failed.append(f"{name}: {type(e).__name__}: {e}")
    if failed:
        print("FAILED:")
        for failure in failed:
            print(" -", failure)
        return 1
    print(f"OK ({len(tests)} tests)")
    return 0


if __name__ == "__main__":
    sys.exit(_run())
