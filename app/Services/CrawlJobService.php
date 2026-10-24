<?php

namespace App\Services;

use Illuminate\Support\Facades\DB;

class CrawlJobService
{
    public static function create(int $maxPages, int $userId, int $sourceId = 1): array
    {
        return DB::transaction(function () use ($maxPages, $userId, $sourceId): array {
            if (DB::selectOne(
                "SELECT id FROM crawl_jobs WHERE user_id=? AND status IN ('PENDING','RUNNING') LIMIT 1",
                [$userId],
            )) {
                throw new \DomainException('JOB_ALREADY_ACTIVE');
            }

            $source = DB::selectOne('SELECT id, name FROM sources WHERE id = ?', [$sourceId]);
            $sourceName = $source ? $source->name : 'Books to Scrape';
            $now = AccountService::now();
            $id = DB::table('crawl_jobs')->insertGetId([
                'source_id' => $sourceId,
                'max_pages' => $maxPages,
                'status' => 'PENDING',
                'created_at' => $now,
                'user_id' => $userId,
            ]);
            DB::insert(
                "INSERT INTO crawl_events(job_id,level,event_type,message,created_at) VALUES(?,'INFO','CREATED',?,?)",
                [$id, "Crawl job created for {$sourceName}", $now],
            );

            return (array) DB::selectOne(
                'SELECT c.id,c.status,c.max_pages,c.created_at,
                        (SELECT COUNT(*) FROM crawl_jobs t WHERE t.user_id = c.user_id AND t.id <= c.id) AS user_job_number
                 FROM crawl_jobs c WHERE c.id=?',
                [$id],
            );
        });
    }

    public static function launch(int $jobId): void
    {
        $python = (string) env('CRAWLINSIGHT_PYTHON', '');
        if ($python === '') {
            $candidate = base_path('.venv/Scripts/python.exe');
            $python = PHP_OS_FAMILY === 'Windows'
                ? (is_file($candidate) ? $candidate : 'python')
                : 'python3';
        } elseif (!str_contains($python, DIRECTORY_SEPARATOR) && !str_contains($python, '/')) {
            $python = $python;
        } elseif (!str_starts_with($python, '/') && !preg_match('/^[A-Za-z]:[\\\\\\/]/', $python)) {
            $python = base_path($python);
        }

        $logDirectory = storage_path('logs');
        if (!is_dir($logDirectory) && !mkdir($logDirectory, 0700, true) && !is_dir($logDirectory)) {
            throw new \RuntimeException('Could not create private crawler log directory.');
        }
        $stdout = $logDirectory.DIRECTORY_SEPARATOR.'crawl-job-'.$jobId.'.log';
        $stderr = $logDirectory.DIRECTORY_SEPARATOR.'crawl-job-'.$jobId.'.err.log';

        if (PHP_OS_FAMILY === 'Windows') {
            self::launchWindows($python, $jobId, $stdout, $stderr);

            return;
        }

        $environment = self::crawlerEnvironment();
        $prefix = implode(' ', array_map(
            static fn (string $key, string $value): string => $key.'='.escapeshellarg($value),
            array_keys($environment),
            array_values($environment),
        ));
        $command = $prefix.' nohup '.escapeshellarg($python)
            .' -m crawler.run_job --job-id '.escapeshellarg((string) $jobId)
            .' </dev/null >>'.escapeshellarg($stdout)
            .' 2>>'.escapeshellarg($stderr).' &';
        $process = proc_open($command, [0 => ['pipe', 'r'], 1 => ['pipe', 'w'], 2 => ['pipe', 'w']], $pipes, base_path());
        if (!is_resource($process)) {
            throw new \RuntimeException('Could not start crawler process.');
        }
        foreach ($pipes as $pipe) {
            fclose($pipe);
        }
        proc_close($process);
    }

    public static function fail(int $jobId, string $message): void
    {
        $now = AccountService::now();
        $message = mb_substr(preg_replace('/\s+/u', ' ', $message) ?? $message, 0, 220);
        DB::transaction(function () use ($jobId, $message, $now): void {
            $changed = DB::update(
                "UPDATE crawl_jobs SET status='FAILED',finished_at=?,last_error=?,error_count=error_count+1 WHERE id=? AND status IN ('PENDING','RUNNING')",
                [$now, $message, $jobId],
            );
            if ($changed) {
                DB::insert(
                    "INSERT INTO crawl_events(job_id,level,event_type,message,created_at) VALUES(?,'ERROR','FAILED',?,?)",
                    [$jobId, $message, $now],
                );
            }
        });
    }

    private static function launchWindows(string $python, int $jobId, string $stdout, string $stderr): void
    {
        $assignments = '';
        foreach (self::crawlerEnvironment() as $key => $value) {
            $assignments .= '$env:'.$key.' = '.self::psQuote($value).'; ';
        }
        $script = '$ErrorActionPreference = "Stop"; '.$assignments
            .'Start-Process -FilePath '.self::psQuote($python)
            .' -ArgumentList @("-m","crawler.run_job","--job-id",'.self::psQuote((string) $jobId).')'
            .' -WorkingDirectory '.self::psQuote(base_path())
            .' -RedirectStandardOutput '.self::psQuote($stdout)
            .' -RedirectStandardError '.self::psQuote($stderr)
            .' -WindowStyle Hidden';
        $encoded = base64_encode(mb_convert_encoding($script, 'UTF-16LE', 'UTF-8'));
        $launcherLog = dirname($stdout).DIRECTORY_SEPARATOR.'crawl-launch.log';
        $process = proc_open(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand', $encoded],
            [0 => ['file', 'NUL', 'r'], 1 => ['file', $launcherLog, 'a'], 2 => ['file', $launcherLog, 'a']],
            $pipes,
            base_path(),
            null,
            ['bypass_shell' => true],
        );
        if (!is_resource($process)) {
            throw new \RuntimeException('Could not start PowerShell crawler launcher.');
        }
        $exitCode = proc_close($process);
        if ($exitCode !== 0) {
            throw new \RuntimeException('PowerShell crawler launcher failed; check crawl-launch.log.');
        }
    }

    private static function psQuote(string $value): string
    {
        return "'".str_replace("'", "''", $value)."'";
    }

    private static function crawlerEnvironment(): array
    {
        $mysql = config('database.connections.mysql');

        return [
            'DB_CONNECTION' => (string) config('database.default'),
            'DB_HOST' => (string) $mysql['host'],
            'DB_PORT' => (string) $mysql['port'],
            'DB_DATABASE' => (string) $mysql['database'],
            'DB_USERNAME' => (string) $mysql['username'],
            'DB_PASSWORD' => (string) $mysql['password'],
        ];
    }
}
