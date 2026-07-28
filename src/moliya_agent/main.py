from __future__ import annotations

from .config import Settings


def main() -> None:
    import uvicorn

    settings = Settings.from_env()
    uvicorn.run(
        "moliya_agent.api:app",
        host=settings.bind_host,
        port=settings.bind_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
