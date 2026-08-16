from __future__ import annotations

import json
import os
import signal
import tempfile
import time
from contextlib import suppress
from pathlib import Path
from threading import RLock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CONFIRM_WORDS = {"ha", "tasdiqlayman", "yoz", "to'g'ri", "to‘g‘ri"}
REJECT_WORDS = {"yo'q", "yo‘q", "rad", "bekor", "bekor qil"}


class BotError(RuntimeError):
    pass


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> dict[str, str]:
        if not self.path.is_file():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return {str(key): str(value) for key, value in data.items()}

    def get(self, user_id: int) -> str | None:
        with self._lock:
            return self._read().get(str(user_id))

    def set(self, user_id: int, draft_id: str) -> None:
        with self._lock:
            data = self._read()
            data[str(user_id)] = draft_id
            self._write(data)

    def clear(self, user_id: int) -> None:
        with self._lock:
            data = self._read()
            data.pop(str(user_id), None)
            self._write(data)

    def _write(self, data: dict[str, str]) -> None:
        descriptor, name = tempfile.mkstemp(prefix=".bot-state-", dir=self.path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                json.dump(data, output, ensure_ascii=False, indent=2, sort_keys=True)
                output.write("\n")
            temporary.chmod(0o600)
            os.replace(temporary, self.path)
        finally:
            if temporary.exists():
                temporary.unlink()


class MoliyaTelegramBot:
    def __init__(self) -> None:
        token = os.environ.get("MOLIYA_TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise BotError("MOLIYA_TELEGRAM_BOT_TOKEN sozlanmagan")
        self.telegram_base = f"https://api.telegram.org/bot{token}"
        self.backend_base = os.environ.get(
            "MOLIYA_AGENT_URL", "http://127.0.0.1:8088"
        ).rstrip("/")
        self.backend_token = os.environ.get("MOLIYA_INTERNAL_TOKEN", "").strip()
        if not self.backend_token:
            raise BotError("MOLIYA_INTERNAL_TOKEN sozlanmagan")
        allowed = os.environ.get("MOLIYA_TELEGRAM_ALLOWED_USERS", "")
        try:
            self.allowed_users = {
                int(item.strip()) for item in allowed.split(",") if item.strip()
            }
        except ValueError as exc:
            raise BotError("MOLIYA_TELEGRAM_ALLOWED_USERS noto'g'ri") from exc
        state_path = Path(
            os.environ.get(
                "MOLIYA_TELEGRAM_STATE_FILE",
                "/home/busin/moliya-agent/data/telegram-state.json",
            )
        )
        self.state = StateStore(state_path)
        self.running = True

    def telegram(self, method: str, payload: dict[str, object]) -> dict[str, object]:
        request = Request(
            f"{self.telegram_base}/{method}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=40) as response:
                result = json.load(response)
        except (HTTPError, URLError, TimeoutError) as exc:
            raise BotError(f"Telegram API bilan aloqa xatosi: {type(exc).__name__}") from exc
        if not result.get("ok"):
            raise BotError("Telegram API so'rovi bajarilmadi")
        return result

    def backend(
        self, method: str, path: str, payload: dict[str, object] | None = None
    ) -> dict[str, object]:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else None
        request = Request(
            f"{self.backend_base}{path}",
            method=method,
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-Moliya-Token": self.backend_token,
            },
        )
        try:
            with urlopen(request, timeout=60) as response:
                return json.load(response)
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(body).get("detail", "Backend xatosi")
            except json.JSONDecodeError:
                detail = "Backend xatosi"
            raise BotError(str(detail)) from exc
        except (URLError, TimeoutError) as exc:
            raise BotError("Moliya backendga ulanib bo'lmadi") from exc

    def send(
        self,
        chat_id: int,
        text: str,
        *,
        buttons: list[list[dict[str, str]]] | None = None,
    ) -> None:
        payload: dict[str, object] = {"chat_id": chat_id, "text": text}
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": buttons}
        self.telegram("sendMessage", payload)

    @staticmethod
    def actor(user_id: int) -> str:
        return f"telegram-{user_id}"

    def allowed(self, user_id: int) -> bool:
        return user_id in self.allowed_users

    def handle_message(self, message: dict[str, object]) -> None:
        chat = message.get("chat") or {}
        sender = message.get("from") or {}
        if not isinstance(chat, dict) or not isinstance(sender, dict):
            return
        chat_id = int(chat.get("id", 0))
        user_id = int(sender.get("id", 0))
        text = str(message.get("text") or "").strip()
        if not chat_id or not user_id or not text:
            return
        if chat.get("type") != "private":
            self.send(chat_id, "Moliya bot faqat shaxsiy chatda ishlaydi.")
            return
        if text.startswith("/start"):
            if self.allowed(user_id):
                self.send(
                    chat_id,
                    "Moliya assistent tayyor. Tushum yoki xarajatni matn bilan yuboring.\n"
                    "Masalan: Bugun naqd 100 000 so'm xarajat, ijara.",
                )
            else:
                self.send(
                    chat_id,
                    f"Sizning Telegram ID: {user_id}\n"
                    "Hozircha ruxsat berilmagan. Ushbu IDni administratorga bering.",
                )
            return
        if not self.allowed(user_id):
            self.send(chat_id, f"Ruxsat berilmagan. Telegram ID: {user_id}")
            return
        if text.startswith("/help"):
            self.send(
                chat_id,
                "Moliyaviy operatsiyani oddiy matn bilan yuboring.\n"
                "/hisobot YYYY-MM — oylik hisobot\n"
                "Tasdiqlashdan oldin hech narsa Google Sheets'ga yozilmaydi.",
            )
            return
        if text.startswith("/hisobot"):
            parts = text.split(maxsplit=1)
            if len(parts) != 2:
                self.send(chat_id, "Format: /hisobot YYYY-MM")
                return
            query = urlencode({"actor_id": self.actor(user_id), "month": parts[1]})
            report = self.backend("GET", f"/v1/reports/monthly?{query}")
            self.send(
                chat_id,
                "Oy: {month}\nTushum: {income_uzs:,} UZS\n"
                "Sof tushum: {net_revenue_uzs:,} UZS\n"
                "Yalpi foyda: {gross_profit_uzs:,} UZS\n"
                "Xarajat: {expense_uzs:,} UZS\n"
                "Sof foyda: {net_profit_uzs:,} UZS".format(**report),
            )
            return
        normalized = text.casefold().strip(" .!?")
        pending = self.state.get(user_id)
        if normalized in CONFIRM_WORDS:
            if not pending:
                self.send(chat_id, "Tasdiqlash uchun kutilayotgan draft yo'q.")
                return
            self.confirm(chat_id, user_id, pending)
            return
        if normalized in REJECT_WORDS:
            if not pending:
                self.send(chat_id, "Rad etish uchun kutilayotgan draft yo'q.")
                return
            self.reject(chat_id, user_id, pending)
            return
        self.create_draft(chat_id, user_id, int(message.get("message_id", 0)), text)

    def create_draft(self, chat_id: int, user_id: int, message_id: int, text: str) -> None:
        old_draft = self.state.get(user_id)
        if old_draft:
            with suppress(BotError):
                self.backend(
                    "POST",
                    f"/v1/drafts/{old_draft}/reject",
                    {"actor_id": self.actor(user_id)},
                )
        result = self.backend(
            "POST",
            "/v1/drafts",
            {
                "actor_id": self.actor(user_id),
                "source_id": f"telegram:{chat_id}:{message_id}",
                "text": text,
                "received_at": None,
            },
        )
        draft = result["draft"]
        draft_id = str(draft["id"])
        self.state.set(user_id, draft_id)
        parsed = draft.get("parsed") or {}
        if isinstance(parsed, dict) and parsed.get("needs_clarification"):
            self.send(chat_id, str(result["preview"]))
            return
        self.send(
            chat_id,
            str(result["preview"]),
            buttons=[
                [
                    {"text": "✅ Tasdiqlash", "callback_data": f"confirm:{draft_id}"},
                    {"text": "❌ Rad etish", "callback_data": f"reject:{draft_id}"},
                ]
            ],
        )

    def confirm(self, chat_id: int, user_id: int, draft_id: str) -> None:
        result = self.backend(
            "POST",
            f"/v1/drafts/{draft_id}/confirm",
            {"actor_id": self.actor(user_id)},
        )
        self.state.clear(user_id)
        self.send(
            chat_id,
            f"✅ Tasdiqlandi. Google Sheets'ga {result['written_rows']} qator yozildi.",
        )

    def reject(self, chat_id: int, user_id: int, draft_id: str) -> None:
        self.backend(
            "POST",
            f"/v1/drafts/{draft_id}/reject",
            {"actor_id": self.actor(user_id)},
        )
        self.state.clear(user_id)
        self.send(chat_id, "❌ Draft rad etildi. Google Sheets'ga yozilmadi.")

    def handle_callback(self, callback: dict[str, object]) -> None:
        sender = callback.get("from") or {}
        message = callback.get("message") or {}
        if not isinstance(sender, dict) or not isinstance(message, dict):
            return
        user_id = int(sender.get("id", 0))
        chat = message.get("chat") or {}
        if not isinstance(chat, dict):
            return
        chat_id = int(chat.get("id", 0))
        callback_id = str(callback.get("id") or "")
        data = str(callback.get("data") or "")
        try:
            if not self.allowed(user_id):
                self.telegram(
                    "answerCallbackQuery",
                    {"callback_query_id": callback_id, "text": "Ruxsat berilmagan"},
                )
                return
            action, draft_id = data.split(":", maxsplit=1)
            if self.state.get(user_id) != draft_id:
                raise BotError("Bu draft eskirgan yoki sizga tegishli emas")
            if action == "confirm":
                self.confirm(chat_id, user_id, draft_id)
            elif action == "reject":
                self.reject(chat_id, user_id, draft_id)
            self.telegram(
                "answerCallbackQuery", {"callback_query_id": callback_id}
            )
        except (BotError, ValueError) as exc:
            self.telegram(
                "answerCallbackQuery",
                {"callback_query_id": callback_id, "text": str(exc)[:180]},
            )

    def run(self) -> None:
        me = self.telegram("getMe", {})["result"]
        print(f"Moliya Telegram bot started: @{me['username']}", flush=True)
        offset = 0
        while self.running:
            try:
                result = self.telegram(
                    "getUpdates",
                    {
                        "offset": offset,
                        "timeout": 25,
                        "allowed_updates": ["message", "callback_query"],
                    },
                )
                for update in result.get("result", []):
                    offset = max(offset, int(update["update_id"]) + 1)
                    try:
                        if "message" in update:
                            self.handle_message(update["message"])
                        elif "callback_query" in update:
                            self.handle_callback(update["callback_query"])
                    except BotError as exc:
                        target = (
                            update.get("message")
                            or update.get("callback_query", {}).get("message")
                            or {}
                        )
                        chat = target.get("chat") or {}
                        if chat.get("id"):
                            self.send(int(chat["id"]), f"Xato: {exc}")
            except BotError as exc:
                print(f"Polling warning: {exc}", flush=True)
                time.sleep(5)


def main() -> None:
    bot = MoliyaTelegramBot()

    def stop(_signum, _frame) -> None:
        bot.running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    bot.run()


if __name__ == "__main__":
    main()
