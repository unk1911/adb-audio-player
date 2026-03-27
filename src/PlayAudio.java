import android.media.AudioAttributes;
import android.media.AudioFormat;
import android.media.AudioTrack;
import java.io.DataInputStream;
import java.io.FileInputStream;

/**
 * Headless WAV player for Android. Runs via app_process without any
 * Activity, Context, or UI — works with screen off/locked.
 *
 * Parses WAV header, writes PCM data to AudioTrack (MODE_STATIC),
 * waits for playback to finish, then exits.
 *
 * Note: MediaCodec (MP3 decoding) is not available to the shell UID
 * on Samsung devices (SIGKILL on codec.configure). So we receive
 * pre-converted WAV from the host. 16kHz mono is used to keep
 * bandwidth low while maintaining speech clarity.
 *
 * Usage on device:
 *   app_process -Djava.class.path=/data/local/tmp/play.dex / PlayAudio /data/local/tmp/hello.wav
 */
public class PlayAudio {

    public static void main(String[] args) {
        try {
            String path = args[0];
            FileInputStream fis = new FileInputStream(path);
            DataInputStream dis = new DataInputStream(fis);

            // Parse WAV header
            dis.skipBytes(4);                                        // "RIFF"
            dis.readInt();                                           // fileSize
            dis.skipBytes(4);                                        // "WAVE"
            dis.skipBytes(4);                                        // "fmt "
            int fmtSize = Integer.reverseBytes(dis.readInt());
            dis.readShort();                                         // audioFormat
            short ch = (short) Short.reverseBytes(dis.readShort());
            int sr = Integer.reverseBytes(dis.readInt());
            int br = Integer.reverseBytes(dis.readInt());
            dis.skipBytes(2);                                        // blockAlign
            dis.readShort();                                         // bitsPerSample
            if (fmtSize > 16) dis.skipBytes(fmtSize - 16);

            // Find "data" chunk
            while (true) {
                byte[] id = new byte[4];
                dis.readFully(id);
                int sz = Integer.reverseBytes(dis.readInt());

                if (new String(id).equals("data")) {
                    byte[] pcm = new byte[sz];
                    dis.readFully(pcm);
                    fis.close();

                    long durMs = sz * 1000L / br;
                    System.out.println(sr + "Hz " + ch + "ch 16bit " + durMs + "ms");

                    int chMask = (ch == 1)
                        ? AudioFormat.CHANNEL_OUT_MONO
                        : AudioFormat.CHANNEL_OUT_STEREO;

                    AudioTrack t = new AudioTrack(
                        new AudioAttributes.Builder()
                            .setUsage(AudioAttributes.USAGE_MEDIA)
                            .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                            .build(),
                        new AudioFormat.Builder()
                            .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                            .setSampleRate(sr)
                            .setChannelMask(chMask)
                            .build(),
                        pcm.length,
                        AudioTrack.MODE_STATIC,
                        0);

                    t.write(pcm, 0, pcm.length);
                    t.play();
                    System.out.println("Playing...");
                    Thread.sleep(durMs + 500);
                    t.stop();
                    t.release();
                    System.out.println("Done.");
                    System.exit(0);
                }
                dis.skipBytes(sz);
            }
        } catch (Exception e) {
            System.err.println("ERR: " + e);
            e.printStackTrace();
            System.exit(1);
        }
    }
}
