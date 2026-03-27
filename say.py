#!/usr/bin/env python3
"""TTS voice alerter for Android via ADB.

Synthesizes speech (ElevenLabs, gTTS fallback), pushes WAV to device,
and plays headlessly via app_process + AudioTrack. Works with screen
off/locked — no Activity or UI needed.

Usage:
    python3 say.py                     # says "hello micko" at 75% volume
    python3 say.py "custom message"    # says whatever you pass
    python3 say.py -v 50 "msg"         # override volume (0-100 percentage)
    python3 say.py --voice aimee "hi"  # use specific voice
    python3 say.py --list-voices       # show all 34 voices
"""

import argparse
import os
import re
import subprocess
import sys
import time
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DEX = os.path.join(PROJECT_DIR, "bin", "play.dex")
LOCAL_WAV = os.path.join(PROJECT_DIR, "log", "last_tts.wav")
LOCAL_MP3 = os.path.join(PROJECT_DIR, "log", "last_tts.mp3")
LOCAL_OGG = os.path.join(PROJECT_DIR, "log", "last_tts.ogg")
ENV_FILE = os.path.join(PROJECT_DIR, "..", ".env")

REMOTE_WAV = "/data/local/tmp/hello.wav"
REMOTE_DEX = "/data/local/tmp/play.dex"

DEFAULT_TEXT = "hello micko"
DEFAULT_VOLUME = 75  # 0-100 percentage


# ── TTS synthesis ─────────────────────────────────────────────────────

# ── Voice selector ───────────────────────────────────────────────────

VOICES = {
    # English (25)
    "roger": "CwhRBWXzGAHq8TQ4Fs17",
    "sarah": "EXAVITQu4vr4xnSDxMaL",
    "laura": "FGY2WhTYpPnrIDTdsKH5",
    "charlie": "IKne3meq5aSn9XLyUdCD",
    "george": "JBFqnCBsd6RMkjVDRZzb",
    "callum": "N2lVS1w4EtoT3dr4eOWO",
    "river": "SAz9YHcvj6GT2YYXdXww",
    "harry": "SOYHLrjzK2X1ezoPC6cr",
    "liam": "TX3LPaxmHKxFdv7VOQHJ",
    "alice": "Xb7hH8MSUJpSbSDYk0k2",
    "matilda": "XrExE9yKIg1WjnnlVkGX",
    "will": "bIHbv24MWmeRgasZH58o",
    "jessica": "cgSgspJ2msm6clMCkdW9",
    "eric": "cjVigY5qzO86Huf0OWal",
    "bella": "hpp4J3VqNfWAUOO0d1Us",
    "chris": "iP95p4xoKVk53GoZ742B",
    "brian": "nPczCjzI2devNBz1zQrb",
    "daniel": "onwK4e9ZLuTAKqWW03F9",
    "lily": "pFZP5JQG7iQjIQuC4Bku",
    "adam": "pNInz6obpgDQGcFmaJgB",
    "bill": "pqHfZKP75CvOlQylNhV4",
    "aimee": "zA6D7RyKdc2EClouEMkP",
    "blondie": "hbB2qXyS2GMyyZIZyhAH",
    "samara": "19STyYD15bswVz51nqLf",
    "fran": "TRnNlYQWHAJwo9K75wNE",
    # Russian (2)
    "mishka": "RLRdvNFwJJct2XZOgfzy",
    "marusya": "hLjwV7lYzk15SWLUmhEH",
    # French (2)
    "aurore": "ucMmKRQbfDEYyb2IIGax",
    "koraly": "sH0WdfE5fsKuM2otdQZr",
    # German (2)
    "helmut": "dFA3XRddYScy6ylAYTIO",
    "whisper_soul": "JgWQ8DAY3rJt6oPhbvxv",
    # Mandarin (1)
    "aki": "xDISamJf8LV5rG5A2te1",
    # Irish (2)
    "paddy": "1yDXKNtyiAtDljYHKmZy",
    "niamh": "1e9Gn3OQenGu4rjQ3Du1",
    # Jamaican (1)
    "nicole": "mrDMz4sYNCz18XYFpmyV",
    # Slavic/Croatian (1)
    "balkanika": "VB7D8zswiztJjyl8LI3a",
}


def synth_elevenlabs(text, voice_name="sarah"):
    """Synthesize with ElevenLabs (high quality). Returns True on success."""
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        return False

    voice_id = VOICES.get(voice_name.lower(), VOICES["sarah"])
    from elevenlabs import ElevenLabs
    client = ElevenLabs(api_key=api_key)
    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id="eleven_turbo_v2",
        output_format="mp3_44100_128",
    )
    with open(LOCAL_MP3, "wb") as f:
        for chunk in audio:
            f.write(chunk)
    _mp3_to_wav(LOCAL_MP3, LOCAL_WAV)
    print(f"  ElevenLabs OK ({voice_name})")
    return True


def synth_gtts(text):
    """Fallback: synthesize with Google TTS."""
    from gtts import gTTS
    tts = gTTS(text=text, lang="en")
    tts.save(LOCAL_MP3)
    _mp3_to_wav(LOCAL_MP3, LOCAL_WAV)
    print("  gTTS OK")
    return True


def _mp3_to_wav(mp3, wav):
    # 16kHz mono is plenty for speech TTS and ~55x smaller than 44.1kHz
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp3, "-ar", "16000", "-ac", "1",
         "-sample_fmt", "s16", wav],
        capture_output=True, timeout=15,
    )


def synthesize(text, voice="sarah"):
    """Try ElevenLabs, fall back to gTTS."""
    print(f'  Text: "{text}"')
    print(f'  Voice: {voice}')
    try:
        if synth_elevenlabs(text, voice):
            return
    except Exception as e:
        print(f"  ElevenLabs failed: {e}")
    try:
        synth_gtts(text)
    except Exception as e:
        print(f"  gTTS also failed: {e}")
        sys.exit(1)


# ── ADB helpers ───────────────────────────────────────────────────────

def adb(*args, quiet=False):
    cmd = ["adb"] + list(args)
    if not quiet:
        print(f"  $ {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if not quiet:
        for line in r.stdout.strip().splitlines()[:3]:
            print(f"    {line}")
        for line in r.stderr.strip().splitlines()[:2]:
            print(f"    [err] {line}")
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def check_device():
    rc, out, _ = adb("devices", quiet=True)
    for line in out.strip().splitlines()[1:]:
        if "\tdevice" in line:
            print(f"  Device: {line.split(chr(9))[0]}")
            return True
    print("  ERROR: No ADB device connected.")
    return False


def set_volume(level):
    """Set volume as percentage (0-100), convert to Android scale (0-15)."""
    # Clamp to 0-100
    level = max(0, min(100, level))
    # Convert percentage to Android stream volume (0-15)
    android_level = int((level / 100.0) * 15)
    adb("shell", "cmd", "media_session", "volume",
        "--stream", "3", "--set", str(android_level), quiet=True)
    print(f"  Volume: {level}% ({android_level}/15)")


def ensure_dex():
    """Push the headless AudioTrack player DEX if not already on device."""
    if not os.path.exists(LOCAL_DEX):
        print(f"  ERROR: {LOCAL_DEX} not found. Run ./build.sh first.")
        sys.exit(1)
    # Always push to keep in sync (tiny file, fast)
    adb("push", LOCAL_DEX, REMOTE_DEX, quiet=True)


def _get_wav_duration_ms(path):
    """Get WAV duration in ms from local file."""
    try:
        import wave
        with wave.open(path, "r") as w:
            return int(w.getnframes() / w.getframerate() * 1000)
    except Exception:
        return 0


def play_on_device():
    """Play the WAV file headlessly via app_process + AudioTrack."""
    adb("shell", "pkill", "-f", "app_process.*PlayAudio", quiet=True)
    time.sleep(0.2)
    # Clear old log
    adb("shell", "rm", "-f", "/data/local/tmp/play.log", quiet=True)
    adb("shell",
        f"nohup app_process -Djava.class.path={REMOTE_DEX} / PlayAudio {REMOTE_WAV}"
        f" > /data/local/tmp/play.log 2>&1 &",
        quiet=True)

    # Compute timeout: WAV duration + generous buffer for ADB/AudioTrack overhead
    dur_ms = _get_wav_duration_ms(LOCAL_WAV)
    timeout_s = max(15, (dur_ms / 1000) + 8)  # at least 15s, or duration + 8s buffer
    deadline = time.monotonic() + timeout_s

    while time.monotonic() < deadline:
        time.sleep(0.8)
        rc, out, _ = adb("shell", "cat", "/data/local/tmp/play.log", quiet=True)
        if "Done." in out:
            m = re.search(r"(\d+)ms", out)
            if m:
                print(f"  Played {int(m.group(1))}ms")
            return True
        if "ERR:" in out:
            print(f"  Playback error: {out}")
            return False

    # Timeout — but audio likely played fine, just log reading lagged
    print(f"  Poll timeout ({timeout_s:.0f}s) — audio likely played OK")
    return True


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="TTS voice alerter via ADB")
    parser.add_argument("text", nargs="*", default=[DEFAULT_TEXT],
                        help=f'Text to speak (default: "{DEFAULT_TEXT}")')
    parser.add_argument("-v", "--volume", type=int, default=DEFAULT_VOLUME,
                        help=f"Volume 0-100 percentage (default: {DEFAULT_VOLUME}%)")
    parser.add_argument("--voice", type=str, default="sarah",
                        help=f"ElevenLabs voice name (default: sarah). Use --list-voices to see all.")
    parser.add_argument("--list-voices", action="store_true",
                        help="List all available voices and exit")
    args = parser.parse_args()

    if args.list_voices:
        print("Available voices (34 total):\n")
        for name in sorted(VOICES.keys()):
            print(f"  {name}")
        sys.exit(0)

    text = " ".join(args.text)

    print("=== Voice Alerter (ADB) ===\n")

    if not check_device():
        sys.exit(1)

    print("Synthesizing...")
    synthesize(text, args.voice)

    print("Pushing...")
    adb("push", LOCAL_WAV, REMOTE_WAV)

    # Also save an Opus copy to Downloads (small, WhatsApp-shareable)
    slug = re.sub(r'[^a-z0-9]+', '-', text.lower())[:40].strip('-')
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    dl_name = f"tts-{ts}-{slug}.ogg"
    subprocess.run(
        ["ffmpeg", "-y", "-i", LOCAL_WAV, "-acodec", "libopus", "-ab", "64k", LOCAL_OGG],
        capture_output=True, timeout=15,
    )
    adb("push", LOCAL_OGG, f"/sdcard/Download/{dl_name}", quiet=True)
    adb("shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
        "-d", f"file:///sdcard/Download/{dl_name}", quiet=True)
    print(f"  Saved to Downloads: {dl_name}")

    print("Setting volume...")
    set_volume(args.volume)

    print("Ensuring player DEX...")
    ensure_dex()

    print("Playing...")
    if play_on_device():
        print("\nDone.")
    else:
        print("\nPlayback may have failed — check device.")


if __name__ == "__main__":
    main()
