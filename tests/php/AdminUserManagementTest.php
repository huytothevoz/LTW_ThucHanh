<?php

namespace Tests;

use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\DB;

class AdminUserManagementTest extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();

        DB::unprepared(<<<'SQL'
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
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
        SQL);

        foreach ([
            [1, 'Admin', 'admin@example.com', 'admin'],
            [2, 'Regular User', 'user@example.com', 'user'],
        ] as [$id, $name, $email, $role]) {
            DB::table('users')->insert([
                'id' => $id,
                'full_name' => $name,
                'email' => $email,
                'password_hash' => 'test-hash',
                'role' => $role,
                'created_at' => '2026-10-24T00:00:00Z',
                'updated_at' => '2026-10-24T00:00:00Z',
            ]);
            DB::table('user_preferences')->insert([
                'user_id' => $id,
                'locale' => 'vi',
                'theme' => 'system',
                'book_layout' => 'grid',
                'updated_at' => '2026-10-24T00:00:00Z',
            ]);
        }
    }

    public function test_regular_users_cannot_open_the_admin_page_or_api(): void
    {
        $this->withSession(['user_id' => 2, 'session_version' => 0])
            ->get('/admin/users')
            ->assertForbidden();

        $this->withSession(['user_id' => 2, 'session_version' => 0])
            ->getJson('/api/admin/users')
            ->assertForbidden()
            ->assertJsonPath('error.code', 'ADMIN_REQUIRED');
    }

    public function test_admin_can_list_and_manage_user_status_and_role(): void
    {
        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->getJson('/api/admin/users')
            ->assertOk()
            ->assertJsonPath('total', 2)
            ->assertJsonPath('items.0.role', 'user')
            ->assertJsonMissingPath('items.0.password_hash');

        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->patchJson('/api/admin/users/2', ['is_active' => false])
            ->assertOk()
            ->assertJsonPath('user.is_active', 0);
        $this->assertDatabaseHas('users', ['id' => 2, 'session_version' => 1]);

        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->patchJson('/api/admin/users/2', ['role' => 'admin'])
            ->assertOk()
            ->assertJsonPath('user.role', 'admin');
    }

    public function test_admin_cannot_modify_their_own_account_or_remove_the_last_active_admin(): void
    {
        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->patchJson('/api/admin/users/1', ['role' => 'user'])
            ->assertBadRequest()
            ->assertJsonPath('error.code', 'SELF_MODIFICATION_NOT_ALLOWED');

        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->patchJson('/api/admin/users/1', ['is_active' => false])
            ->assertBadRequest();
    }

    public function test_operator_command_promotes_only_the_configured_active_account(): void
    {
        config(['app.admin_email' => 'user@example.com']);

        $this->assertSame(0, Artisan::call('admin:promote'));
        $this->assertDatabaseHas('users', [
            'id' => 2,
            'role' => 'admin',
            'session_version' => 1,
        ]);
    }
}
