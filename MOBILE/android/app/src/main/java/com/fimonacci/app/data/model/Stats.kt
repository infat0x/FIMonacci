package com.fimonacci.app.data.model

data class Stats(
    val modified: Int,
    val deleted: Int,
    val created: Int,
    val accessed: Int,
    val critical: Int,
    val high: Int,
    val medium: Int,
    val low: Int
)


