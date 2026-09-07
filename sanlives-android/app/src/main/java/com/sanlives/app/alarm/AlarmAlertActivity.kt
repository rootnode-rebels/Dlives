package com.sanlives.app.alarm

import android.app.KeyguardManager
import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.media.AudioAttributes
import android.media.MediaPlayer
import android.media.RingtoneManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.view.WindowManager
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.sanlives.app.SanLivesApp
import com.sanlives.app.ui.components.IconChip
import com.sanlives.app.ui.components.SanLivesPillButton
import com.sanlives.app.ui.theme.DarkBg
import com.sanlives.app.ui.theme.DarkCard
import com.sanlives.app.ui.theme.SanLivesTheme
import kotlinx.coroutines.delay
import java.text.SimpleDateFormat
import java.util.*
import kotlin.math.sqrt

class AlarmAlertActivity : ComponentActivity(), SensorEventListener {

    private var mediaPlayer: MediaPlayer? = null
    private var vibrator: Vibrator? = null
    private var sensorManager: SensorManager? = null
    private var accelerometer: Sensor? = null

    private var shakeCount = mutableIntStateOf(0)
    private val requiredShakes = 15
    private var lastAcceleration = 0f
    private var currentAcceleration = 0f
    private var shakeThreshold = 12f

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Turn screen on and show above lockscreen
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true)
            setTurnScreenOn(true)
            val km = getSystemService(Context.KEYGUARD_SERVICE) as KeyguardManager
            km.requestDismissKeyguard(this, null)
        } else {
            @Suppress("DEPRECATION")
            window.addFlags(
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
                        WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD or
                        WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON or
                        WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
            )
        }

        val alarmId = intent.getLongExtra(AlarmReceiver.EXTRA_ALARM_ID, -1L)
        val label = intent.getStringExtra(AlarmReceiver.EXTRA_ALARM_LABEL) ?: "Alarm"
        val hour = intent.getIntExtra(AlarmReceiver.EXTRA_ALARM_HOUR, Calendar.getInstance().get(Calendar.HOUR_OF_DAY))
        val minute = intent.getIntExtra(AlarmReceiver.EXTRA_ALARM_MINUTE, Calendar.getInstance().get(Calendar.MINUTE))
        val soundUriStr = intent.getStringExtra(AlarmReceiver.EXTRA_ALARM_SOUND_URI)
        val repeatDays = intent.getStringArrayListExtra(AlarmReceiver.EXTRA_ALARM_REPEAT_DAYS) ?: arrayListOf()
        val mission = intent.getStringExtra(AlarmReceiver.EXTRA_ALARM_MISSION) ?: "none"

        startSoundAndVibration(soundUriStr)

        if (mission == "shake") {
            setupShakeSensor()
        }

        val prefs = (application as SanLivesApp).preferencesManager
        val durationSec = prefs.alarmDisplayDurationSec.value

        setContent {
            val themeMode by prefs.themeMode.collectAsState()
            val accentName by prefs.accentName.collectAsState()
            val is12h by prefs.is12HourFormat.collectAsState()

            SanLivesTheme(themeMode = themeMode, accentName = accentName) {
                AlarmAlertScreen(
                    label = label,
                    hour = hour,
                    minute = minute,
                    is12h = is12h,
                    repeatDays = repeatDays,
                    timeoutSeconds = durationSec,
                    mission = mission,
                    currentShakes = shakeCount.intValue,
                    requiredShakes = requiredShakes,
                    onSnooze = { minutes ->
                        stopSoundAndVibration()
                        val scheduler = AlarmScheduler(this@AlarmAlertActivity)
                        scheduler.scheduleSnooze(alarmId, label, minutes, soundUriStr)
                        finish()
                    },
                    onDismiss = {
                        stopSoundAndVibration()
                        finish()
                    }
                )
            }
        }
    }

    private fun setupShakeSensor() {
        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        accelerometer = sensorManager?.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
        sensorManager?.registerListener(this, accelerometer, SensorManager.SENSOR_DELAY_UI)
        lastAcceleration = SensorManager.GRAVITY_EARTH
        currentAcceleration = SensorManager.GRAVITY_EARTH
    }

    override fun onSensorChanged(event: SensorEvent?) {
        if (event == null) return
        val x = event.values[0]
        val y = event.values[1]
        val z = event.values[2]

        lastAcceleration = currentAcceleration
        currentAcceleration = sqrt((x * x + y * y + z * z).toDouble()).toFloat()
        val delta = currentAcceleration - lastAcceleration

        if (delta > shakeThreshold) {
            shakeCount.intValue++
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    private fun startSoundAndVibration(soundUriStr: String?) {
        try {
            val soundUri = if (soundUriStr != null) Uri.parse(soundUriStr) else RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM)
            mediaPlayer = MediaPlayer().apply {
                setDataSource(this@AlarmAlertActivity, soundUri)
                setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ALARM)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                        .build()
                )
                isLooping = true
                prepare()
                start()
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }

        try {
            vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val vm = getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
                vm.defaultVibrator
            } else {
                @Suppress("DEPRECATION")
                getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
            }

            val pattern = longArrayOf(0, 500, 500, 500, 500)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator?.vibrate(VibrationEffect.createWaveform(pattern, 0))
            } else {
                @Suppress("DEPRECATION")
                vibrator?.vibrate(pattern, 0)
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun stopSoundAndVibration() {
        try {
            mediaPlayer?.stop()
            mediaPlayer?.release()
            mediaPlayer = null
        } catch (e: Exception) {
            e.printStackTrace()
        }

        try {
            vibrator?.cancel()
            vibrator = null
        } catch (e: Exception) {
            e.printStackTrace()
        }

        try {
            sensorManager?.unregisterListener(this)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        stopSoundAndVibration()
    }
}

@Composable
fun AlarmAlertScreen(
    label: String,
    hour: Int,
    minute: Int,
    is12h: Boolean,
    repeatDays: List<String>,
    timeoutSeconds: Int,
    mission: String,
    currentShakes: Int,
    requiredShakes: Int,
    onSnooze: (Int) -> Unit,
    onDismiss: () -> Unit
) {
    var secondsLeft by remember { mutableIntStateOf(timeoutSeconds) }
    var showMathDialog by remember { mutableStateOf(false) }

    // Math Challenge State
    val numA = remember { (12..48).random() }
    val numB = remember { (15..49).random() }
    val correctSum = numA + numB
    var mathAnswerInput by remember { mutableStateOf("") }
    var mathError by remember { mutableStateOf(false) }

    // Auto-dismiss countdown timer
    LaunchedEffect(Unit) {
        while (secondsLeft > 0) {
            delay(1000)
            secondsLeft--
        }
        onDismiss()
    }

    val timeFormatted = if (is12h) {
        val ampm = if (hour >= 12) "PM" else "AM"
        val h = hour % 12
        val displayH = if (h == 0) 12 else h
        "%02d:%02d %s".format(displayH, minute, ampm)
    } else {
        "%02d:%02d".format(hour, minute)
    }

    // Pulsing Scale Animation for Bell
    val infiniteTransition = rememberInfiniteTransition(label = "BellPulse")
    val bellScale by infiniteTransition.animateFloat(
        initialValue = 1.0f,
        targetValue = 1.22f,
        animationSpec = infiniteRepeatable(
            animation = tween(600, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "BellScaleAnim"
    )

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBg)
            .padding(24.dp),
        contentAlignment = Alignment.Center
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Auto-Dismiss Progress Bar
            LinearProgressIndicator(
                progress = { secondsLeft.toFloat() / timeoutSeconds },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(4.dp)
                    .clip(RoundedCornerShape(2.dp)),
                color = Color(0xFFEF4444),
                trackColor = Color(0xFF232733)
            )

            Spacer(modifier = Modifier.height(10.dp))

            Text(
                text = "Auto-dismisses in s",
                fontSize = 11.sp,
                color = Color(0xFF94A3B8)
            )

            Spacer(modifier = Modifier.height(40.dp))

            // Animated Pulsing Alarm Bell Icon
            Box(
                modifier = Modifier
                    .size(110.dp)
                    .scale(bellScale)
                    .clip(CircleShape)
                    .background(Color(0xFFEF4444).copy(alpha = 0.2f)),
                contentAlignment = Alignment.Center
            ) {
                Box(
                    modifier = Modifier
                        .size(80.dp)
                        .clip(CircleShape)
                        .background(Color(0xFFEF4444)),
                    contentAlignment = Alignment.Center
                ) {
                    Text(text = "⏰", fontSize = 38.sp)
                }
            }

            Spacer(modifier = Modifier.height(30.dp))

            // Alarm Time
            Text(
                text = timeFormatted,
                fontSize = 44.sp,
                fontWeight = FontWeight.ExtraBold,
                color = Color.White
            )

            Spacer(modifier = Modifier.height(6.dp))

            // Alarm Label
            Text(
                text = label,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF38BDF8)
            )

            // Mission Banner if required
            if (mission == "shake") {
                Spacer(modifier = Modifier.height(16.dp))
                val shakeProgress = (currentShakes.toFloat() / requiredShakes).coerceIn(0f, 1f)
                Card(
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFF59E0B).copy(alpha = 0.15f))
                ) {
                    Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            text = "📳 Shake Phone to Unlock Dismiss:  / ",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFFF59E0B)
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        LinearProgressIndicator(
                            progress = { shakeProgress },
                            modifier = Modifier.fillMaxWidth().height(6.dp).clip(RoundedCornerShape(3.dp)),
                            color = Color(0xFFF59E0B),
                            trackColor = Color(0xFF232733)
                        )
                    }
                }
            } else if (mission == "math") {
                Spacer(modifier = Modifier.height(14.dp))
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(10.dp))
                        .background(Color(0xFFEF4444).copy(alpha = 0.15f))
                        .padding(horizontal = 12.dp, vertical = 4.dp)
                ) {
                    Text(text = "🔢 Math Mission Required to Dismiss", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = Color(0xFFEF4444))
                }
            }

            Spacer(modifier = Modifier.height(36.dp))

            // 1-Tap Quick Snooze Duration Pills
            Text(
                text = "Quick Snooze:",
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color(0xFF94A3B8)
            )
            Spacer(modifier = Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                listOf(5, 10, 15, 30, 60).forEach { mins ->
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(10.dp))
                            .background(DarkCard)
                            .clickable { onSnooze(mins) }
                            .padding(horizontal = 10.dp, vertical = 8.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "m",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF38BDF8)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(36.dp))

            // Big Dismiss Button (Subject to Mission verification)
            val canDismiss = when (mission) {
                "shake" -> currentShakes >= requiredShakes
                "math" -> false // Needs dialog solve
                else -> true
            }

            Button(
                onClick = {
                    if (mission == "math") {
                        showMathDialog = true
                    } else if (mission == "shake") {
                        if (currentShakes >= requiredShakes) onDismiss()
                    } else {
                        onDismiss()
                    }
                },
                modifier = Modifier
                    .fillMaxWidth(0.85f)
                    .height(54.dp),
                shape = CircleShape,
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (canDismiss || mission == "math") Color(0xFFEF4444) else Color(0xFF334155),
                    contentColor = Color.White
                )
            ) {
                Text(
                    text = if (mission == "math") "🔢 Solve Math & Dismiss" else if (mission == "shake" && !canDismiss) "📳 Shake to Unlock Dismiss" else "✓ Dismiss Alarm",
                    fontSize = 16.sp,
                    fontWeight = FontWeight.ExtraBold
                )
            }
        }
    }

    // Math Challenge Dialog
    if (showMathDialog) {
        Dialog(onDismissRequest = { showMathDialog = false }) {
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = DarkCard),
                modifier = Modifier.padding(16.dp)
            ) {
                Column(
                    modifier = Modifier.padding(20.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "🧠 Wake-Up Math Mission",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = " +  = ?",
                        fontSize = 28.sp,
                        fontWeight = FontWeight.ExtraBold,
                        color = Color(0xFF38BDF8)
                    )
                    Spacer(modifier = Modifier.height(14.dp))
                    OutlinedTextField(
                        value = mathAnswerInput,
                        onValueChange = {
                            mathAnswerInput = it
                            mathError = false
                        },
                        placeholder = { Text("Enter answer...", fontSize = 13.sp, color = Color(0xFF94A3B8)) },
                        singleLine = true,
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedContainerColor = DarkBg,
                            unfocusedContainerColor = DarkBg,
                            focusedBorderColor = if (mathError) Color(0xFFEF4444) else Color(0xFF38BDF8),
                            unfocusedBorderColor = if (mathError) Color(0xFFEF4444) else Color(0xFF232733),
                            focusedTextColor = Color.White,
                            unfocusedTextColor = Color.White
                        ),
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth()
                    )
                    if (mathError) {
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(text = "❌ Incorrect answer. Try again!", fontSize = 11.sp, color = Color(0xFFEF4444))
                    }
                    Spacer(modifier = Modifier.height(16.dp))
                    SanLivesPillButton(
                        text = "Submit & Dismiss",
                        onClick = {
                            val parsed = mathAnswerInput.trim().toIntOrNull()
                            if (parsed == correctSum) {
                                showMathDialog = false
                                onDismiss()
                            } else {
                                mathError = true
                            }
                        },
                        backgroundColor = Color(0xFFEF4444),
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }
        }
    }
}
