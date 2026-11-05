<?php

namespace Tests;

use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\DB;

class AvatarUploadTest extends TestCase
{
    private string $avatarDirectory;

    protected function setUp(): void
    {
        parent::setUp();

        $this->avatarDirectory = storage_path('framework/testing/avatars-'.bin2hex(random_bytes(6)));
        putenv('AVATAR_STORAGE_PATH='.$this->avatarDirectory);
        $_ENV['AVATAR_STORAGE_PATH'] = $this->avatarDirectory;
        $_SERVER['AVATAR_STORAGE_PATH'] = $this->avatarDirectory;

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
            CREATE TABLE user_preferences (
                user_id INTEGER PRIMARY KEY,
                locale TEXT NOT NULL,
                theme TEXT NOT NULL,
                book_layout TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            SQL);
        DB::table('users')->insert([
            'id' => 1,
            'full_name' => 'Avatar User',
            'email' => 'avatar@example.com',
            'password_hash' => 'test-hash',
            'created_at' => '2026-11-05T00:00:00Z',
            'updated_at' => '2026-11-05T00:00:00Z',
        ]);
        DB::table('user_preferences')->insert([
            'user_id' => 1,
            'locale' => 'vi',
            'theme' => 'system',
            'book_layout' => 'grid',
            'updated_at' => '2026-11-05T00:00:00Z',
        ]);
    }

    protected function tearDown(): void
    {
        if (is_dir($this->avatarDirectory)) {
            foreach (glob($this->avatarDirectory.DIRECTORY_SEPARATOR.'*') ?: [] as $file) {
                if (is_file($file)) {
                    unlink($file);
                }
            }
            rmdir($this->avatarDirectory);
        }
        putenv('AVATAR_STORAGE_PATH');
        unset($_ENV['AVATAR_STORAGE_PATH'], $_SERVER['AVATAR_STORAGE_PATH']);

        parent::tearDown();
    }

    public function test_user_can_upload_and_retrieve_their_cropped_avatar(): void
    {
        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->post('/api/me/avatar', ['avatar' => UploadedFile::fake()->createWithContent('avatar.png', $this->png512())])
            ->assertOk()
            ->assertJsonPath('avatar_url', '/api/me/avatar');

        $filename = DB::table('users')->where('id', 1)->value('avatar_path');
        $this->assertMatchesRegularExpression('/^[a-f0-9]{48}\.png$/', $filename);
        $this->assertFileExists($this->avatarDirectory.DIRECTORY_SEPARATOR.$filename);
        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->getJson('/api/auth/me')
            ->assertOk()
            ->assertJsonPath('user.avatar_url', '/api/me/avatar');

        $response = $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->get('/api/me/avatar')
            ->assertOk()
            ->assertHeader('content-type', 'image/png');
        $this->assertStringContainsString('no-store', (string) $response->headers->get('Cache-Control'));
    }

    public function test_non_image_upload_is_rejected(): void
    {
        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->post('/api/me/avatar', ['avatar' => UploadedFile::fake()->createWithContent('invalid.png', 'not an image')])
            ->assertStatus(422)
            ->assertJsonPath('error.code', 'INVALID_AVATAR');

        $this->assertNull(DB::table('users')->where('id', 1)->value('avatar_path'));
    }

    private function png512(): string
    {
        $chunk = static function (string $type, string $data): string {
            return pack('N', strlen($data)).$type.$data.pack('N', crc32($type.$data));
        };
        $row = "\0".str_repeat("\x44\x88\xcc\xff", 512);

        return "\x89PNG\r\n\x1a\n"
            .$chunk('IHDR', pack('NNCCCCC', 512, 512, 8, 6, 0, 0, 0))
            .$chunk('IDAT', gzcompress(str_repeat($row, 512)))
            .$chunk('IEND', '');
    }
}
