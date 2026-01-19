package com.fimonacci.app.data.api

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

class RetrofitClient private constructor() {
    companion object {
        private const val DEFAULT_URL = "http://13.62.224.164:2828/"

        private val loggingInterceptor = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }

        private val okHttpClient = OkHttpClient.Builder()
            .addInterceptor(loggingInterceptor)
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build()

        @Volatile
        private var currentBaseUrl: String = DEFAULT_URL

        @Volatile
        private var apiServiceInstance: ApiService? = null

        fun getApiService(baseUrl: String = DEFAULT_URL): ApiService {
            // If URL changed, recreate the service
            if (baseUrl != currentBaseUrl || apiServiceInstance == null) {
                synchronized(this) {
                    currentBaseUrl = baseUrl

                    val normalizedUrl = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"

                    val retrofit = Retrofit.Builder()
                        .baseUrl(normalizedUrl)
                        .client(okHttpClient)
                        .addConverterFactory(GsonConverterFactory.create())
                        .build()

                    apiServiceInstance = retrofit.create(ApiService::class.java)
                }
            }
            return apiServiceInstance!!
        }
    }
}


