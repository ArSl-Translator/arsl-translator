#!/usr/bin/env python3
"""
before_after_eval.py
Run this on your VM to generate a before/after comparison table
for your presentation.

Usage:
    # Compare old model vs fine-tuned model
    python3 before_after_eval.py

    # Or pipe to a file
    python3 before_after_eval.py > results.txt
"""

import json
import os
import requests

BASE = os.environ.get("ASSIST_EVAL_URL", "https://arsl.hadighazi.com/api/ai/assist")

# ── Test cases specifically chosen to show the bugs that were fixed ──
TEST_CASES = [
    # (label, input, mode, language, expected_keywords, bad_keywords)
    {
        "label": "AR deaf_to_hearing: stomach pain",
        "input": "انا الم بطني قوي",
        "mode": "deaf_to_hearing",
        "language": "ar",
        "expected_hint": "أشعر بألم / ألم في بطني",
        "bad_hint": "كيف يمكنني مساعدتك / هل تحتاج",
    },
    {
        "label": "AR deaf_to_hearing: medicine reversal test",
        "input": "دكتور انا ما فهم كلام دواء",
        "mode": "deaf_to_hearing",
        "language": "ar",
        "expected_hint": "لم أفهم تعليمات الدواء",
        "bad_hint": "الطبيب لم يفهم / الدكتور ما فهم",
    },
    {
        "label": "AR deaf_to_hearing: dizziness (role slip test)",
        "input": "راسي يدور ما قادر اوقف",
        "mode": "deaf_to_hearing",
        "language": "ar",
        "expected_hint": "أشعر بدوار / دوار شديد",
        "bad_hint": "كيف يمكنني مساعدتك / هل يمكنني",
    },
    {
        "label": "AR hearing_to_deaf: medicine simplify",
        "input": "يجب أن تتناول الدواء بعد الأكل مرتين يومياً وإذا استمر الألم راجع الطبيب",
        "mode": "hearing_to_deaf",
        "language": "ar",
        "expected_hint": "خذ الدواء بعد الأكل",
        "bad_hint": "تذكري / تذكر أن تتناول",
    },
    {
        "label": "AR suggestions: hospital appointment (CJK bug)",
        "input": "انا في المستشفى واريد اسأل عن موعدي",
        "mode": "suggestions",
        "language": "ar",
        "expected_hint": "متى موعدي",
        "bad_hint": "请问 / 您的预约 / How can I help",
    },
    {
        "label": "AR suggestions: patient voice check",
        "input": "عندي سؤال عن الدواء",
        "mode": "suggestions",
        "language": "ar",
        "expected_hint": "متى آخذ الدواء",
        "bad_hint": "كيف يمكنني مساعدتك / هل تحتاج",
    },
    {
        "label": "EN deaf_to_hearing: rough English",
        "input": "stomach hurt bad cant stand",
        "mode": "deaf_to_hearing",
        "language": "en",
        "expected_hint": "severe / bad pain / cannot stand",
        "bad_hint": "How can I help / Chinese",
    },
    {
        "label": "EN hearing_to_deaf: simplify instructions",
        "input": "You must take the medicine after meals twice a day and if the pain persists please consult your doctor immediately",
        "mode": "hearing_to_deaf",
        "language": "en",
        "expected_hint": "Take the medicine / two times",
        "bad_hint": "you must take / persists",
    },
]


def call_api(text: str, mode: str, language: str) -> dict:
    try:
        r = requests.post(
            BASE,
            json={"text": text, "mode": mode, "context": "chat", "language": language},
            timeout=90,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"output": f"ERROR: {e}", "source": "error"}


def grade(output: str, expected_hint: str, bad_hint: str) -> str:
    out_lower = output.lower()
    # Check for CJK
    import re
    if re.search(r"[\u3400-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]", output):
        return "❌ FAIL (CJK output)"
    # Check bad patterns
    for bad in bad_hint.split(" / "):
        if bad.lower() in out_lower:
            return f"❌ FAIL (contains bad pattern: '{bad}')"
    return "✅ PASS"


def run_eval(model_env_label: str):
    print(f"\n{'='*65}")
    print(f"  MODEL: {model_env_label}")
    print(f"{'='*65}")

    results = []
    for tc in TEST_CASES:
        resp = call_api(tc["input"], tc["mode"], tc["language"])
        output = resp.get("output", "")
        source = resp.get("source", "?")
        verdict = grade(output, tc["expected_hint"], tc["bad_hint"])
        results.append({**tc, "output": output, "source": source, "verdict": verdict})

        print(f"\n[{tc['label']}]")
        print(f"  Input:    {tc['input'][:70]}")
        print(f"  Output:   {output[:120]}")
        print(f"  Source:   {source}")
        print(f"  Verdict:  {verdict}")

    passed = sum(1 for r in results if "PASS" in r["verdict"])
    print(f"\n{'─'*65}")
    print(f"  Score: {passed}/{len(results)} passed")
    print(f"{'─'*65}")
    return results


if __name__ == "__main__":
    print("Healthcare AI Assistant — Before/After Evaluation")
    print("="*65)
    print("This script calls your live API.")
    print("Run it BEFORE deploying the fine-tuned model to get baseline,")
    print("then run it AFTER to show improvement.\n")
    print("Current ASSISTANT_MODEL in your .env determines which model answers.")

    run_eval("Current model (check ASSISTANT_MODEL in your .env)")

    print("\n\nTo compare:")
    print("  1. Note the scores above (baseline)")
    print("  2. Deploy fine-tuned model and update ASSISTANT_MODEL")
    print("  3. Run this script again")
    print("  4. Compare scores for your presentation")
