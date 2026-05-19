"""
Google Analytics 4 / Search Console MCPサーバ

- 認証: OAuth 2.0 (リフレッシュトークン方式)
- シークレット: 同フォルダの .env から読み込みます
- 転送方式: stdio (Claude Desktop から直接起動して使う想定)

公開関数:
    GA4 : ga4_run_report / ga4_top_pages / ga4_landing_pages / ga4_traffic_sources / ga4_returning_users
    GSC : gsc_search_analytics / gsc_top_queries / gsc_page_queries / gsc_low_ctr_pages / gsc_position_window
    その他: health_check
"""

from __future__ import annotations

import os
import sys
import logging

import truststore
truststore.inject_into_ssl()
from datetime import date, timedelta
from typing import Any, Optional

from dotenv import load_dotenv

_HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_HERE, ".env"))

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    DateRange,
    Dimension,
    Metric,
    OrderBy,
)
from googleapiclient.discovery import build

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# 初期化
# ---------------------------------------------------------------------------

DEBUG = os.getenv("MCP_DEBUG", "0") == "1"
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    stream=sys.stderr,
    format="[ga4-gsc-mcp] %(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("ga4-gsc-mcp")

GA4_PROPERTY_ID = os.getenv("GA4_PROPERTY_ID", "").strip()
GSC_SITE_URL = os.getenv("GSC_SITE_URL", "").strip()
QUOTA_PROJECT = os.getenv("GOOGLE_QUOTA_PROJECT", "").strip()

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN", "").strip()
TOKEN_URI = "https://oauth2.googleapis.com/token"

SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
]

_credentials: Optional[Credentials] = None
_ga4_client: Optional[BetaAnalyticsDataClient] = None
_gsc_service = None


def _load_credentials() -> Credentials:
    """.env から OAuth クライアント情報とリフレッシュトークンを読み、Credentials を構築する。"""
    missing = [
        name for name, val in (
            ("GOOGLE_CLIENT_ID", CLIENT_ID),
            ("GOOGLE_CLIENT_SECRET", CLIENT_SECRET),
            ("GOOGLE_REFRESH_TOKEN", REFRESH_TOKEN),
        ) if not val
    ]
    if missing:
        raise RuntimeError(
            ".env に必須項目がありません: " + ", ".join(missing) + "\n"
            "README.md の「セットアップ手順」を参照して値を埋めてください。"
        )

    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_uri=TOKEN_URI,
        scopes=SCOPES,
        quota_project_id=QUOTA_PROJECT or None,
    )

    # 初期状態では access_token を持たないため、refresh で取得する。
    log.info("OAuth アクセストークンを取得します")
    creds.refresh(Request())
    return creds


def _creds() -> Credentials:
    global _credentials
    if _credentials is None:
        _credentials = _load_credentials()
    return _credentials


def _ga4() -> BetaAnalyticsDataClient:
    global _ga4_client
    if _ga4_client is None:
        if not GA4_PROPERTY_ID:
            raise RuntimeError("GA4_PROPERTY_ID が設定されていません。")
        _ga4_client = BetaAnalyticsDataClient(credentials=_creds())
    return _ga4_client


def _gsc():
    global _gsc_service
    if _gsc_service is None:
        if not GSC_SITE_URL:
            raise RuntimeError("GSC_SITE_URL が設定されていません。")
        _gsc_service = build(
            "searchconsole", "v1", credentials=_creds(), cache_discovery=False
        )
    return _gsc_service


def _default_range(days: int = 28) -> tuple[str, str]:
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def _ga4_response_to_rows(resp) -> dict[str, Any]:
    dim_headers = [h.name for h in resp.dimension_headers]
    met_headers = [h.name for h in resp.metric_headers]
    rows = []
    for r in resp.rows:
        row: dict[str, Any] = {}
        for i, dh in enumerate(dim_headers):
            row[dh] = r.dimension_values[i].value
        for i, mh in enumerate(met_headers):
            v = r.metric_values[i].value
            try:
                row[mh] = float(v) if "." in v else int(v)
            except ValueError:
                row[mh] = v
        rows.append(row)
    return {
        "row_count": resp.row_count,
        "dimensions": dim_headers,
        "metrics": met_headers,
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# MCP サーバ定義
# ---------------------------------------------------------------------------

mcp = FastMCP("ga4-gsc-analytics")


# ===== GA4 ==================================================================

@mcp.tool()
def ga4_run_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    dimensions: Optional[list[str]] = None,
    metrics: Optional[list[str]] = None,
    order_by_metric: Optional[str] = None,
    descending: bool = True,
    limit: int = 100,
) -> dict[str, Any]:
    """GA4 を任意のディメンション/指標で集計する汎用関数。日付未指定時は直近28日。"""
    if not start_date or not end_date:
        start_date, end_date = _default_range(28)
    dims = [Dimension(name=d) for d in (dimensions or ["pagePath"])]
    mets = [Metric(name=m) for m in (metrics or ["screenPageViews", "sessions"])]
    order_bys = []
    if order_by_metric:
        order_bys.append(
            OrderBy(metric=OrderBy.MetricOrderBy(metric_name=order_by_metric), desc=descending)
        )
    req = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=dims,
        metrics=mets,
        order_bys=order_bys,
        limit=limit,
    )
    resp = _ga4().run_report(req)
    return _ga4_response_to_rows(resp)


@mcp.tool()
def ga4_top_pages(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> dict[str, Any]:
    """期間内のPV上位ページ。"""
    return ga4_run_report(
        start_date=start_date,
        end_date=end_date,
        dimensions=["pagePath", "pageTitle"],
        metrics=["screenPageViews", "sessions", "engagementRate", "averageSessionDuration"],
        order_by_metric="screenPageViews",
        descending=True,
        limit=limit,
    )


@mcp.tool()
def ga4_landing_pages(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> dict[str, Any]:
    """ランディングページ別: セッション、エンゲージメント、平均滞在、コンバージョン。"""
    return ga4_run_report(
        start_date=start_date,
        end_date=end_date,
        dimensions=["landingPage"],
        metrics=[
            "sessions",
            "engagedSessions",
            "engagementRate",
            "averageSessionDuration",
            "screenPageViewsPerSession",
            "conversions",
        ],
        order_by_metric="sessions",
        descending=True,
        limit=limit,
    )


@mcp.tool()
def ga4_traffic_sources(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict[str, Any]:
    """流入チャネル別のセッション、ユーザー、コンバージョン。"""
    return ga4_run_report(
        start_date=start_date,
        end_date=end_date,
        dimensions=["sessionDefaultChannelGroup", "sessionSource", "sessionMedium"],
        metrics=["sessions", "totalUsers", "conversions", "engagementRate"],
        order_by_metric="sessions",
        descending=True,
        limit=100,
    )


@mcp.tool()
def ga4_returning_users(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict[str, Any]:
    """新規ユーザーと再訪ユーザーの比率。"""
    return ga4_run_report(
        start_date=start_date,
        end_date=end_date,
        dimensions=["newVsReturning"],
        metrics=["totalUsers", "sessions", "engagementRate", "averageSessionDuration"],
        order_by_metric="totalUsers",
        descending=True,
        limit=10,
    )


# ===== Search Console =======================================================

def _gsc_query(body: dict[str, Any]) -> dict[str, Any]:
    log.debug("GSC query: %s", body)
    resp = _gsc().searchanalytics().query(siteUrl=GSC_SITE_URL, body=body).execute()
    rows = resp.get("rows", [])
    out = []
    keys = body.get("dimensions", [])
    for r in rows:
        item: dict[str, Any] = {}
        for i, k in enumerate(keys):
            item[k] = r["keys"][i]
        item["clicks"] = r.get("clicks", 0)
        item["impressions"] = r.get("impressions", 0)
        item["ctr"] = round(r.get("ctr", 0), 6)
        item["position"] = round(r.get("position", 0), 3)
        out.append(item)
    return {"row_count": len(out), "rows": out}


@mcp.tool()
def gsc_search_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    dimensions: Optional[list[str]] = None,
    row_limit: int = 500,
    search_type: str = "web",
) -> dict[str, Any]:
    """Search Console を任意ディメンションで集計する汎用関数。"""
    if not start_date or not end_date:
        start_date, end_date = _default_range(28)
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions or ["query"],
        "rowLimit": row_limit,
        "type": search_type,
    }
    return _gsc_query(body)


@mcp.tool()
def gsc_top_queries(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
) -> dict[str, Any]:
    """クリック上位クエリ。"""
    return gsc_search_analytics(start_date, end_date, ["query"], limit)


@mcp.tool()
def gsc_page_queries(
    page: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
) -> dict[str, Any]:
    """特定URLのクエリ別 CTR / 平均掲載順位。"""
    if not start_date or not end_date:
        start_date, end_date = _default_range(28)
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["query"],
        "rowLimit": limit,
        "type": "web",
        "dimensionFilterGroups": [
            {"filters": [{"dimension": "page", "operator": "equals", "expression": page}]}
        ],
    }
    return _gsc_query(body)


@mcp.tool()
def gsc_low_ctr_pages(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_impressions: int = 500,
    max_ctr: float = 0.02,
    limit: int = 200,
) -> dict[str, Any]:
    """表示数が min_impressions 以上で CTR が max_ctr 以下のページ。"""
    raw = gsc_search_analytics(start_date, end_date, ["page"], 5000)
    rows = [
        r for r in raw["rows"]
        if r["impressions"] >= min_impressions and r["ctr"] <= max_ctr
    ]
    rows.sort(key=lambda r: r["impressions"], reverse=True)
    return {"row_count": len(rows[:limit]), "rows": rows[:limit]}


@mcp.tool()
def gsc_position_window(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_position: float = 4.0,
    max_position: float = 15.0,
    min_impressions: int = 200,
    limit: int = 200,
) -> dict[str, Any]:
    """平均掲載順位が指定レンジ(既定 4-15位)のページ。"""
    raw = gsc_search_analytics(start_date, end_date, ["page"], 5000)
    rows = [
        r for r in raw["rows"]
        if r["impressions"] >= min_impressions
        and min_position <= r["position"] <= max_position
    ]
    rows.sort(key=lambda r: (r["position"], -r["impressions"]))
    return {"row_count": len(rows[:limit]), "rows": rows[:limit]}


# ===== ヘルスチェック =======================================================

@mcp.tool()
def health_check() -> dict[str, Any]:
    """設定値と各APIへの疎通を軽く確認する。"""
    out: dict[str, Any] = {
        "ga4_property_id_set": bool(GA4_PROPERTY_ID),
        "gsc_site_url": GSC_SITE_URL or None,
        "quota_project": QUOTA_PROJECT or None,
        "client_id_set": bool(CLIENT_ID),
        "client_secret_set": bool(CLIENT_SECRET),
        "refresh_token_set": bool(REFRESH_TOKEN),
        "ga4_ok": False,
        "gsc_ok": False,
    }
    try:
        s, e = _default_range(2)
        _ = ga4_run_report(s, e, ["date"], ["sessions"], None, True, 5)
        out["ga4_ok"] = True
    except Exception as ex:
        out["ga4_error"] = str(ex)
    try:
        s, e = _default_range(2)
        _ = gsc_search_analytics(s, e, ["date"], 5)
        out["gsc_ok"] = True
    except Exception as ex:
        out["gsc_error"] = str(ex)
    return out


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    log.info(
        "ga4-gsc-mcp 起動: GA4_PROPERTY_ID=%s, GSC_SITE_URL=%s",
        GA4_PROPERTY_ID or "(未設定)",
        GSC_SITE_URL or "(未設定)",
    )
    mcp.run()
