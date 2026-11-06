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
                role TEXT NOT NULL DEFAULT 'user',
                is_active INTEGER NOT NULL DEFAULT 1,
                session_version INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT,
                avatar_path TEXT
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
            CREATE TABLE password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                token_hash TEXT NOT NULL UNIQUE,
                otp_hash TEXT,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                created_at TEXT NOT NULL
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

    public function test_password_reset_requires_the_email_otp_after_opening_the_link(): void
    {
        $this->postJson('/api/auth/register', [
            'full_name' => 'Test User',
            'email' => 'reset.user@example.com',
            'password' => 'InitialPassword123',
        ])->assertCreated();

        $reset = $this->postJson('/api/auth/request-reset', [
            'email' => 'reset.user@example.com',
        ])->assertOk()->json();
        $this->assertSame(1, preg_match('~/reset-password/([A-Za-z0-9_-]+)~', $reset['local_test_link'], $matches));
        $token = $matches[1];
        $this->assertSame(
            hash('sha256', $reset['local_test_otp']),
            DB::table('password_reset_tokens')->value('otp_hash'),
        );

        $this->get('/reset-password/'.$token)
            ->assertOk()
            ->assertSee('id="auth-otp"', false)
            ->assertSee('name="otp"', false);

        // Test verify-otp endpoint exceptions
        $this->postJson('/api/auth/verify-otp', [
            'token' => $token,
            'email' => 'reset.user@example.com',
            'otp' => '',
        ])->assertBadRequest()
            ->assertJsonPath('error.code', 'MISSING_OTP');

        $this->postJson('/api/auth/verify-otp', [
            'token' => $token,
            'email' => 'reset.user@example.com',
            'otp' => 'abc12',
        ])->assertBadRequest()
            ->assertJsonPath('error.code', 'INVALID_OTP_FORMAT');

        $this->postJson('/api/auth/verify-otp', [
            'token' => $token,
            'email' => 'reset.user@example.com',
            'otp' => '000000',
        ])->assertBadRequest()
            ->assertJsonPath('error.code', 'INVALID_OTP');

        $this->postJson('/api/auth/verify-otp', [
            'token' => $token,
            'email' => 'reset.user@example.com',
            'otp' => $reset['local_test_otp'],
        ])->assertOk()
            ->assertJsonPath('ok', true);

        $this->postJson('/api/auth/reset-password', [
            'token' => $token,
            'otp' => '000000',
            'password' => 'NewPassword123',
        ])->assertBadRequest()
            ->assertJsonPath('error.code', 'INVALID_TOKEN');

        $this->postJson('/api/auth/reset-password', [
            'token' => $token,
            'otp' => $reset['local_test_otp'],
            'password' => 'NewPassword123',
        ])->assertOk()->assertJsonPath('ok', true);

        // After password is reset, OTP cannot be verified again
        $this->postJson('/api/auth/verify-otp', [
            'token' => $token,
            'email' => 'reset.user@example.com',
            'otp' => $reset['local_test_otp'],
        ])->assertBadRequest()
            ->assertJsonPath('error.code', 'OTP_ALREADY_USED');

        $this->postJson('/api/auth/login', [
            'email' => 'reset.user@example.com',
            'password' => 'NewPassword123',
        ])->assertOk();
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
            ->assertJsonPath('user.role', 'user')
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
