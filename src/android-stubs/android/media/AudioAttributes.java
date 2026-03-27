package android.media;

/** Minimal stub — real implementation lives on the Android device. */
public class AudioAttributes {
    public static final int USAGE_MEDIA = 1;
    public static final int CONTENT_TYPE_MUSIC = 2;

    public static class Builder {
        public Builder setUsage(int u) { return this; }
        public Builder setContentType(int c) { return this; }
        public AudioAttributes build() { return new AudioAttributes(); }
    }
}
