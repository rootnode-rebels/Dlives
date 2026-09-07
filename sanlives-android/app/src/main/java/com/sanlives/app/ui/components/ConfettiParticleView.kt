package com.sanlives.app.ui.components

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.rotate
import kotlin.random.Random

data class Particle(
    val x: Float,
    val y: Float,
    val speedX: Float,
    val speedY: Float,
    val size: Float,
    val color: Color,
    val rotation: Float,
    val rotationSpeed: Float
)

@Composable
fun ConfettiCelebrationView(
    trigger: Boolean,
    onAnimationEnd: () -> Unit = {}
) {
    if (!trigger) return

    val particles = remember {
        val colors = listOf(
            Color(0xFFFF3B30),
            Color(0xFF34C759),
            Color(0xFF38BDF8),
            Color(0xFFFFD60A),
            Color(0xFFAF52DE),
            Color(0xFFFF9500)
        )
        List(60) {
            Particle(
                x = Random.nextFloat() * 1000f,
                y = -Random.nextFloat() * 200f,
                speedX = (Random.nextFloat() - 0.5f) * 600f,
                speedY = Random.nextFloat() * 700f + 400f,
                size = Random.nextFloat() * 14f + 8f,
                color = colors.random(),
                rotation = Random.nextFloat() * 360f,
                rotationSpeed = (Random.nextFloat() - 0.5f) * 720f
            )
        }
    }

    val progress = remember { Animatable(0f) }

    LaunchedEffect(trigger) {
        progress.animateTo(
            targetValue = 1f,
            animationSpec = tween(durationMillis = 2800, easing = LinearOutSlowInEasing)
        )
        onAnimationEnd()
    }

    Canvas(modifier = Modifier.fillMaxSize()) {
        val t = progress.value
        val alpha = (1f - (t - 0.6f) / 0.4f).coerceIn(0f, 1f)

        particles.forEach { p ->
            val curX = (p.x + p.speedX * t) % size.width
            val curY = p.y + p.speedY * t
            val curRot = p.rotation + p.rotationSpeed * t

            rotate(degrees = curRot, pivot = Offset(curX, curY)) {
                drawRect(
                    color = p.color.copy(alpha = alpha),
                    topLeft = Offset(curX, curY),
                    size = Size(p.size, p.size * 0.6f)
                )
            }
        }
    }
}
