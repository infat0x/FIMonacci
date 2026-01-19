package com.fimonacci.app.utils

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.media.RingtoneManager
import android.os.Build
import androidx.core.app.NotificationCompat
import com.fimonacci.app.MainActivity
import com.fimonacci.app.R
import com.fimonacci.app.data.model.Alert

object NotificationHelper {
    private const val CHANNEL_ID = "fimonacci_alerts"
    private const val CHANNEL_NAME = "FIMonacci Alerts"
    private var notificationId = 0

    fun createNotificationChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Notifications for new file integrity alerts"
                enableVibration(true)
                enableLights(true)
            }
            val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }

    fun showNotification(
        context: Context,
        alert: Alert,
        soundEnabled: Boolean = true
    ) {
        val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        val pendingIntent = PendingIntent.getActivity(
            context,
            0,
            intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val severityEmoji = when (alert.severity.name) {
            "CRITICAL" -> "🔴"
            "HIGH" -> "⚠️"
            "MEDIUM" -> "🟡"
            else -> "ℹ️"
        }

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle("$severityEmoji New Alert: ${alert.filename}")
            .setContentText("${alert.eventType} on ${alert.agentName}")
            .setStyle(NotificationCompat.BigTextStyle()
                .bigText("File: ${alert.filename}\nAgent: ${alert.agentName}\nType: ${alert.eventType}\nSeverity: ${alert.severity.name}"))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .apply {
                if (soundEnabled) {
                    setSound(RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION))
                }
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    setVibrate(longArrayOf(0, 250, 250, 250))
                }
            }
            .build()

        notificationManager.notify(notificationId++, notification)
    }

    fun showMultipleAlertsNotification(
        context: Context,
        count: Int,
        soundEnabled: Boolean = true
    ) {
        val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        val pendingIntent = PendingIntent.getActivity(
            context,
            0,
            intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle("$count New Alerts")
            .setContentText("Tap to view details")
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .apply {
                if (soundEnabled) {
                    setSound(RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION))
                }
            }
            .build()

        notificationManager.notify(notificationId++, notification)
    }
}
