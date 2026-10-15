package com.music.bitchord.playback.audio.bluetooth

import android.bluetooth.BluetoothA2dp
import android.bluetooth.BluetoothAdapter
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.media.AudioDeviceCallback
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.os.Build
import android.util.Log
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.music.bitchord.playback.AudioRouting
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Monitors effective audio routing for Bluetooth A2DP or LE audio devices.
 * Specifically validates that the active route is media Bluetooth and explicitly
 * excludes built-in phone speaker, earpiece, and Bluetooth SCO (telephony).
 *
 * Persists the user preference to auto-enable spatial audio only when connected
 * to Bluetooth headphones, and coordinates real-time state with [com.music.bitchord.playback.SpatialAudioProcessor].
 */
class BluetoothRouteMonitor(private val context: Context) {

    private val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as? AudioManager

    private val _isBluetoothRouteActive = MutableStateFlow(false)
    val isBluetoothRouteActive: StateFlow<Boolean> = _isBluetoothRouteActive.asStateFlow()

    private var isRegistered = false

    private val deviceCallback = object : AudioDeviceCallback() {
        override fun onAudioDevicesAdded(addedDevices: Array<AudioDeviceInfo>) {
            refreshRoute()
        }

        override fun onAudioDevicesRemoved(removedDevices: Array<AudioDeviceInfo>) {
            refreshRoute()
        }
    }

    private val connectionReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            val action = intent?.action ?: return
            when (action) {
                BluetoothA2dp.ACTION_CONNECTION_STATE_CHANGED,
                BluetoothAdapter.ACTION_CONNECTION_STATE_CHANGED,
                BluetoothAdapter.ACTION_STATE_CHANGED -> {
                    refreshRoute()
                }
            }
        }
    }

    fun start() {
        init(context)
        if (!isRegistered) {
            audioManager?.registerAudioDeviceCallback(deviceCallback, null)

            val filter = IntentFilter().apply {
                addAction(BluetoothA2dp.ACTION_CONNECTION_STATE_CHANGED)
                addAction(BluetoothAdapter.ACTION_CONNECTION_STATE_CHANGED)
                addAction(BluetoothAdapter.ACTION_STATE_CHANGED)
            }
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    context.registerReceiver(connectionReceiver, filter, Context.RECEIVER_EXPORTED)
                } else {
                    context.registerReceiver(connectionReceiver, filter)
                }
            } catch (e: Throwable) {
                Log.w(TAG, "Failed to register Bluetooth receiver: ${e.message}")
            }

            isRegistered = true
        }
        refreshRoute()
    }

    fun stop() {
        if (isRegistered) {
            try {
                audioManager?.unregisterAudioDeviceCallback(deviceCallback)
            } catch (_: Throwable) {}

            try {
                context.unregisterReceiver(connectionReceiver)
            } catch (_: Throwable) {}

            isRegistered = false
        }
        isBluetoothActive = false
        _isBluetoothRouteActive.value = false
    }

    /**
     * Re-evaluates whether the current effective audio output is a Bluetooth media sink.
     */
    fun refreshRoute() {
        val manager = audioManager ?: run {
            isBluetoothActive = false
            _isBluetoothRouteActive.value = false
            return
        }

        val devices = runCatching {
            manager.getDevices(AudioManager.GET_DEVICES_OUTPUTS)
        }.getOrNull() ?: emptyArray()

        val active = AudioRouting.activeOf(devices, AudioRouting.selectedId.value)
        val isBt = isQualifyingBluetoothDevice(active)
        isBluetoothActive = isBt
        _isBluetoothRouteActive.value = isBt
    }

    companion object {
        private const val TAG = "BluetoothRouteMonitor"
        const val PREF_KEY_SPATIAL_AUDIO_AUTO_BLUETOOTH = "spatial_audio_auto_bluetooth"

        @Volatile
        var isBluetoothActive: Boolean = false
            internal set

        @Volatile
        var isAutoBluetoothEnabled: Boolean = false
            private set

        private val _autoBluetoothFlow = MutableStateFlow(false)
        val autoBluetoothFlow: StateFlow<Boolean> = _autoBluetoothFlow.asStateFlow()

        fun init(context: Context) {
            val prefs = context.getSharedPreferences("bitchord_settings", Context.MODE_PRIVATE)
            val saved = prefs.getBoolean(PREF_KEY_SPATIAL_AUDIO_AUTO_BLUETOOTH, false)
            isAutoBluetoothEnabled = saved
            _autoBluetoothFlow.value = saved

            val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as? AudioManager
            if (audioManager != null) {
                val devices = runCatching {
                    audioManager.getDevices(AudioManager.GET_DEVICES_OUTPUTS)
                }.getOrNull() ?: emptyArray()
                val active = AudioRouting.activeOf(devices, AudioRouting.selectedId.value)
                isBluetoothActive = isQualifyingBluetoothDevice(active)
            }
        }

        fun setAutoBluetoothEnabled(context: Context, enabled: Boolean) {
            isAutoBluetoothEnabled = enabled
            _autoBluetoothFlow.value = enabled
            val prefs = context.getSharedPreferences("bitchord_settings", Context.MODE_PRIVATE)
            prefs.edit().putBoolean(PREF_KEY_SPATIAL_AUDIO_AUTO_BLUETOOTH, enabled).apply()
        }

        /**
         * Checks whether [device] is a Bluetooth media sink (A2DP, LE Audio, or Hearing Aid),
         * strictly excluding built-in speaker and Bluetooth SCO.
         */
        fun isQualifyingBluetoothDevice(device: AudioDeviceInfo?): Boolean {
            if (device == null || !device.isSink) return false
            val type = device.type

            // Strictly exclude phone speaker, earpiece and SCO (telephony)
            if (type == AudioDeviceInfo.TYPE_BUILTIN_SPEAKER ||
                type == AudioDeviceInfo.TYPE_BUILTIN_EARPIECE ||
                type == AudioDeviceInfo.TYPE_BLUETOOTH_SCO
            ) {
                return false
            }

            // Strictly exclude wired or USB outputs
            if (type == AudioDeviceInfo.TYPE_WIRED_HEADPHONES ||
                type == AudioDeviceInfo.TYPE_WIRED_HEADSET ||
                type == AudioDeviceInfo.TYPE_LINE_ANALOG ||
                type == AudioDeviceInfo.TYPE_AUX_LINE ||
                type == AudioDeviceInfo.TYPE_USB_DEVICE ||
                type == AudioDeviceInfo.TYPE_USB_HEADSET ||
                type == AudioDeviceInfo.TYPE_USB_ACCESSORY
            ) {
                return false
            }

            // Must match Kind.BLUETOOTH in AudioRouting
            return AudioRouting.kindOf(type) == AudioRouting.Kind.BLUETOOTH
        }
    }
}

/**
 * Minimal Compose UI row for toggling automatic Bluetooth spatial audio.
 */
@Composable
fun SpatialAudioAutoBluetoothRow(
    context: Context,
    modifier: Modifier = Modifier,
) {
    val autoBluetooth by BluetoothRouteMonitor.autoBluetoothFlow.collectAsStateWithLifecycle()

    Row(
        modifier = modifier
            .fillMaxWidth()
            .clickable { BluetoothRouteMonitor.setAutoBluetoothEnabled(context, !autoBluetooth) }
            .padding(horizontal = 16.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = "Ativar apenas em fones Bluetooth",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onBackground,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = "Ativa o áudio espacial apenas em Bluetooth e desativa no alto-falante",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 3,
            )
        }
        Spacer(Modifier.width(12.dp))
        Switch(
            checked = autoBluetooth,
            onCheckedChange = { BluetoothRouteMonitor.setAutoBluetoothEnabled(context, it) },
            colors = SwitchDefaults.colors(
                checkedTrackColor = MaterialTheme.colorScheme.primary,
                checkedBorderColor = MaterialTheme.colorScheme.primary,
            ),
        )
    }
}
