<?php

declare(strict_types=1);

namespace Tests;

use App\Services\AccountService;
use Illuminate\Support\Facades\DB;

final class PasswordResetOtpFlowTest extends TestCase
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

    public function test_complete_otp_multi_step_password_reset_flow(): void
    {
        // 1. Create a user
        $this->postJson('/api/auth/register', [
            'full_name' => 'OTP Test User',
            'email' => 'otp.tester@example.com',
            'password' => 'OriginalPassword123',
        ])->assertCreated();

        // 2. Request OTP
        $response = $this->postJson('/api/auth/request-reset', [
            'email' => 'otp.tester@example.com',
        ])->assertOk()->json();

        $this->assertArrayHasKey('local_test_otp', $response);
        $otp = $response['local_test_otp'];
        $token = $response['reset_token'] ?? null;
        $this->assertNotNull($token);

        // 3. Test Verify OTP Exception Cases
        // Case a: Missing OTP
        $this->postJson('/api/auth/verify-otp', [
            'email' => 'otp.tester@example.com',
            'token' => $token,
            'otp' => '',
        ])->assertStatus(400)
            ->assertJsonPath('error.code', 'MISSING_OTP');

        // Case b: Invalid OTP length or non-numeric
        $this->postJson('/api/auth/verify-otp', [
            'email' => 'otp.tester@example.com',
            'token' => $token,
            'otp' => '12345',
        ])->assertStatus(400)
            ->assertJsonPath('error.code', 'INVALID_OTP_FORMAT');

        $this->postJson('/api/auth/verify-otp', [
            'email' => 'otp.tester@example.com',
            'token' => $token,
            'otp' => 'abcdef',
        ])->assertStatus(400)
            ->assertJsonPath('error.code', 'INVALID_OTP_FORMAT');

        // Case c: Incorrect OTP
        $this->postJson('/api/auth/verify-otp', [
            'email' => 'otp.tester@example.com',
            'token' => $token,
            'otp' => '000000',
        ])->assertStatus(400)
            ->assertJsonPath('error.code', 'INVALID_OTP');

        // Case c2: Expired OTP
        DB::table('password_reset_tokens')
            ->where('token_hash', hash('sha256', $token))
            ->update(['expires_at' => gmdate('Y-m-d\TH:i:s\Z', time() - 100)]);

        $this->postJson('/api/auth/verify-otp', [
            'email' => 'otp.tester@example.com',
            'token' => $token,
            'otp' => $otp,
        ])->assertStatus(400)
            ->assertJsonPath('error.code', 'OTP_EXPIRED');

        // Restore expiry for next test steps
        DB::table('password_reset_tokens')
            ->where('token_hash', hash('sha256', $token))
            ->update(['expires_at' => gmdate('Y-m-d\TH:i:s\Z', time() + 1200)]);

        // Case d: Correct OTP verification
        $this->postJson('/api/auth/verify-otp', [
            'email' => 'otp.tester@example.com',
            'token' => $token,
            'otp' => $otp,
        ])->assertOk()
            ->assertJsonPath('ok', true);

        // 4. Test Reset Password Validation
        // Case a: Password too short
        $this->postJson('/api/auth/reset-password', [
            'email' => 'otp.tester@example.com',
            'token' => $token,
            'otp' => $otp,
            'password' => 'Short1',
        ])->assertStatus(400)
            ->assertJsonPath('error.code', 'VALIDATION_ERROR');

        // Case b: Successful password change
        $this->postJson('/api/auth/reset-password', [
            'email' => 'otp.tester@example.com',
            'token' => $token,
            'otp' => $otp,
            'password' => 'BrandNewPassword123',
        ])->assertOk()
            ->assertJsonPath('ok', true);

        // 5. Test Replay Attack Prevention (Used OTP must be rejected)
        $this->postJson('/api/auth/verify-otp', [
            'email' => 'otp.tester@example.com',
            'token' => $token,
            'otp' => $otp,
        ])->assertStatus(400)
            ->assertJsonPath('error.code', 'OTP_ALREADY_USED');

        // 6. Verify logging in with the new password
        $this->postJson('/api/auth/login', [
            'email' => 'otp.tester@example.com',
            'password' => 'BrandNewPassword123',
        ])->assertOk();

        // Old password should fail
        $this->postJson('/api/auth/login', [
            'email' => 'otp.tester@example.com',
            'password' => 'OriginalPassword123',
        ])->assertStatus(401);
    }
}
