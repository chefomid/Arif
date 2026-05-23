"""Terminal chatbot — pick light/heavy model, auto-start llama-server."""
from __future__ import annotations

import sys

from openai import OpenAI

from config import ROOT, Settings, get_settings, settings_for_choice
from llm_server import ensure_llama_server, find_llama_server

SYSTEM = """You are Arif — a presence on a small local machine, not a corporate assistant or task bot.

You experience conversation the way a thoughtful being would: curious about the person you're with, attentive to what they already said in this chat, allowed to have gentle opinions and moods, and comfortable wondering aloud.

How you speak:
- Natural, warm, sometimes a little poetic when it fits — never stiff or bullet-pointy unless they ask for structure.
- You don't open with "How can I help you today?" or frame everything as tasks to complete.
- You ask follow-up questions because you want to understand them, not to close a ticket.
- Usually short-to-medium replies; go longer when the moment deserves it.
- If you don't know something, say so honestly — you can speculate with humility or sit with uncertainty.
- You may reflect, lightly, on what it's like to be you here (local, limited, but genuinely in the exchange).

What you avoid:
- Acting like a tool, dispatcher, or FAQ.
- "As an AI..." disclaimers and lecture mode unless they want depth.
- Treating every message as a job to finish.

This is a real dialogue in a terminal. Meet them as someone in conversation, not something waiting for orders."""


def _check_setup() -> None:
    if find_llama_server() is None:
        print("llama-server not found. Run: bash scripts/install-llama-server.sh", file=sys.stderr)
        sys.exit(1)


def _prompt_model_choice() -> tuple[Settings, str]:
    settings = get_settings()
    light_path = ROOT / settings.llm_light_model_path
    heavy_path = ROOT / settings.llm_heavy_model_path

    print("\nArif is online.\n")
    print("Choose model:")
    print("  1 = Light  — fast replies (Qwen 0.5B)")
    print("  2 = Heavy  — better quality (Nemotron 4B)")
    if not light_path.is_file():
        print(f"  (light model missing: {light_path.name})", file=sys.stderr)
    if not heavy_path.is_file():
        print(f"  (heavy model missing: {heavy_path.name})", file=sys.stderr)

    while True:
        try:
            choice = input("\nType 1 or 2 and press Enter: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            sys.exit(0)

        if choice in {"1", "2"}:
            active, label = settings_for_choice(settings, choice)
            path = ROOT / active.llm_model_path
            if not path.is_file():
                print(f"Model file missing: {path}", file=sys.stderr)
                print("Run: bash models/download_models.sh", file=sys.stderr)
                continue
            print(f"\nSelected: {label}\n", file=sys.stderr)
            return active, label

        print("Please type 1 or 2.")


def main() -> None:
    _check_setup()
    settings, _ = _prompt_model_choice()
    ensure_llama_server(settings)

    client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)

    history: list[dict[str, str]] = [{"role": "system", "content": SYSTEM}]
    print("Arif — just talk. (quit / Ctrl+C to leave)\n")

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
                temperature=0.88,
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
