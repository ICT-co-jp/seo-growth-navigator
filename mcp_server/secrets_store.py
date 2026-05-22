"""
ictgrowthhacker-mcp 用シークレットストア。

Windows では keyring が Windows資格情報マネージャー（DPAPI暗号化）を使う。
mac では Keychain、Linux では Secret Service (gnome-keyring等) を使う。

格納するもの:
- client_secrets : OAuth 2.0 クライアントID JSONの中身（client_secret.jsonの全文）
- oauth_token    : `auth_login.py` で取得した認可済み資格情報のJSON（refresh_token込）

注意:
- Windows資格情報マネージャーの credential blob は最大 2560 バイト。
  client_secret.json と token.json はいずれも数百バイトなので余裕で収まる。
"""
from __future__ import annotations

import os
from typing import Optional

import keyring

DEFAULT_SERVICE = "ictgrowthhacker-mcp"

# キー名（resource name）の定数
KEY_CLIENT_SECRETS = "client_secrets"
KEY_OAUTH_TOKEN = "oauth_token"


def service_name() -> str:
    """環境変数 ICTGROWTHHACKER_KEYRING_SERVICE があればそれを使う。無ければ既定。"""
    s = os.getenv("ICTGROWTHHACKER_KEYRING_SERVICE", "").strip()
    return s or DEFAULT_SERVICE


def get(name: str) -> Optional[str]:
    """資格情報マネージャーから値を読む。存在しなければ None。"""
    return keyring.get_password(service_name(), name)


def put(name: str, value: str) -> None:
    """資格情報マネージャーに上書き保存する。"""
    keyring.set_password(service_name(), name, value)


def delete(name: str) -> bool:
    """資格情報マネージャーから削除する。元から無い場合も True を返す。"""
    try:
        keyring.delete_password(service_name(), name)
        return True
    except keyring.errors.PasswordDeleteError:
        return False


def backend_name() -> str:
    """現在使われている keyring バックエンドの名前（デバッグ用）。"""
    try:
        return keyring.get_keyring().__class__.__name__
    except Exception:
        return "unknown"
