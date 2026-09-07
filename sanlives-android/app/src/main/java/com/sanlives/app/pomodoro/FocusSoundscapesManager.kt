package com.sanlives.app.pomodoro

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlin.math.sin
import kotlin.random.Random

enum class Soundscape(val id: String, val displayName: String, val icon: String) {
    NONE("none", "Silent", "🔇"),
    RAIN("rain", "Rain & Storm", "🌧️"),
    OCEAN("ocean", "Ocean Waves", "🌊"),
    BROWN_NOISE("brown", "Deep Brown Noise", "🍂"),
    WHITE_NOISE("white", "White Noise", "💨")
}

object FocusSoundscapesManager {

    private var audioTrack: AudioTrack? = null
    private var generatorJob: Job? = null
    private val scope = CoroutineScope(Dispatchers.Default)

    private val _currentSoundscape = MutableStateFlow(Soundscape.NONE)
    val currentSoundscape: StateFlow<Soundscape> = _currentSoundscape.asStateFlow()

    private val _volume = MutableStateFlow(0.7f)
    val volume: StateFlow<Float> = _volume.asStateFlow()

    private const val SAMPLE_RATE = 44100
    private const val BUFFER_SIZE = 4096

    fun setSoundscape(soundscape: Soundscape) {
        if (_currentSoundscape.value == soundscape) return
        _currentSoundscape.value = soundscape

        if (soundscape == Soundscape.NONE) {
            stopAudio()
        } else {
            startAudio(soundscape)
        }
    }

    fun setVolume(vol: Float) {
        val clamped = vol.coerceIn(0f, 1f)
        _volume.value = clamped
        audioTrack?.setVolume(clamped)
    }

    private fun startAudio(soundscape: Soundscape) {
        stopAudio()

        try {
            audioTrack = AudioTrack.Builder()
                .setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_MEDIA)
                        .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                        .build()
                )
                .setAudioFormat(
                    AudioFormat.Builder()
                        .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                        .setSampleRate(SAMPLE_RATE)
                        .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                        .build()
                )
                .setBufferSizeInBytes(BUFFER_SIZE * 2)
                .setTransferMode(AudioTrack.MODE_STREAM)
                .build()

            audioTrack?.setVolume(_volume.value)
            audioTrack?.play()

            generatorJob = scope.launch {
                val buffer = ShortArray(BUFFER_SIZE)
                var lastVal = 0f
                var phase = 0.0

                while (isActive) {
                    when (_currentSoundscape.value) {
                        Soundscape.BROWN_NOISE -> {
                            for (i in 0 until BUFFER_SIZE) {
                                val white = (Random.nextFloat() * 2f - 1f)
                                lastVal = (lastVal + (0.02f * white)) / 1.02f
                                buffer[i] = (lastVal.coerceIn(-1f, 1f) * 32000).toInt().toShort()
                            }
                        }
                        Soundscape.WHITE_NOISE -> {
                            for (i in 0 until BUFFER_SIZE) {
                                val white = (Random.nextFloat() * 2f - 1f) * 0.4f
                                buffer[i] = (white * 32000).toInt().toShort()
                            }
                        }
                        Soundscape.RAIN -> {
                            for (i in 0 until BUFFER_SIZE) {
                                val white = (Random.nextFloat() * 2f - 1f)
                                lastVal = (lastVal * 0.85f) + (white * 0.15f)
                                val drop = if (Random.nextFloat() < 0.003f) (Random.nextFloat() * 0.7f) else 0f
                                val sample = (lastVal * 0.6f + drop).coerceIn(-1f, 1f)
                                buffer[i] = (sample * 30000).toInt().toShort()
                            }
                        }
                        Soundscape.OCEAN -> {
                            for (i in 0 until BUFFER_SIZE) {
                                phase += 2.0 * Math.PI * 0.1 / SAMPLE_RATE
                                val waveMod = (sin(phase).toFloat() + 1f) * 0.5f
                                val white = (Random.nextFloat() * 2f - 1f)
                                lastVal = (lastVal * 0.94f) + (white * 0.06f)
                                val sample = (lastVal * (0.3f + waveMod * 0.7f)).coerceIn(-1f, 1f)
                                buffer[i] = (sample * 32000).toInt().toShort()
                            }
                        }
                        Soundscape.NONE -> break
                    }

                    audioTrack?.write(buffer, 0, BUFFER_SIZE)
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    fun stopAudio() {
        generatorJob?.cancel()
        generatorJob = null
        try {
            audioTrack?.stop()
            audioTrack?.release()
            audioTrack = null
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
}
