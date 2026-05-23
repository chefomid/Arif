"""Terminal chatbot via llama-server (Nemotron GGUF)."""
from __future__ import annotations

import sys

from openai import OpenAI

from config import get_settings

SYSTEM = (
    "You are Arif, a helpful AI assistant running locally. "
    "Be concise and clear."
)


def main() -> None:
    settings = get_settings()
    client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)

    try:
        client.models.list()
    except Exception as exc:
        print("LLM not reachable.", file=sys.stderr)
        print(f"  URL: {settings.llm_base_url}", file=sys.stderr)
        print("Start llama-server first, e.g.:", file=sys.stderr)
        print(
            "  llama-server -m models/NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf "
            "--host 127.0.0.1 --port 8080 --n-gpu-layers 0 --alias nemotron",
            file=sys.stderr,
        )
        print(f"Details: {exc}", file=sys.stderr)
        sys.exit(1)

    history: list[dict[str, str]] = [{"role": "system", "content": SYSTEM}]
    print("Arif chat — type a message (Ctrl+C or 'quit' to exit)\n")

    while True:
        try:
            user = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user:
            continue
        if user.lower() in {"quit", "exit", "q"}:
            print("Bye.")
            break

        history.append({"role": "user", "content": user})
        print("Arif: ", end="", flush=True)

        try:
            stream = client.chat.completions.create(
                model=settings.llm_model,
                messages=history,
                stream=True,
                temperature=0.7,
            )
            parts: list[str] = []
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    print(delta, end="", flush=True)
                    parts.append(delta)
            print()
            history.append({"role": "assistant", "content": "".join(parts)})
        except Exception as exc:
            print(f"\nChat failed: {exc}", file=sys.stderr)
            history.pop()


if __name__ == "__main__":
    main()
