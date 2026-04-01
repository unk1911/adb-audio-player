#!/usr/bin/env bash
# Build the headless Android AudioTrack player DEX.
#
# Requirements: javac (JDK 11+), d8 (Android build-tools)
#
# Output: bin/play.dex  (push to /data/local/tmp/play.dex on device)

set -euo pipefail
cd "$(dirname "$0")"

D8_JAR="${D8_JAR:-/tmp/android-14/lib/d8.jar}"
BUILD_DIR="build"
BIN_DIR="bin"
SRC="src/PlayAudio.java"
STUBS="src/android-stubs"

echo "=== Building PlayAudio DEX ==="

# Clean
rm -rf "$BUILD_DIR"/*.class
mkdir -p "$BUILD_DIR" "$BIN_DIR"

# Compile Java → .class (stubs provide Android API signatures)
echo "Compiling..."
javac -source 11 -target 11 \
    -d "$BUILD_DIR" \
    "$STUBS"/android/media/*.java \
    "$SRC" 2>&1 | grep -v "^warning:" || true

# Convert .class → .dex (include inner classes)
echo "Dexing..."
java -cp "$D8_JAR" com.android.tools.r8.D8 \
    --output "$BUILD_DIR" \
    "$BUILD_DIR"/PlayAudio*.class 2>&1 | grep -v "^Warning" || true

# Copy to bin/
cp "$BUILD_DIR/classes.dex" "$BIN_DIR/play.dex"
echo "Built: $BIN_DIR/play.dex ($(wc -c < "$BIN_DIR/play.dex") bytes)"

# --- StreamAudio (MODE_STREAM, reads PCM from stdin) ---
echo ""
echo "=== Building StreamAudio DEX ==="

echo "Compiling..."
javac -source 11 -target 11 \
    -d "$BUILD_DIR" \
    "$STUBS"/android/media/*.java \
    src/StreamAudio.java 2>&1 | grep -v "^warning:" || true

echo "Dexing..."
mkdir -p "$BUILD_DIR/stream"
java -cp "$D8_JAR" com.android.tools.r8.D8 \
    --output "$BUILD_DIR/stream" \
    "$BUILD_DIR"/StreamAudio*.class 2>&1 | grep -v "^Warning" || true

cp "$BUILD_DIR/stream/classes.dex" "$BIN_DIR/stream.dex"
echo "Built: $BIN_DIR/stream.dex ($(wc -c < "$BIN_DIR/stream.dex") bytes)"
