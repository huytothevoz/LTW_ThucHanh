<?php

use App\Services\AccountService;
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

Artisan::command('app:seed-demo', function (): int {
    if (config('app.env') !== 'local') {
        $this->error('Default demo accounts can only be created when APP_ENV=local.');

        return \Symfony\Component\Console\Command\Command::FAILURE;
    }

    $accounts = [
        [
            'name' => 'CrawlInsight Admin',
            'email' => 'admin@crawlinsight.local',
            'password' => 'CrawlInsightAdmin2026!',
            'role' => 'admin',
        ],
        [
            'name' => 'CrawlInsight Demo',
            'email' => 'demo@crawlinsight.local',
            'password' => 'CrawlInsightDemo2026!',
            'role' => 'user',
        ],
    ];
    $books = [
        ['The Paper Observatory', 'Fiction', 1299, 5, 'demo-paper-observatory'],
        ['A Field Guide to Quiet Stars', 'Science', 1849, 4, 'demo-quiet-stars'],
        ['The Cartographers Garden', 'Travel', 975, 4, 'demo-cartographers-garden'],
        ['Small Histories of Tomorrow', 'History', 2240, 3, 'demo-small-histories'],
        ['The Curious Clockwork Forest', 'Children', 1599, 5, 'demo-clockwork-forest'],
    ];

    try {
        $result = DB::transaction(function () use ($accounts, $books): array {
            $created = [];
            foreach ($accounts as $account) {
                $existing = DB::table('users')->where('email', $account['email'])->first();
                if ($existing) {
                    if ($existing->role !== $account['role'] || (int) $existing->is_active !== 1) {
                        throw new \RuntimeException(
                            "Account {$account['email']} already exists with a different role or inactive status; it was not changed.",
                        );
                    }
                    $created[$account['email']] = false;
                    continue;
                }

                $user = AccountService::register(
                    $account['name'],
                    $account['email'],
                    $account['password'],
                );
                if ($account['role'] === 'admin') {
                    DB::table('users')->where('id', $user['id'])->update([
                        'role' => 'admin',
                        'updated_at' => AccountService::now(),
                    ]);
                }
                $created[$account['email']] = true;
            }

            if (!DB::table('sources')->where('id', 1)->exists()) {
                throw new \RuntimeException('The default Books to Scrape source is missing.');
            }

            $demoUserId = (int) DB::table('users')
                ->where('email', 'demo@crawlinsight.local')
                ->value('id');
            $now = AccountService::now();
            foreach ($books as [$title, $categoryName, $pricePence, $rating, $slug]) {
                $category = DB::table('categories')
                    ->where('source_id', 1)
                    ->where('name', $categoryName)
                    ->first();
                if (!$category) {
                    $categoryId = DB::table('categories')->insertGetId([
                        'source_id' => 1,
                        'name' => $categoryName,
                        'first_seen_at' => $now,
                    ]);
                } else {
                    $categoryId = (int) $category->id;
                }

                $url = "https://books.toscrape.com/catalogue/{$slug}.html";
                $urlHash = hash('sha256', $url);
                if (DB::table('books')
                    ->where('user_id', $demoUserId)
                    ->where('source_url_hash', $urlHash)
                    ->exists()) {
                    continue;
                }

                DB::table('books')->insert([
                    'source_id' => 1,
                    'category_id' => $categoryId,
                    'user_id' => $demoUserId,
                    'source_url' => $url,
                    'source_url_hash' => $urlHash,
                    'title' => $title,
                    'price_pence' => $pricePence,
                    'rating' => $rating,
                    'availability' => 'In stock',
                    'image_url' => null,
                    'upc' => null,
                    'first_seen_at' => $now,
                    'last_seen_at' => $now,
                    'last_crawl_job_id' => null,
                ]);
            }

            return $created;
        });
    } catch (\RuntimeException $exception) {
        $this->error($exception->getMessage());

        return \Symfony\Component\Console\Command\Command::FAILURE;
    }

    foreach ($accounts as $account) {
        if ($result[$account['email']]) {
            $this->line("Created {$account['role']} account: {$account['email']} / {$account['password']}");
        } else {
            $this->line("{$account['role']} account already exists; its password was not changed.");
        }
    }
    $this->info('Demo books are ready for demo@crawlinsight.local.');

    return \Symfony\Component\Console\Command\Command::SUCCESS;
})->purpose('Create local-only admin and demo accounts with sample books.');
