<?php

use Monolog\Handler\StreamHandler;
use Monolog\Level;

return [
    'default' => env('LOG_CHANNEL', 'single'),
    'deprecations' => [
        'channel' => env('LOG_DEPRECATIONS_CHANNEL', 'null'),
        'trace' => env('LOG_DEPRECATIONS_TRACE', false),
    ],
    'channels' => [
        'single' => [
            'driver' => 'single',
            'path' => storage_path('logs/laravel.log'),
            'level' => env('LOG_LEVEL', 'warning'),
            'replace_placeholders' => true,
        ],
        'stderr' => [
            'driver' => 'monolog',
            'handler' => StreamHandler::class,
            'with' => ['stream' => 'php://stderr'],
            'level' => env('LOG_LEVEL', 'warning'),
        ],
        'null' => [
            'driver' => 'monolog',
            'handler' => \Monolog\Handler\NullHandler::class,
        ],
    ],
];
