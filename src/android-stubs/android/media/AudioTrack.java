package android.media;

/** Minimal stub — real implementation lives on the Android device. */
public class AudioTrack {
    public static final int MODE_STATIC = 0;
    public static final int MODE_STREAM = 1;

    public AudioTrack(AudioAttributes a, AudioFormat f, int buf, int mode, int sess) {}
    public static int getMinBufferSize(int sr, int ch, int enc) { return 0; }
    public int getState() { return 0; }
    public int write(byte[] d, int off, int sz) { return 0; }
    public void play() {}
    public void stop() {}
    public void release() {}
}
