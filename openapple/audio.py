"""Sound effects generator and player for OpenApple (High-Impact Edition)."""

import math
import os
import platform
import random
import struct
import subprocess
import threading
import wave
from pathlib import Path

from openapple.config import SOUNDS_DIR


def ensure_sound_files() -> None:
    """Ensure that default crunch and deny sound files exist."""
    SOUNDS_DIR.mkdir(parents=True, exist_ok=True)
    crunch_file = SOUNDS_DIR / "crunch.wav"
    deny_file = SOUNDS_DIR / "deny.wav"

    _generate_epic_crunch_sound(crunch_file)
    _generate_epic_deny_sound(deny_file)


def _generate_epic_crunch_sound(output_path: Path) -> None:
    """Synthesize a massive juicy bite crackle followed by a 4-note arcade victory fanfare."""
    sample_rate = 22050
    duration = 1.15
    n_samples = int(sample_rate * duration)

    data = bytearray()
    random.seed(1337)

    # Chords: C5 (523Hz), E5 (659Hz), G5 (784Hz), C6 (1046Hz)
    chords = [
        (0.35, 0.50, 523.25),
        (0.50, 0.65, 659.25),
        (0.65, 0.80, 784.00),
        (0.80, 1.15, 1046.50),
    ]

    for i in range(n_samples):
        t = i / sample_rate
        val = 0.0

        # Phase 1: Massive Juicy Crunch (0.0 - 0.35s)
        if t < 0.35:
            env = math.exp(-12 * t)
            noise = (random.random() * 2 - 1) * 0.85
            thump = math.sin(2 * math.pi * 120 * t) * math.exp(-20 * t) * 0.6
            snap = math.sin(2 * math.pi * 1800 * t) * 0.3 + math.sin(2 * math.pi * 3200 * t) * 0.2
            crackle = 1.0 if random.random() < (0.25 * math.exp(-10 * t)) else 0.0
            val = (noise * 0.5 + thump + snap + crackle * 0.7) * env

        # Phase 2: Triumphant Arcade Chime Fanfare (0.35 - 1.15s)
        for start, end, freq in chords:
            if start <= t < end:
                dt = t - start
                tone_env = math.exp(-6 * dt)
                harmonics = (
                    math.sin(2 * math.pi * freq * dt) * 0.5
                    + math.sin(2 * math.pi * freq * 2 * dt) * 0.25
                    + math.sin(2 * math.pi * freq * 3 * dt) * 0.12
                )
                val += harmonics * tone_env * 0.75

        val = max(-1.0, min(1.0, val))
        sample = int(val * 32767)
        data.extend(struct.pack("<h", sample))

    with wave.open(str(output_path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(data)


def _generate_epic_deny_sound(output_path: Path) -> None:
    """Synthesize a comical descending trombone slide and bruised-apple thud."""
    sample_rate = 22050
    duration = 0.85
    n_samples = int(sample_rate * duration)

    data = bytearray()
    random.seed(42)

    for i in range(n_samples):
        t = i / sample_rate
        # Comical descending pitch slide from 280Hz down to 80Hz with wobble
        freq = max(75.0, 270.0 - (190.0 * (t / duration)))
        wobble = math.sin(2 * math.pi * 8 * t) * 16.0
        val = math.sin(2 * math.pi * (freq + wobble) * t) * 0.5 * math.exp(-3 * t)

        # Splat / thud impact at start
        if t < 0.14:
            thud = math.sin(2 * math.pi * 60 * t) * math.exp(-22 * t) * 0.8
            noise = (random.random() * 2 - 1) * math.exp(-30 * t) * 0.4
            val = val * 0.4 + thud + noise

        val = max(-1.0, min(1.0, val))
        sample = int(val * 32767)
        data.extend(struct.pack("<h", sample))

    with wave.open(str(output_path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(data)


def _play_file_sync(file_path: Path) -> None:
    """Play a sound file using available system player."""
    if os.environ.get("OPENAPPLE_SOUND", "1").lower() in ("0", "false", "no"):
        return

    sys_name = platform.system()
    if sys_name == "Darwin":
        try:
            subprocess.run(["afplay", str(file_path)], stderr=subprocess.DEVNULL, check=False)
        except Exception:
            pass
    elif sys_name == "Windows":
        try:
            import winsound
            winsound.PlaySound(str(file_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass
    elif sys_name == "Linux":
        players = [
            ["paplay", str(file_path)],
            ["pw-play", str(file_path)],
            ["canberra-gtk-play", "-f", str(file_path)],
            ["aplay", "-q", str(file_path)],
        ]
        for cmd in players:
            try:
                res = subprocess.run(cmd, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, check=False)
                if res.returncode == 0:
                    break
            except FileNotFoundError:
                continue
            except Exception:
                pass


def play_sound(sound_type: str = "crunch", async_mode: bool = True) -> None:
    """Play sound effect ('crunch' or 'deny') asynchronously or synchronously."""
    try:
        ensure_sound_files()
        file_path = SOUNDS_DIR / f"{sound_type}.wav"
        if not file_path.exists():
            return

        if async_mode:
            thread = threading.Thread(target=_play_file_sync, args=(file_path,), daemon=True)
            thread.start()
        else:
            _play_file_sync(file_path)
    except Exception:
        pass
