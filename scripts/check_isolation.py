#!/usr/bin/env python3
"""Assert that the compose stack keeps its data stores off the host network.

Redis and ChromaDB hold the ESI cache and the whole knowledge base, and neither
authenticates by default. They used to run with network_mode: "host", which put
them on every interface of the machine. This check exists so that cannot come
back unnoticed — reaching for `network_mode: host` or a `ports:` entry is an
easy thing to do while debugging and an easy thing to forget to undo.

Run it directly: python3 scripts/check_isolation.py
"""

import sys
from pathlib import Path

import yaml

COMPOSE = Path(__file__).parent.parent / "docker-compose.yml"

# Ollama runs on the host, so the bot needs a route to it. That is the one
# service allowed to talk outward, and it does so via the bridge gateway rather
# than by joining the host's network namespace.
BOT_SERVICE = "eve-discord-bot"


def main() -> int:
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    services = compose.get("services", {})
    problems = []

    if not services:
        problems.append("no services found — is docker-compose.yml intact?")

    for name, svc in services.items():
        if "network_mode" in svc:
            problems.append(
                f"{name}: network_mode is set to {svc['network_mode']!r}; "
                "services must stay on the private compose network"
            )

        if svc.get("ports"):
            problems.append(
                f"{name}: publishes {svc['ports']} to the host; "
                "use `docker compose exec` for debugging instead"
            )

        if not svc.get("networks"):
            problems.append(f"{name}: not attached to the private network")

    redis = services.get("eve-redis", {})
    command = " ".join(redis.get("command", []))
    if "--requirepass" not in command:
        problems.append("eve-redis: started without --requirepass")

    bot_env = services.get(BOT_SERVICE, {}).get("environment", [])
    if not any(str(e).startswith("REDIS_PASSWORD=") for e in bot_env):
        problems.append(f"{BOT_SERVICE}: no REDIS_PASSWORD passed through")

    if problems:
        print("Container isolation check FAILED:\n")
        for p in problems:
            print(f"  - {p}")
        return 1

    print(f"Container isolation check passed ({len(services)} services).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
