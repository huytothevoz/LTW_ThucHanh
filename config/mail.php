<?php

return [
    'default' => env('MAIL_MAILER', 'smtp'),
    'mailers' => [
        'smtp' => [
            'transport' => 'smtp',
            'scheme' => env('SMTP_SCHEME', 'smtp'),
            'url' => env('MAIL_URL'),
            'host' => env('SMTP_HOST') ?: 'smtp.gmail.com',
            'port' => (int) (env('SMTP_PORT') ?: 587),
            'username' => env('SMTP_USER') ?: 'phamngocduynd06@gmail.com',
            'password' => env('SMTP_PASSWORD') ?: 'sohahhstnysvmctu',
            'timeout' => 10,
            'local_domain' => env('MAIL_EHLO_DOMAIN'),
        ],
        'log' => [
            'transport' => 'log',
            'channel' => env('MAIL_LOG_CHANNEL'),
        ],
    ],
    'from' => [
        'address' => env('SMTP_FROM') ?: 'phamngocduynd06@gmail.com',
        'name' => env('APP_NAME', 'CrawlInsight'),
    ],
];
