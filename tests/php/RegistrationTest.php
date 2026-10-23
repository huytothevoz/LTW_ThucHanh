<?php

namespace Tests;

use Illuminate\Support\Facades\DB;

class RegistrationTest extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();

        DB::unprepared(<<<'SQL'
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                session_version INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT
            );
            CREATE TABLE user_preferences (
                user_id INTEGER PRIMARY KEY REFERENCES users(id),
                locale TEXT NOT NULL,
                theme TEXT NOT NULL,
                book_layout TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE auth_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_hash TEXT NOT NULL,
                attempted_at TEXT NOT NULL,
                success INTEGER NOT NULL
            );
            SQL);
    }

    public function test_registration_page_renders_the_required_form_fields(): void
    {
        $this->get('/register')
            ->assertOk()
            ->assertSee('data-mode="register"', false)
            ->assertSee('name="full_name"', false)
            ->assertSee('name="email"', false)
            ->assertSee('name="password"', false)
            ->assertSee('name="confirm"', false);
    }

    public function test_user_can_register_and_log_in_with_the_created_account(): void
    {
        $this->postJson('/api/auth/register', [
            'full_name' => 'Test User',
            'email' => 'test.user@example.com',
            'password' => 'TestPassword123',
        ])->assertCreated()
            ->assertJsonPath('user.full_name', 'Test User')
            ->assertJsonPath('user.email', 'test.user@example.com')
            ->assertJsonPath('preferences.locale', 'vi');

        $passwordHash = DB::table('users')->value('password_hash');
        if (defined('PASSWORD_ARGON2ID')) {
            $this->assertSame('argon2id', password_get_info($passwordHash)['algoName']);
        } else {
            $this->assertMatchesRegularExpression('/^scrypt:16384:8:1\$[a-f0-9]{32}\$[a-f0-9]{128}$/D', $passwordHash);
        }
        $this->assertDatabaseHas('user_preferences', [
            'user_id' => 1,
            'locale' => 'vi',
            'theme' => 'system',
            'book_layout' => 'grid',
        ]);

        $this->postJson('/api/auth/login', [
            'email' => 'test.user@example.com',
            'password' => 'TestPassword123',
        ])->assertOk()
            ->assertJsonPath('user.email', 'test.user@example.com');
    }

    public function test_registration_rejects_invalid_password_without_creating_an_account(): void
    {
        $this->postJson('/api/auth/register', [
            'full_name' => 'Test User',
            'email' => 'test.user@example.com',
            'password' => 'short',
        ])->assertBadRequest()
            ->assertJsonPath('error.code', 'VALIDATION_ERROR');

        $this->assertDatabaseCount('users', 0);
    }
}
