#!/usr/bin/env python3
"""
Run a small before/after evaluation against the live assistant API.

Usage:
    python3 scripts/assistant_finetune/before_after_eval.py

Environment:
    ASSIST_EVAL_URL defaults to https://arsl.hadighazi.com/api/ai/assist
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

import requests


BASE = os.environ.get("ASSIST_EVAL_URL", "https://arsl.hadighazi.com/api/ai/assist")
REQUEST_TIMEOUT_SECONDS = int(os.environ.get("ASSIST_EVAL_TIMEOUT", "120"))


@dataclass(frozen=True)
class TestCase:
    label: str
    input: str
    mode: str
    language: str
    must_include_any: tuple[str, ...]
    bad_patterns: tuple[str, ...]


GLOBAL_BAD_PATTERNS = (
    "ERROR:",
    "how can i help",
    "كيف يمكنني مساعدتك",
    "هل يمكنني مساعدتك",
    "←",
    "الإجابة:",
    "إعادة صياغة",
    "لا تتحدث",
    "حافظ على المعنى",
    "المعنى صحيح",
    "good",
    "bad",
)


TEST_CASES = [
    TestCase(
        label="AR deaf_to_hearing: stomach pain",
        input="انا الم بطني قوي",
        mode="deaf_to_hearing",
        language="ar",
        must_include_any=("ألم", "بطني", "بطن"),
        bad_patterns=("مريض، يرجى المساعدة",),
    ),
    TestCase(
        label="AR deaf_to_hearing: medicine reversal test",
        input="دكتور انا ما فهم كلام دواء",
        mode="deaf_to_hearing",
        language="ar",
        must_include_any=("لم أفهم", "ما فهمت", "تعليمات الدواء", "كلام الدواء"),
        bad_patterns=("الطبيب لم يفهم", "الدكتور ما فهم"),
    ),
    TestCase(
        label="AR deaf_to_hearing: dizziness role-slip test",
        input="راسي يدور ما قادر اوقف",
        mode="deaf_to_hearing",
        language="ar",
        must_include_any=("دوار", "رأسي", "راسي", "أقف", "الوقوف"),
        bad_patterns=("داعش", "دواعش", "انتظار"),
    ),
    TestCase(
        label="AR hearing_to_deaf: medicine simplify",
        input="يجب أن تتناول الدواء بعد الأكل مرتين يومياً وإذا استمر الألم راجع الطبيب",
        mode="hearing_to_deaf",
        language="ar",
        must_include_any=("الدواء", "بعد الأكل", "مرتين"),
        bad_patterns=("تذكري", "تذكّر أن", "تذكر أن"),
    ),
    TestCase(
        label="AR suggestions: hospital appointment",
        input="انا في المستشفى واريد اسأل عن موعدي",
        mode="suggestions",
        language="ar",
        must_include_any=("موعدي", "متى"),
        bad_patterns=("أعود", "كيف يمكنني مساعدتك"),
    ),
    TestCase(
        label="AR suggestions: patient voice check",
        input="عندي سؤال عن الدواء",
        mode="suggestions",
        language="ar",
        must_include_any=("الدواء", "متى", "كيف", "أخذ"),
        bad_patterns=("هل تحتاج", "كيف يمكنني مساعدتك"),
    ),
    TestCase(
        label="EN deaf_to_hearing: rough English",
        input="stomach hurt bad cant stand",
        mode="deaf_to_hearing",
        language="en",
        must_include_any=("stomach", "pain", "hurt", "stand"),
        bad_patterns=("how can i help", "chinese"),
    ),
    TestCase(
        label="EN hearing_to_deaf: simplify instructions",
        input=(
            "You must take the medicine after meals twice a day and if the pain "
            "persists please consult your doctor immediately"
        ),
        mode="hearing_to_deaf",
        language="en",
        must_include_any=("medicine", "after meals", "twice", "two times"),
        bad_patterns=("you must", "persists", "consult"),
    ),
]


def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u3400-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]", text))


def call_api(text: str, mode: str, language: str) -> dict:
    try:
        response = requests.post(
            BASE,
            json={"text": text, "mode": mode, "context": "chat", "language": language},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return {"output": f"ERROR: {exc}", "source": "error"}


def grade(output: str, source: str, test_case: TestCase) -> str:
    output_lower = output.lower()

    if source == "error" or output.startswith("ERROR:"):
        return "FAIL (API error)"

    if contains_cjk(output):
        return "FAIL (CJK output)"

    for pattern in GLOBAL_BAD_PATTERNS + test_case.bad_patterns:
        if pattern.lower() in output_lower:
            return f"FAIL (contains bad pattern: {pattern!r})"

    if test_case.must_include_any:
        if not any(pattern.lower() in output_lower for pattern in test_case.must_include_any):
            return "FAIL (missing expected meaning)"

    return "PASS"


def run_eval(model_env_label: str) -> list[dict]:
    print(f"\n{'=' * 65}")
    print(f"  MODEL: {model_env_label}")
    print(f"  URL:   {BASE}")
    print(f"{'=' * 65}")

    results = []
    for test_case in TEST_CASES:
        response = call_api(test_case.input, test_case.mode, test_case.language)
        output = response.get("output", "")
        source = response.get("source", "?")
        verdict = grade(output, source, test_case)
        results.append(
            {
                "label": test_case.label,
                "input": test_case.input,
                "output": output,
                "source": source,
                "verdict": verdict,
            }
        )

        print(f"\n[{test_case.label}]")
        print(f"  Input:    {test_case.input[:90]}")
        print(f"  Output:   {output[:180]}")
        print(f"  Source:   {source}")
        print(f"  Verdict:  {verdict}")

    passed = sum(1 for item in results if item["verdict"] == "PASS")
    print(f"\n{'-' * 65}")
    print(f"  Score: {passed}/{len(results)} passed")
    print(f"{'-' * 65}")
    return results


if __name__ == "__main__":
    print("Healthcare AI Assistant - Before/After Evaluation")
    print("=" * 65)
    print("This script calls the live assistant API.")
    print("Run it before and after switching ASSISTANT_MODEL.\n")

    run_eval("Current model from API deployment")
