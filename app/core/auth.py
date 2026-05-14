from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from pathlib import Path


@dataclass
class User:
    username: str
    display_name: str
    role: str
    can_write: bool
    can_manage_users: bool
    can_clear_data: bool

    def public(self) -> dict:
        return {
            "username": self.username,
            "display_name": self.display_name,
            "role": self.role,
            "can_write": self.can_write,
            "can_manage_users": self.can_manage_users,
            "can_clear_data": self.can_clear_data,
        }


class AuthManager:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.sessions: dict[str, str] = {}
        if not self.path.exists():
            admin_username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
            admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "change-this-password")
            self._write(
                {
                    "users": [
                        self._user_record(admin_username, admin_password, "مدير النظام", "admin", True, True, True),
                        self._user_record("demo", "demo123", "مستخدم عرض تسويقي", "demo", False, False, False),
                    ]
                }
            )

    def authenticate(self, username: str, password: str) -> User | None:
        record = self._find(username)
        if not record:
            return None
        expected = record.get("password_hash", "")
        actual = self._hash_password(password, record.get("salt", ""))
        if not hmac.compare_digest(expected, actual):
            return None
        return self._to_user(record)

    def create_session(self, username: str) -> str:
        token = secrets.token_urlsafe(32)
        self.sessions[token] = username
        return token

    def user_from_token(self, token: str | None) -> User | None:
        if not token:
            return None
        username = self.sessions.get(token)
        if not username:
            return None
        record = self._find(username)
        return self._to_user(record) if record else None

    def logout(self, token: str | None) -> None:
        if token:
            self.sessions.pop(token, None)

    def list_users(self) -> list[dict]:
        return [self._to_user(item).public() for item in self._read().get("users", [])]

    def add_user(
        self,
        username: str,
        password: str,
        display_name: str,
        role: str = "user",
        can_write: bool = True,
        can_manage_users: bool = False,
        can_clear_data: bool = False,
    ) -> User:
        username = username.strip()
        if not username:
            raise ValueError("اسم المستخدم مطلوب.")
        if len(password) < 4:
            raise ValueError("كلمة المرور يجب أن تكون 4 أحرف على الأقل.")
        data = self._read()
        if any(item.get("username") == username for item in data.get("users", [])):
            raise ValueError("اسم المستخدم موجود مسبقًا.")
        record = self._user_record(username, password, display_name or username, role, can_write, can_manage_users, can_clear_data)
        data.setdefault("users", []).append(record)
        self._write(data)
        return self._to_user(record)

    def delete_user(self, username: str) -> None:
        data = self._read()
        remaining = [item for item in data.get("users", []) if item.get("username") != username]
        if len(remaining) == len(data.get("users", [])):
            raise ValueError("المستخدم غير موجود.")
        if not any(item.get("role") == "admin" for item in remaining):
            raise ValueError("لا يمكن حذف آخر مدير للنظام.")
        data["users"] = remaining
        self._write(data)
        for token, session_user in list(self.sessions.items()):
            if session_user == username:
                self.sessions.pop(token, None)

    def _read(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8-sig"))

    def _write(self, payload: dict) -> None:
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _find(self, username: str) -> dict | None:
        for item in self._read().get("users", []):
            if item.get("username") == username:
                return item
        return None

    def _user_record(
        self,
        username: str,
        password: str,
        display_name: str,
        role: str,
        can_write: bool,
        can_manage_users: bool,
        can_clear_data: bool,
    ) -> dict:
        salt = secrets.token_hex(16)
        return {
            "username": username,
            "display_name": display_name,
            "role": role,
            "salt": salt,
            "password_hash": self._hash_password(password, salt),
            "can_write": can_write,
            "can_manage_users": can_manage_users,
            "can_clear_data": can_clear_data,
        }

    def _hash_password(self, password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()

    def _to_user(self, record: dict) -> User:
        return User(
            username=record.get("username", ""),
            display_name=record.get("display_name", record.get("username", "")),
            role=record.get("role", "user"),
            can_write=bool(record.get("can_write", False)),
            can_manage_users=bool(record.get("can_manage_users", False)),
            can_clear_data=bool(record.get("can_clear_data", False)),
        )
