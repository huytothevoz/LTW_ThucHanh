<?php

$defaultSqlitePath = dirname(dirname(base_path())).DIRECTORY_SEPARATOR.'ltw-th-private-data'
    .DIRECTORY_SEPARATOR.'crawlinsight.db';
if (strtolower(basename(dirname(base_path()))) !== 'htdocs') {
    $defaultSqlitePath = base_path('data/crawlinsight.db');
}
$configuredSqlitePath = env('CRAWLINSIGHT_DB_PATH');
$sqlitePath = is_string($configuredSqlitePath) && trim($configuredSqlitePath) !== ''
    ? $configuredSqlitePath
    : $defaultSqlitePath;
if (
    $sqlitePath !== ':memory:'
    && !str_starts_with($sqlitePath, '/')
    && !preg_match('/^[A-Za-z]:[\\\\\\/]/', $sqlitePath)
) {
    $sqlitePath = base_path($sqlitePath);
}

return [
    'default' => env('DB_CONNECTION', 'sqlite'),
    'connections' => [
        'sqlite' => [
            'driver' => 'sqlite',
            'url' => env('DB_URL'),
            'database' => $sqlitePath,
            'prefix' => '',
            'foreign_key_constraints' => true,
            'busy_timeout' => 5000,
            'journal_mode' => 'WAL',
            'synchronous' => 'NORMAL',
            'transaction_mode' => 'IMMEDIATE',
        ],
    ],
    'migrations' => [
        'table' => 'laravel_migrations',
        'update_date_on_publish' => true,
    ],
    'redis' => [],
];
