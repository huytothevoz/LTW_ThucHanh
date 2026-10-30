<?php

use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\DB;

Artisan::command('admin:promote', function (): int {
    $email = strtolower(trim((string) config('app.admin_email', '')));
    if ($email === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
        $this->error('Set a valid ADMIN_EMAIL in .env before promoting an administrator.');

        return \Symfony\Component\Console\Command\Command::FAILURE;
    }

    $user = DB::selectOne('SELECT id,is_active,role FROM users WHERE email=?', [$email]);
    if (!$user || (int) $user->is_active !== 1) {
        $this->error('The configured administrator account must exist and be active.');

        return \Symfony\Component\Console\Command\Command::FAILURE;
    }

    if ($user->role !== 'admin') {
        DB::update(
            "UPDATE users SET role='admin',session_version=session_version+1,updated_at=? WHERE id=?",
            [gmdate('Y-m-d\TH:i:s\Z'), $user->id],
        );
    }

    $this->info('Administrator role is enabled. Sign in again to refresh the session.');

    return \Symfony\Component\Console\Command\Command::SUCCESS;
})->purpose('Promote the configured, operator-verified ADMIN_EMAIL account.');
