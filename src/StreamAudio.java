import android.media.AudioAttributes;
import android.media.AudioFormat;
import android.media.AudioTrack;
import java.io.File;

/**
 * Headless streaming PCM player for Android. Reads raw PCM from stdin
 * and plays it via AudioTrack in MODE_STREAM. Runs until EOF.
 *
 * Stop from phone: touch /data/local/tmp/stream.stop
 *   (checked every ~1s; file is deleted on exit)
 *
 * Usage on device:
 *   echo PCM_DATA | app_process -Djava.class.path=/data/local/tmp/stream.dex / StreamAudio 44100 2
 */
public class StreamAudio {

    static final String STOP_FILE = "/data/local/tmp/stream.stop";

    public static void main(String[] args) {
        try {
            if (args.length < 2) {
                System.err.println("Usage: StreamAudio <sampleRate> <channels>");
                System.exit(1);
            }

            int sampleRate = Integer.parseInt(args[0]);
            int channels = Integer.parseInt(args[1]);
            int channelMask = (channels == 1)
                ? AudioFormat.CHANNEL_OUT_MONO
                : AudioFormat.CHANNEL_OUT_STEREO;

            int minBuf = AudioTrack.getMinBufferSize(
                sampleRate, channelMask, AudioFormat.ENCODING_PCM_16BIT);
            int bufSize = Math.max(minBuf * 4, 32768);

            AudioTrack track = new AudioTrack(
                new AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                    .build(),
                new AudioFormat.Builder()
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                    .setSampleRate(sampleRate)
                    .setChannelMask(channelMask)
                    .build(),
                bufSize,
                AudioTrack.MODE_STREAM,
                0);

            // Clean up any leftover stop file
            new File(STOP_FILE).delete();

            track.play();
            System.out.println("Streaming " + sampleRate + "Hz " + channels + "ch 16bit");

            byte[] buf = new byte[bufSize];
            long totalBytes = 0;
            int checkCounter = 0;

            while (true) {
                int bytesRead = System.in.read(buf, 0, buf.length);
                if (bytesRead <= 0) break;
                track.write(buf, 0, bytesRead);
                totalBytes += bytesRead;

                // Check stop file roughly every second (~5 reads at 32KB/176KB per sec)
                if (++checkCounter >= 5) {
                    checkCounter = 0;
                    if (new File(STOP_FILE).exists()) {
                        System.out.println("Stop requested via " + STOP_FILE);
                        break;
                    }
                }
            }

            track.stop();
            track.release();
            new File(STOP_FILE).delete();

            long durationMs = totalBytes * 1000L / (sampleRate * channels * 2);
            System.out.println("Done. Streamed " + totalBytes + " bytes (" + durationMs + "ms)");
            System.exit(0);

        } catch (Exception e) {
            System.err.println("ERR: " + e);
            e.printStackTrace();
            System.exit(1);
        }
    }
}
