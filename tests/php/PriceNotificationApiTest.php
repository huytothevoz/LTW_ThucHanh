<?php

namespace Tests;

use Illuminate\Support\Facades\DB;

class PriceNotificationApiTest extends TestCase
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
                is_active INTEGER NOT NULL DEFAULT 1,
                session_version INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT
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
                title TEXT NOT NULL
            );
            CREATE TABLE book_price_history (
                id INTEGER PRIMARY KEY,
                old_price_pence INTEGER NOT NULL,
                new_price_pence INTEGER NOT NULL,
                changed_at TEXT NOT NULL
            );
            CREATE TABLE price_change_notifications (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                book_id INTEGER NOT NULL,
                price_history_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                read_at TEXT
            );
            SQL);

        foreach ([1, 2] as $userId) {
            DB::table('users')->insert([
                'id' => $userId,
                'full_name' => "User {$userId}",
                'email' => "user{$userId}@example.com",
                'password_hash' => 'test-hash',
                'created_at' => '2026-10-23T00:00:00Z',
                'updated_at' => '2026-10-23T00:00:00Z',
            ]);
        }

        DB::table('books')->insert([
            ['id' => 1, 'title' => 'Book One'],
            ['id' => 2, 'title' => 'Book Two'],
        ]);
        DB::table('book_price_history')->insert([
            ['id' => 1, 'old_price_pence' => 1000, 'new_price_pence' => 900, 'changed_at' => '2026-10-23T00:00:00Z'],
            ['id' => 2, 'old_price_pence' => 2000, 'new_price_pence' => 2100, 'changed_at' => '2026-10-23T00:00:00Z'],
        ]);
        DB::table('price_change_notifications')->insert([
            ['id' => 1, 'user_id' => 1, 'book_id' => 1, 'price_history_id' => 1, 'created_at' => '2026-10-23T00:00:00Z', 'read_at' => null],
            ['id' => 2, 'user_id' => 2, 'book_id' => 2, 'price_history_id' => 2, 'created_at' => '2026-10-23T00:00:00Z', 'read_at' => null],
        ]);
    }

    public function test_notifications_are_scoped_to_the_signed_in_user(): void
    {
        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->getJson('/api/notifications')
            ->assertOk()
            ->assertJsonPath('unread_count', 1)
            ->assertJsonCount(1, 'items')
            ->assertJsonPath('items.0.title', 'Book One')
            ->assertJsonPath('items.0.old_price_pence', 1000)
            ->assertJsonPath('items.0.new_price_pence', 900);
    }

    public function test_notification_read_endpoints_only_update_the_signed_in_users_rows(): void
    {
        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->patchJson('/api/notifications/2/read')
            ->assertNotFound()
            ->assertJsonPath('error.code', 'NOTIFICATION_NOT_FOUND');

        $this->assertNull(DB::table('price_change_notifications')->where('id', 2)->value('read_at'));

        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->patchJson('/api/notifications/read')
            ->assertOk()
            ->assertJsonPath('ok', true);

        $this->assertNotNull(DB::table('price_change_notifications')->where('id', 1)->value('read_at'));
        $this->assertNull(DB::table('price_change_notifications')->where('id', 2)->value('read_at'));
    }
}
