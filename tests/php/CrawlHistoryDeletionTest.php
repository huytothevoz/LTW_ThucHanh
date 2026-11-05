<?php

namespace Tests;

use Illuminate\Support\Facades\DB;

class CrawlHistoryDeletionTest extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();

        DB::unprepared(<<<'SQL'
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_active INTEGER NOT NULL DEFAULT 1,
                session_version INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT,
                avatar_path TEXT
            );
            CREATE TABLE crawl_jobs (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE user_preferences (
                user_id INTEGER PRIMARY KEY,
                locale TEXT NOT NULL,
                theme TEXT NOT NULL,
                book_layout TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE books (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                last_crawl_job_id INTEGER,
                title TEXT NOT NULL
            );
            CREATE TABLE book_price_history (
                id INTEGER PRIMARY KEY,
                job_id INTEGER NOT NULL
            );
            CREATE TABLE price_change_notifications (
                id INTEGER PRIMARY KEY,
                price_history_id INTEGER NOT NULL
            );
            CREATE TABLE crawl_job_books (
                id INTEGER PRIMARY KEY,
                job_id INTEGER NOT NULL
            );
            CREATE TABLE crawl_events (
                id INTEGER PRIMARY KEY,
                job_id INTEGER NOT NULL
            );
            CREATE TABLE crawl_pages (
                id INTEGER PRIMARY KEY,
                job_id INTEGER NOT NULL
            );
            CREATE TABLE crawl_notifications (
                id INTEGER PRIMARY KEY,
                job_id INTEGER NOT NULL
            );
            SQL);

        foreach ([1, 2] as $userId) {
            DB::table('users')->insert([
                'id' => $userId,
                'full_name' => "User {$userId}",
                'email' => "user{$userId}@example.com",
                'password_hash' => 'test-hash',
                'created_at' => '2026-11-05T00:00:00Z',
                'updated_at' => '2026-11-05T00:00:00Z',
            ]);
            DB::table('user_preferences')->insert([
                'user_id' => $userId,
                'locale' => 'vi',
                'theme' => 'system',
                'book_layout' => 'grid',
                'updated_at' => '2026-11-05T00:00:00Z',
            ]);
        }

        DB::table('crawl_jobs')->insert([
            ['id' => 10, 'user_id' => 1, 'status' => 'COMPLETED'],
            ['id' => 11, 'user_id' => 1, 'status' => 'RUNNING'],
            ['id' => 12, 'user_id' => 2, 'status' => 'COMPLETED'],
        ]);
        DB::table('books')->insert([
            ['id' => 1, 'user_id' => 1, 'last_crawl_job_id' => 10, 'title' => 'Keep this book'],
            ['id' => 2, 'user_id' => 2, 'last_crawl_job_id' => 12, 'title' => 'Other user book'],
        ]);
        DB::table('book_price_history')->insert([
            ['id' => 20, 'job_id' => 10],
            ['id' => 21, 'job_id' => 12],
        ]);
        DB::table('price_change_notifications')->insert([
            ['id' => 30, 'price_history_id' => 20],
            ['id' => 31, 'price_history_id' => 21],
        ]);
        foreach (['crawl_job_books', 'crawl_events', 'crawl_pages', 'crawl_notifications'] as $table) {
            DB::table($table)->insert([
                ['id' => 1, 'job_id' => 10],
                ['id' => 2, 'job_id' => 12],
            ]);
        }
    }

    public function test_owner_can_delete_completed_history_without_deleting_books(): void
    {
        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->deleteJson('/api/jobs/10')
            ->assertOk()
            ->assertExactJson(['ok' => true]);

        $this->assertDatabaseMissing('crawl_jobs', ['id' => 10]);
        $this->assertDatabaseHas('crawl_jobs', ['id' => 12]);
        $this->assertDatabaseHas('books', ['id' => 1, 'title' => 'Keep this book', 'last_crawl_job_id' => null]);
        $this->assertDatabaseHas('books', ['id' => 2, 'last_crawl_job_id' => 12]);

        foreach (['book_price_history', 'crawl_job_books', 'crawl_events', 'crawl_pages', 'crawl_notifications'] as $table) {
            $this->assertDatabaseMissing($table, ['job_id' => 10]);
        }
        $this->assertDatabaseMissing('price_change_notifications', ['price_history_id' => 20]);
        $this->assertDatabaseHas('price_change_notifications', ['price_history_id' => 21]);
        $this->assertDatabaseHas('crawl_events', ['job_id' => 12]);
    }

    public function test_user_cannot_delete_another_users_crawl_history(): void
    {
        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->deleteJson('/api/jobs/12')
            ->assertNotFound()
            ->assertJsonPath('error.code', 'JOB_NOT_FOUND');

        $this->assertDatabaseHas('crawl_jobs', ['id' => 12, 'user_id' => 2]);
    }

    public function test_active_crawl_cannot_be_deleted(): void
    {
        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->deleteJson('/api/jobs/11')
            ->assertStatus(409)
            ->assertJsonPath('error.code', 'JOB_ALREADY_ACTIVE');

        $this->assertDatabaseHas('crawl_jobs', ['id' => 11, 'status' => 'RUNNING']);
    }
}
