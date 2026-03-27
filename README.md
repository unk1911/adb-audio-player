# adb-audio-player

Headless TTS voice alerter for Android via ADB. Synthesizes speech on a remote server, pushes audio to an Android phone over ADB, and plays it through the speaker — **works with screen off and phone locked**. No Activity, Context, or UI needed.

## Architecture

```
┌─────────────────────────────────────┐       ADB over Tailscale       ┌──────────────────────────┐
│            Linux Server             │ ────────────────────────────▶   │    Android Phone          │
│                                     │                                │    (Galaxy S24 Ultra)     │
│  say.py                             │    1. adb push hello.wav       │                           │
│    ├─ ElevenLabs API → MP3          │    2. adb push play.dex        │  /data/local/tmp/         │
│    ├─ ffmpeg MP3 → WAV (16kHz)      │    3. adb shell app_process    │    ├─ hello.wav           │
│    ├─ ffmpeg WAV → OGG (Opus)       │       → PlayAudio              │    ├─ play.dex            │
│    └─ adb push + play               │    4. adb push .ogg            │    └─ play.log            │
│                                     │       → /sdcard/Download/      │                           │
│  src/PlayAudio.java                 │                                │  AudioTrack API           │
│    └─ compiled → bin/play.dex       │                                │    └─ PCM → speaker       │
└─────────────────────────────────────┘                                └──────────────────────────┘
```

### Why this works screen-off/locked

Android's `app_process` binary runs Java/DEX code from the ADB shell with access to the full Android framework — but without any Activity, Context, or UI. The key insight is that **AudioTrack** (unlike MediaPlayer) doesn't require a Context. It writes raw PCM samples directly to the audio hardware.

### Why WAV instead of MP3

Samsung devices kill `MediaCodec.configure()` with SIGKILL when called from the shell UID (SELinux policy). So MP3 decoding on-device is impossible from ADB. Instead, we decode on the server and send pre-converted WAV. Using 16kHz mono keeps the file small (~30-60KB for typical speech) while maintaining clarity.

### Why not MediaPlayer?

`MediaPlayer.setDataSource()` calls `FileUtils.convertToModernFd()` internally, which requires a Context — crashes with NullPointerException under `app_process`. AudioTrack bypasses this entirely by accepting raw PCM bytes.

## Files

```
say.py                     Main script — TTS + ADB push + playback orchestration
src/PlayAudio.java         Headless AudioTrack WAV player (runs on device via app_process)
src/android-stubs/         Minimal API stubs for javac (real impls live on device)
bin/play.dex               Compiled DEX (push to /data/local/tmp/play.dex)
build.sh                   Compiles Java → DEX (requires javac + d8)
log/                       Last synthesized MP3/WAV/OGG (gitignored)
```

## Setup

### Prerequisites

- **ADB** connected to device (USB or wireless/Tailscale)
- **JDK 11+** and **Android build-tools** (d8) for compiling the DEX
- **ffmpeg** for audio conversion
- **Python 3** with `elevenlabs` and `python-dotenv` packages
- **ElevenLabs API key** in `.env` (falls back to gTTS if unavailable)

### Build the DEX (one-time)

```bash
# Set D8_JAR if not at default location
export D8_JAR=/path/to/android-build-tools/lib/d8.jar

./build.sh
# Output: bin/play.dex
```

### Environment

Create a `.env` file in the parent directory:

```
ELEVENLABS_API_KEY=sk_your_key_here
```

## Usage

```bash
# Default: says "hello micko" at 75% volume with Sarah voice
python3 say.py

# Custom message
python3 say.py "wake up, breakfast is ready"

# Quiet (for night use)
python3 say.py -v 10 "goodnight"

# Full volume
python3 say.py -v 100 "FIRE ALARM"

# Pick a voice
python3 say.py --voice aimee "hey there"

# List all 34 available voices
python3 say.py --list-voices
```

### Volume

Volume is specified as a percentage (0-100), mapped to Android's 0-15 media stream scale:

| Flag | Percentage | Android level | Use case |
|------|-----------|---------------|----------|
| `-v 5` | 5% | 0/15 | Barely audible |
| `-v 25` | 25% | 3/15 | Quiet background |
| `-v 50` | 50% | 7/15 | Normal |
| `-v 75` | 75% | 11/15 | Default — clear and present |
| `-v 100` | 100% | 15/15 | Maximum |

### Voices

34 voices across 8 languages. English voices (sarah, roger, aimee, charlie, etc.) work best. Foreign language voices (Russian, Mandarin, etc.) use English-trained models so results vary.

### Downloads folder

Every TTS clip is automatically saved to the phone's `/sdcard/Download/` as an OGG/Opus file (e.g. `tts-20260327-171151-hey-there.ogg`). These are small, visible in My Files, and shareable via WhatsApp.

## How it works (step by step)

1. **Synthesize** — `say.py` calls ElevenLabs API (or gTTS fallback) to generate MP3
2. **Convert** — ffmpeg converts MP3 → 16kHz mono WAV (for AudioTrack) and WAV → OGG/Opus (for Downloads)
3. **Push** — `adb push` sends WAV to `/data/local/tmp/hello.wav` and OGG to `/sdcard/Download/`
4. **Volume** — `adb shell cmd media_session volume` sets media stream level
5. **Play** — `adb shell nohup app_process -Djava.class.path=/data/local/tmp/play.dex / PlayAudio /data/local/tmp/hello.wav` launches the headless player
6. **Monitor** — `say.py` polls `/data/local/tmp/play.log` until it sees "Done." or times out
7. **Cleanup** — AudioTrack releases, `app_process` exits

## Cron / automation

Works great as a scheduled job. Example: hourly news headlines read aloud by Aimee voice.

```bash
python3 say.py --voice aimee "Here are the latest headlines: ..."
```
