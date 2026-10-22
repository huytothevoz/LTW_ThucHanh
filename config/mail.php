<?php

return [
    'default' => env('MAIL_MAILER', 'smtp'),
    'mailers' => [
        'smtp' => [
            'transport' => 'smtp',
            'scheme' => env('SMTP_SCHEME', 'smtp'),
            'url' => env('MAIL_URL'),
            'host' => env('SMTP_HOST'),
            'port' => (int) env('SMTP_PORT', 587),
            'username' => env('SMTP_USER'),
            'password' => env('SMTP_PASSWORD'),
            'timeout' => 10,
            'local_domain' => env('MAIL_EHLO_DOMAIN'),
        ],
        'log' => [
            'transport' => 'log',
            'channel' => env('MAIL_LOG_CHANNEL'),
        ],
    ],
    'from' => [
        'address' => env('SMTP_FROM', 'hello@example.com'),
        'name' => env('APP_NAME', 'CrawlInsight'),
    ],
];
