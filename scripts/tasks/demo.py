from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.api.app.conversation.agent import ChatRequest, ConversationAgent


async def run_demo() -> None:
    print("Starting WeatherGPT Demo...")
    agent = ConversationAgent()
    req = ChatRequest(
        session_id="demo_session_001",
        text="Will it rain tomorrow in Pune?",
        language="en",
        stream=True,
    )

    print("\nUser Query: 'Will it rain tomorrow in Pune?'")
    print("Assistant Response: ", end="", flush=True)

    async for event in agent.run_chat(req):
        if event["event"] == "token":
            print(event["data"]["text"], end="", flush=True)
        elif event["event"] == "card":
            print("\n\n[Card Rendered]")
            print(f"Headline: {event['data']['headline']}")
            print(f"Key Values: {event['data']['key_values']}")
            print(f"Source: {event['data']['source_line']}")
            print(f"Caveat: {event['data']['caveat']}")
        elif event["event"] == "done":
            print(f"\nLatency: {event['data']['latency_ms']} ms")


def main() -> int:
    asyncio.run(run_demo())
    print("\nDemo completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
