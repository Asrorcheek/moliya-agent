from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass


class InvalidSessionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Principal:
    actor_id: str
    username: str
    authentication: str
    role: str = "owner"
    user_id: str | None = None


_PASSWORD_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, _PASSWORD_ITERATIONS
    )
    salt_encoded = base64.urlsafe_b64encode(salt).decode()
    digest_encoded = base64.urlsafe_b64encode(digest).decode()
    return f"pbkdf2_sha256${_PASSWORD_ITERATIONS}${salt_encoded}${digest_encoded}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        expected = base64.urlsafe_b64decode(digest_text)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            base64.urlsafe_b64decode(salt_text),
            int(iterations_text),
        )
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError):
        return False


class SessionManager:
    def __init__(self, secret: str, lifetime_seconds: int = 8 * 60 * 60) -> None:
        self._secret = secret.encode()
        self.lifetime_seconds = lifetime_seconds

    @staticmethod
    def _encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode().rstrip("=")

    @staticmethod
    def _decode(value: str) -> bytes:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

    def create(
        self,
        *,
        username: str,
        actor_id: str,
        role: str = "owner",
        user_id: str | None = None,
    ) -> str:
        payload = self._encode(
            json.dumps(
                {
                    "sub": username,
                    "actor_id": actor_id,
                    "role": role,
                    "user_id": user_id,
                    "exp": int(time.time()) + self.lifetime_seconds,
                },
                separators=(",", ":"),
            ).encode()
        )
        signature = self._encode(hmac.new(self._secret, payload.encode(), hashlib.sha256).digest())
        return f"{payload}.{signature}"

    def verify(self, token: str) -> Principal:
        try:
            payload, supplied_signature = token.split(".", maxsplit=1)
            expected = self._encode(
                hmac.new(self._secret, payload.encode(), hashlib.sha256).digest()
            )
            if not hmac.compare_digest(supplied_signature, expected):
                raise InvalidSessionError("Sessiya imzosi noto'g'ri")
            data = json.loads(self._decode(payload))
            if int(data["exp"]) < int(time.time()):
                raise InvalidSessionError("Sessiya muddati tugagan")
            return Principal(
                actor_id=str(data["actor_id"]),
                username=str(data["sub"]),
                authentication="session",
                role=str(data.get("role", "owner")),
                user_id=str(data["user_id"]) if data.get("user_id") else None,
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            if isinstance(exc, InvalidSessionError):
                raise
            raise InvalidSessionError("Sessiya noto'g'ri") from exc
