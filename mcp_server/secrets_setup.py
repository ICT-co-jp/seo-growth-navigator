"""
シークレット取り込みCLI。

OAuth 2.0 クライアントID JSON（GCPでデスクトップアプリとして発行したもの）を
Windows資格情報マネージャーに取り込む。取り込み後はソースのJSONファイルを削除して
ディスク上に平文を残さないようにする。

使い方:
    python secrets_setup.py import-client <client_secret.jsonへのパス>
    python secrets_setup.py status
    python secrets_setup.py delete-token         # 現在のリフレッシュトークンを削除
    python secrets_setup.py delete-client        # クライアントシークレットも削除（再認可必要）

実行例:
    python secrets_setup.py import-client C:\\Users\\%USERPROFILE%\\Downloads\\client_secret_xxx.json
"""
from __future__ import annotations

import json
import os
import sys

from dotenv import load_dotenv

_HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_HERE, ".env"))

import secrets_store as ss


def _validate_client_secret_json(text: str) -> dict:
    """client_secret.jsonとして妥当か検証して dict で返す。"""
    obj = json.loads(text)
    # GCPの「デスクトップアプリ」種別なら installed セクションがある
    section = obj.get("installed") or obj.get("web")
    if not section:
        raise ValueError("client_secret.json に installed/web セクションがありません。")
    for k in ("client_id", "client_secret", "auth_uri", "token_uri"):
        if not section.get(k):
            raise ValueError(f"client_secret.json に {k} がありません。")
    return obj


def cmd_import_client(path: str) -> int:
    if not os.path.exists(path):
        print(f"[error] ファイルが見つかりません: {path}", file=sys.stderr)
        return 2
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    try:
        _validate_client_secret_json(text)
    except Exception as ex:
        print(f"[error] 無効な client_secret.json: {ex}", file=sys.stderr)
        return 2
    ss.put(ss.KEY_CLIENT_SECRETS, text)
    print(f"[ok] client_secrets を keyring に保存しました (service={ss.service_name()}, backend={ss.backend_name()})")
    print("[next] 元の client_secret.json は削除してください。")
    print("       次に `python auth_login.py` でブラウザ認可を実行します。")
    return 0


def cmd_status() -> int:
    cs = ss.get(ss.KEY_CLIENT_SECRETS)
    tk = ss.get(ss.KEY_OAUTH_TOKEN)
    print(f"keyring service : {ss.service_name()}")
    print(f"keyring backend : {ss.backend_name()}")
    print(f"client_secrets  : {'present' if cs else 'absent'}")
    print(f"oauth_token     : {'present' if tk else 'absent'}")
    return 0


def cmd_delete(name: str) -> int:
    ok = ss.delete(name)
    print(f"[{'ok' if ok else 'noop'}] delete {name}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "import-client":
        if len(argv) < 3:
            print("Usage: secrets_setup.py import-client <path>", file=sys.stderr)
            return 2
        return cmd_import_client(argv[2])
    if cmd == "status":
        return cmd_status()
    if cmd == "delete-token":
        return cmd_delete(ss.KEY_OAUTH_TOKEN)
    if cmd == "delete-client":
        return cmd_delete(ss.KEY_CLIENT_SECRETS)
    print(f"unknown command: {cmd}", file=sys.stderr)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
