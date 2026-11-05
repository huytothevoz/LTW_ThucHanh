<?php

namespace Tests;

use App\Services\AccountService;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\DB;

class DemoAccountsTest extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();

        DB::unprepared(<<<'SQL'
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_active INTEGER NOT NULL DEFAULT 1,
                session_version INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT,
                avatar_path TEXT
            );
            CREATE TABLE user_preferences (
                user_id INTEGER PRIMARY KEY,
                locale TEXT NOT NULL,
                theme TEXT NOT NULL,
                book_layout TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE sources (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            CREATE TABLE categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                UNIQUE(source_id, name)
            );
            CREATE TABLE books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                source_url TEXT NOT NULL,
                source_url_hash TEXT NOT NULL,
                title TEXT NOT NULL,
                price_pence INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                availability TEXT NOT NULL,
                image_url TEXT,
                upc TEXT,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                last_crawl_job_id INTEGER,
                UNIQUE(user_id, source_url_hash)
            );
        SQL);
        DB::table('sources')->insert(['id' => 1, 'name' => 'Books to Scrape']);
    }

    public function test_local_setup_seeds_two_accounts_and_demo_books_idempotently(): void
    {
        config(['app.env' => 'local']);

        $this->assertSame(0, Artisan::call('app:seed-demo'));
        $this->assertDatabaseHas('users', [
            'email' => 'admin@crawlinsight.local',
            'role' => 'admin',
        ]);
        $this->assertDatabaseHas('users', [
            'email' => 'demo@crawlinsight.local',
            'role' => 'user',
        ]);

        $admin = AccountService::authenticate('admin@crawlinsight.local', 'CrawlInsightAdmin2026!');
        $demo = AccountService::authenticate('demo@crawlinsight.local', 'CrawlInsightDemo2026!');
        $this->assertSame('admin', $admin['role']);
        $this->assertSame('user', $demo['role']);
        $this->assertSame(5, DB::table('books')->where('user_id', $demo['id'])->count());
        $this->assertSame(0, DB::table('books')->where('user_id', $admin['id'])->count());

        $adminHash = DB::table('users')->where('id', $admin['id'])->value('password_hash');
        $demoHash = DB::table('users')->where('id', $demo['id'])->value('password_hash');
        $this->assertNotSame('CrawlInsightAdmin2026!', $adminHash);
        $this->assertNotSame('CrawlInsightDemo2026!', $demoHash);

        $this->assertSame(0, Artisan::call('app:seed-demo'));
        $this->assertSame($adminHash, DB::table('users')->where('id', $admin['id'])->value('password_hash'));
        $this->assertSame($demoHash, DB::table('users')->where('id', $demo['id'])->value('password_hash'));
        $this->assertSame(5, DB::table('books')->where('user_id', $demo['id'])->count());
    }

    public function test_default_accounts_are_not_created_outside_local_environment(): void
    {
        config(['app.env' => 'production']);

        $this->assertSame(1, Artisan::call('app:seed-demo'));
        $this->assertSame(0, DB::table('users')->count());
    }
}
