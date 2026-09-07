package com.sanlives.app.ui.components

import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sanlives.app.ui.theme.LocalSanLivesColors

@Composable
fun SanLivesPillButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    isPrimary: Boolean = true,
    backgroundColor: Color? = null,
    contentColor: Color? = null
) {
    val colors = LocalSanLivesColors.current
    val bg = backgroundColor ?: if (isPrimary) colors.accentColor else colors.inputBackground
    val fg = contentColor ?: if (isPrimary) Color.White else colors.textPrimary

    Button(
        onClick = onClick,
        modifier = modifier.height(38.dp),
        shape = CircleShape,
        colors = ButtonDefaults.buttonColors(
            containerColor = bg,
            contentColor = fg
        ),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 6.dp)
    ) {
        Text(
            text = text,
            fontWeight = FontWeight.Bold,
            fontSize = 12.5.sp
        )
    }
}
