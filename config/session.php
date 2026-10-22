<?php

return [
    'driver' => env('SESSION_DRIVER', 'file'),
    'lifetime' => (int) env('SESSION_LIFETIME', 10080),
    'expire_on_close' => false,
    'encrypt' => true,
    'files' => storage_path('framework/sessions'),
    'connection' => env('SESSION_CONNECTION'),
    'table' => env('SESSION_TABLE', 'sessions'),
    'store' => env('SESSION_STORE'),
    'lottery' => [2, 100],
    'cookie' => env('SESSION_COOKIE', 'crawl_insight_session'),
    'path' => '/',
    'domain' => env('SESSION_DOMAIN'),
    'secure' => (bool) env('CRAWLINSIGHT_HTTPS', false),
    'http_only' => true,
    'same_site' => 'lax',
    'partitioned' => false,
];
