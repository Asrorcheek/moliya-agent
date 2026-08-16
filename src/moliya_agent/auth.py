from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass


class InvalidSessionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Principal:
    actor_id: str
    username: str
    authentication: str


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

    def create(self, *, username: str, actor_id: str) -> str:
        payload = self._encode(
            json.dumps(
                {
                    "sub": username,
                    "actor_id": actor_id,
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
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            if isinstance(exc, InvalidSessionError):
                raise
            raise InvalidSessionError("Sessiya noto'g'ri") from exc
