<?php

namespace App\Services;

use Illuminate\Support\Facades\DB;

class CrawlJobService
{
    public static function create(int $maxPages, int $userId): array
    {
        return DB::transaction(function () use ($maxPages, $userId): array {
            if (DB::selectOne("SELECT id FROM crawl_jobs WHERE status IN ('PENDING','RUNNING') LIMIT 1")) {
                throw new \DomainException('JOB_ALREADY_ACTIVE');
            }

            $now = AccountService::now();
            $id = DB::table('crawl_jobs')->insertGetId([
                'source_id' => 1,
                'max_pages' => $maxPages,
                'status' => 'PENDING',
                'created_at' => $now,
                'user_id' => $userId,
            ]);
            DB::insert(
                "INSERT INTO crawl_events(job_id,level,event_type,message,created_at) VALUES(?,'INFO','CREATED','Crawl job created',?)",
                [$id, $now],
            );

            return (array) DB::selectOne(
                'SELECT id,status,max_pages,created_at FROM crawl_jobs WHERE id=?',
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

        $databasePath = (string) config('database.connections.sqlite.database');
        $logDirectory = dirname($databasePath).DIRECTORY_SEPARATOR.'logs';
        if (!is_dir($logDirectory) && !mkdir($logDirectory, 0700, true) && !is_dir($logDirectory)) {
            throw new \RuntimeException('Could not create private crawler log directory.');
        }
        $stdout = $logDirectory.DIRECTORY_SEPARATOR.'crawl-job-'.$jobId.'.log';
        $stderr = $logDirectory.DIRECTORY_SEPARATOR.'crawl-job-'.$jobId.'.err.log';

        if (PHP_OS_FAMILY === 'Windows') {
            self::launchWindows($python, $jobId, $stdout, $stderr);

            return;
        }

        $command = 'CRAWLINSIGHT_DB_PATH='.escapeshellarg($databasePath)
            .' nohup '.escapeshellarg($python)
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
        $script = '$ErrorActionPreference = "Stop"; $env:CRAWLINSIGHT_DB_PATH = '
            .self::psQuote((string) config('database.connections.sqlite.database'))
            .'; Start-Process -FilePath '.self::psQuote($python)
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
}
