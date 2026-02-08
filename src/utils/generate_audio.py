"""
Generate pronunciation audio (.wav) for every label using espeak-ng.

espeak-ng supports Arabic natively (language code "ar").
Audio files are written to  data/audio/{label_id}.wav
and only regenerated when the file does not already exist.

Can be used standalone:
    python -m src.utils.generate_audio

Or called programmatically from API startup:
    from src.utils.generate_audio import generate_all_audio
    generate_all_audio()
"""

import json
import os
import subprocess
import shutil
from pathlib import Path

# Defaults – callers can override via arguments
_DEFAULT_LABEL_MAP = os.path.join("outputs", "index", "label2text.json")
_DEFAULT_AUDIO_DIR = os.path.join("data", "audio")


def _espeak_available() -> bool:
    """Check whether espeak-ng is installed on this system."""
    return shutil.which("espeak-ng") is not None


def generate_wav(text: str, output_path: str, lang: str = "ar", speed: int = 130) -> bool:
    """
    Generate a single .wav file using espeak-ng.

    Args:
        text:        The word / phrase to speak.
        output_path: Where to write the .wav file.
        lang:        Language code (default "ar" for Arabic).
        speed:       Words-per-minute (lower = slower / clearer).

    Returns:
        True if the file was created successfully, False otherwise.
    """
    try:
        subprocess.run(
            [
                "espeak-ng",
                "-v", lang,
                "-s", str(speed),
                "-w", output_path,
                "--", text,
            ],
            check=True,
            capture_output=True,
            timeout=10,
        )
        return os.path.isfile(output_path) and os.path.getsize(output_path) > 0
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        print(f"  [espeak-ng] failed for '{text}': {exc}")
        return False


def generate_all_audio(
    label_map_path: str = _DEFAULT_LABEL_MAP,
    audio_dir: str = _DEFAULT_AUDIO_DIR,
    force: bool = False,
) -> dict:
    """
    Generate .wav files for every label in the label map.

    Args:
        label_map_path: Path to label2text.json.
        audio_dir:      Directory to write .wav files into.
        force:          If True, regenerate even if the file already exists.

    Returns:
        dict with keys 'generated', 'skipped', 'failed' (counts).
    """
    if not _espeak_available():
        print("[generate_audio] espeak-ng not found – skipping audio generation.")
        return {"generated": 0, "skipped": 0, "failed": 0}

    if not os.path.isfile(label_map_path):
        print(f"[generate_audio] label map not found at {label_map_path} – skipping.")
        return {"generated": 0, "skipped": 0, "failed": 0}

    with open(label_map_path, "r", encoding="utf-8") as f:
        label2text: dict = json.load(f)

    os.makedirs(audio_dir, exist_ok=True)

    stats = {"generated": 0, "skipped": 0, "failed": 0}

    for label_id, text in sorted(label2text.items(), key=lambda x: int(x[0])):
        wav_path = os.path.join(audio_dir, f"{label_id}.wav")

        if not force and os.path.isfile(wav_path) and os.path.getsize(wav_path) > 0:
            stats["skipped"] += 1
            continue

        ok = generate_wav(text, wav_path)
        if ok:
            stats["generated"] += 1
        else:
            stats["failed"] += 1

    total = sum(stats.values())
    print(
        f"[generate_audio] Done – {stats['generated']} generated, "
        f"{stats['skipped']} skipped (already exist), "
        f"{stats['failed']} failed, {total} total labels."
    )
    return stats


# Allow running as: python -m src.utils.generate_audio
if __name__ == "__main__":
    generate_all_audio()
