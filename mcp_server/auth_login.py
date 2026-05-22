"""
初回認可フロー（keyring版）。

事前条件:
- `python secrets_setup.py import-client <client_secret.json>` で
  client_secrets を Windows 資格情報マネージャーに格納済みであること。

処理:
- keyring から client_secrets を読み出し、ブラウザでGoogle認可を実行する。
- 取得した認可資格情報（refresh_token込）を keyring の oauth_token に保存する。
- ディスクには .env 以外、機密情報を一切書き出さない。

事前にやっておくこと:
1. GCPコンソールで OAuth 2.0 クライアントID（種別: デスクトップアプリ）を作成し、
   client_secret_xxx.json をダウンロード。
2. GA4 / Search Console プロパティに、認可するGoogleアカウントを
   閲覧権限以上で追加（OAuth発行アカウントが既に管理者ならそのままでOK）。
3. `python secrets_setup.py import-client <path>` で keyring に取り込み、
   元の JSON ファイルは削除。
"""

from __future__ import annotations

import json
import os
import sys

import truststore
truststore.inject_into_ssl()

from dotenv import load_dotenv

_HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_HERE, ".env"))

from google_auth_oauthlib.flow import InstalledAppFlow

import secrets_store as ss

SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
]


def main() -> int:
    cs_text = ss.get(ss.KEY_CLIENT_SECRETS)
    if not cs_text:
        print(
            "[error] keyring に client_secrets が無いため認可できません。\n"
            "        先に `python secrets_setup.py import-client <path>` を実行してください。",
            file=sys.stderr,
        )
        return 2

    try:
        client_config = json.loads(cs_text)
    except json.JSONDecodeError as ex:
        print(f"[error] keyring内のclient_secretsが壊れています: {ex}", file=sys.stderr)
        return 2

    print(f"[auth_login] keyring backend = {ss.backend_name()}")
    print("[auth_login] ブラウザを起動してGoogle認可画面を開きます...")

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(
        port=0,
        prompt="consent",
        access_type="offline",
        open_browser=True,
        authorization_prompt_message="ブラウザで認可してください。完了後ここに戻ります。",
        success_message="認可に成功しました。このタブは閉じてください。",
    )

    token_json = creds.to_json()
    ss.put(ss.KEY_OAUTH_TOKEN, token_json)
    print(f"[auth_login] oauth_token を keyring に保存しました (service={ss.service_name()})")
    print("[auth_login] 完了しました。`run_server.bat` で MCP を起動できます。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
