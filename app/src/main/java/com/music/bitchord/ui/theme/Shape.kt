package com.music.bitchord.ui.theme

import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.unit.dp

/**
 * Padrões de formas geométricas (Shapes) do Sonium / Apple iOS HIG.
 */

// Cápsula 100% redonda para itens individuais/standalone (pílula perfeita)
val CapsuleShape: Shape = CircleShape

// Bloco retangular com cantos arredondados no padrão Inset Grouped do iOS (14.dp)
val InsetGroupedShape: Shape = RoundedCornerShape(14.dp)

// Shapes para cantos superiores e inferiores em blocos agrupados
val InsetGroupedTopShape: Shape = RoundedCornerShape(topStart = 14.dp, topEnd = 14.dp, bottomStart = 0.dp, bottomEnd = 0.dp)
val InsetGroupedMiddleShape: Shape = RoundedCornerShape(0.dp)
val InsetGroupedBottomShape: Shape = RoundedCornerShape(topStart = 0.dp, topEnd = 0.dp, bottomStart = 14.dp, bottomEnd = 14.dp)

/**
 * Retorna o Shape correto para grupos de configurações:
 * - Se o grupo tiver apenas 1 item (standalone), usa cápsula 100% redonda (CapsuleShape / CircleShape).
 * - Se houver múltiplos itens no mesmo bloco, usa o bloco retangular arredondado (InsetGroupedShape).
 */
fun settingsGroupShape(count: Int = 1, isStandalone: Boolean = (count == 1)): Shape {
    return if (isStandalone || count == 1) CapsuleShape else InsetGroupedShape
}
