"""Tiny eval for team memory: does ask_team cite the note/source a human says it should?

data/eval.json: [{"question": "...", "expect": "substring that must appear in a cited note, title or URL"}]
Run: python scripts/eval_ask.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crew import config  # noqa: E402
from crew.memory import ask_team  # noqa: E402


def main() -> None:
    cases = json.loads((config.DATA_DIR / "eval.json").read_text())
    hits = 0
    for case in cases:
        result = ask_team(case["question"])
        blob = json.dumps(result.get("citations", [])).lower()
        ok = case["expect"].lower() in blob
        hits += ok
        print(f"{'PASS' if ok else 'FAIL'}  {case['question']}")
        if not ok:
            print(f"      expected '{case['expect']}', got: {result.get('answer', '')[:160]}")
    print(f"\n{hits}/{len(cases)} answers cited the right evidence")


if __name__ == "__main__":
    main()
