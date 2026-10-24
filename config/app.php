<?php

return [
    'name' => env('APP_NAME', 'CrawlInsight'),
    'env' => env('APP_ENV', 'local'),
    'debug' => (bool) env('APP_DEBUG', false),
    'url' => env('APP_URL', 'http://127.0.0.1:8000'),
    'timezone' => 'UTC',
    'locale' => env('APP_LOCALE', 'vi'),
    'admin_email' => env('ADMIN_EMAIL', ''),
    'fallback_locale' => 'en',
    'faker_locale' => 'vi_VN',
    'cipher' => 'AES-256-CBC',
    'key' => env('APP_KEY'),
    'previous_keys' => array_filter(explode(',', (string) env('APP_PREVIOUS_KEYS', ''))),
    'maintenance' => [
        'driver' => env('APP_MAINTENANCE_DRIVER', 'file'),
        'store' => env('APP_MAINTENANCE_STORE', 'database'),
    ],
];
