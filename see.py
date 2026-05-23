"""Chat with live camera vision — ask if Arif can see you."""
from __future__ import annotations

import sys

from openai import OpenAI

from chat import SYSTEM, _check_setup, _prompt_model_choice
from llm_server import ensure_llama_server
from vision_worker import VisionWorker

VISION_ADDON = """

You have a live camera with person detection (not face recognition). Before each reply you receive a ## What I see now block with fresh detection data.

Vision rules:
- Answer "can you see me?" and similar questions ONLY from that block — never guess.
- If person_count >= 1: you can say yes naturally; mention distance if given.
- If person_count == 0: say you don't see anyone in frame right now — gently, in your own voice.
- You cannot identify who someone is, only that a person is present and roughly how far.
- Weave vision into conversation when relevant; don't recite the block like a status report unless asked."""


def _build_messages(
    history: list[dict[str, str]],
    scene: str,
) -> list[dict[str, str]]:
    """Inject current vision into the latest user turn."""
    if not history:
        return history
    out = history.copy()
    if out[-1]["role"] != "user":
        return out
    user_text = out[-1]["content"]
    out[-1] = {
        "role": "user",
        "content": f"## What I see now\n{scene}\n\n## Message\n{user_text}",
    }
    return out


def main() -> None:
    _check_setup()
    settings, _ = _prompt_model_choice()
    ensure_llama_server(settings)

    print("Starting camera vision …", file=sys.stderr)
    vision = VisionWorker(settings)
    try:
        vision.start()
    except RuntimeError as exc:
        print(f"Vision failed: {exc}", file=sys.stderr)
        sys.exit(1)

    snap = vision.snapshot()
    print(f"Vision online — {snap.to_context()}", file=sys.stderr)

    client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)
    system = SYSTEM + VISION_ADDON
    history: list[dict[str, str]] = [{"role": "system", "content": system}]
    print("Arif see — camera + chat. Ask if I can see you. (quit / Ctrl+C to leave)\n")

    try:
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
            scene = vision.snapshot().to_context()
            messages = _build_messages(history, scene)
            print("Arif: ", end="", flush=True)

            try:
                stream = client.chat.completions.create(
                    model=settings.llm_model,
                    messages=messages,
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
    finally:
        vision.stop()


if __name__ == "__main__":
    main()
