package android.media;

/** Minimal stub — real implementation lives on the Android device. */
public class AudioFormat {
    public static final int ENCODING_PCM_16BIT = 2;
    public static final int ENCODING_PCM_8BIT = 3;
    public static final int CHANNEL_OUT_MONO = 4;
    public static final int CHANNEL_OUT_STEREO = 12;

    public static class Builder {
        public Builder setEncoding(int e) { return this; }
        public Builder setSampleRate(int r) { return this; }
        public Builder setChannelMask(int c) { return this; }
        public AudioFormat build() { return new AudioFormat(); }
    }
}
