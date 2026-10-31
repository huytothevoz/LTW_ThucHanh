<?php

namespace App\Services;

use Illuminate\Support\Facades\DB;
use function Vinsaj9\Crypto\Scrypt\scrypt;

class AccountService
{
    private const SCRYPT_N = 16384;

    public static function now(): string
    {
        return gmdate('Y-m-d\TH:i:s\Z');
    }

    public static function publicUser(?object $row): ?array
    {
        if (!$row) {
            return null;
        }

        return [
            'id' => (int) $row->id,
            'full_name' => $row->full_name,
            'email' => $row->email,
            'created_at' => $row->created_at,
            'last_login_at' => $row->last_login_at,
            'is_active' => (int) $row->is_active,
            'role' => property_exists($row, 'role') ? $row->role : 'user',
        ];
    }

    public static function register(mixed $fullName, mixed $email, mixed $password): array
    {
        if (!is_string($fullName) || !is_string($email)) {
            throw new \DomainException('Tên hoặc email không hợp lệ.');
        }
        $name = preg_replace('/\s+/u', ' ', trim($fullName)) ?? '';
        $mail = strtolower(trim($email));
        self::validateName($name);
        self::validateEmail($mail);
        self::validatePassword($password);

        return DB::transaction(function () use ($name, $mail, $password): array {
            if (DB::selectOne('SELECT id FROM users WHERE email=?', [$mail])) {
                throw new \DomainException('Email này đã được đăng ký.');
            }

            $now = self::now();
            $id = DB::table('users')->insertGetId([
                'full_name' => $name,
                'email' => $mail,
                'password_hash' => self::hashPassword($password),
                'created_at' => $now,
                'updated_at' => $now,
            ]);
            DB::table('user_preferences')->insert([
                'user_id' => $id,
                'locale' => 'vi',
                'theme' => 'system',
                'book_layout' => 'grid',
                'updated_at' => $now,
            ]);

            return self::publicUser(DB::selectOne('SELECT * FROM users WHERE id=?', [$id]));
        });
    }

    public static function authenticate(mixed $email, mixed $password): ?array
    {
        if (!is_string($email)) {
            return null;
        }
        $mail = substr(strtolower(trim($email)), 0, 254);
        $row = DB::selectOne('SELECT * FROM users WHERE email=? AND is_active=1', [$mail]);
        if (!$row || !is_string($password) || !self::verifyPassword($password, $row->password_hash)) {
            return null;
        }

        $now = self::now();
        if (str_starts_with($row->password_hash, 'scrypt:')) {
            DB::update(
                'UPDATE users SET password_hash=?,updated_at=?,last_login_at=? WHERE id=?',
                [self::hashPassword($password), $now, $now, $row->id],
            );
        } else {
            DB::update('UPDATE users SET last_login_at=? WHERE id=?', [$now, $row->id]);
        }

        return self::publicUser(DB::selectOne('SELECT * FROM users WHERE id=?', [$row->id]));
    }

    public static function sessionVersion(int $userId): ?int
    {
        $row = DB::selectOne('SELECT session_version FROM users WHERE id=? AND is_active=1', [$userId]);

        return $row ? (int) $row->session_version : null;
    }

    public static function preferences(int $userId): array
    {
        $row = DB::selectOne(
            'SELECT locale,theme,book_layout FROM user_preferences WHERE user_id=?',
            [$userId],
        );

        return $row ? (array) $row : ['locale' => 'vi', 'theme' => 'system', 'book_layout' => 'grid'];
    }

    public static function updateProfile(int $userId, mixed $name): array
    {
        if (!is_string($name)) {
            throw new \DomainException('Tên không hợp lệ.');
        }
        $clean = preg_replace('/\s+/u', ' ', trim($name)) ?? '';
        self::validateName($clean);
        DB::update('UPDATE users SET full_name=?,updated_at=? WHERE id=?', [$clean, self::now(), $userId]);

        return self::publicUser(DB::selectOne('SELECT * FROM users WHERE id=? AND is_active=1', [$userId]));
    }

    public static function updatePreferences(int $userId, mixed $values): array
    {
        $allowed = [
            'locale' => ['vi', 'en'],
            'theme' => ['light', 'dark', 'system'],
            'book_layout' => ['grid', 'list'],
        ];
        if (!is_array($values) || !$values || array_diff(array_keys($values), array_keys($allowed))) {
            throw new \DomainException('Cấu hình không hợp lệ.');
        }

        foreach ($values as $key => $value) {
            if (!is_string($value) || !in_array($value, $allowed[$key], true)) {
                throw new \DomainException("Giá trị {$key} không hợp lệ.");
            }
        }
        DB::transaction(function () use ($values, $userId): void {
            foreach ($values as $key => $value) {
                DB::update(
                    "UPDATE user_preferences SET {$key}=?,updated_at=? WHERE user_id=?",
                    [$value, self::now(), $userId],
                );
            }
        });

        return self::preferences($userId);
    }

    public static function changePassword(int $userId, mixed $current, mixed $next): void
    {
        self::validatePassword($next);
        DB::transaction(function () use ($userId, $current, $next): void {
            $row = DB::selectOne('SELECT password_hash FROM users WHERE id=?', [$userId]);
            if (!$row || !is_string($current) || !self::verifyPassword($current, $row->password_hash)) {
                throw new \DomainException('Mật khẩu hiện tại không đúng.');
            }

            DB::update(
                'UPDATE users SET password_hash=?,session_version=session_version+1,updated_at=? WHERE id=?',
                [self::hashPassword($next), self::now(), $userId],
            );
            DB::update(
                'UPDATE password_reset_tokens SET used_at=? WHERE user_id=? AND used_at IS NULL',
                [self::now(), $userId],
            );
        });
    }

    public static function createResetToken(string $email): ?array
    {
        return DB::transaction(function () use ($email): ?array {
            $user = DB::selectOne('SELECT * FROM users WHERE email=? AND is_active=1', [strtolower(trim($email))]);
            if (!$user) {
                return null;
            }

            $token = rtrim(strtr(base64_encode(random_bytes(36)), '+/', '-_'), '=');
            $otp = sprintf('%06d', random_int(100000, 999999));
            $now = self::now();
            $expiry = gmdate('Y-m-d\TH:i:s\Z', time() + 20 * 60);
            DB::update(
                'UPDATE password_reset_tokens SET used_at=? WHERE user_id=? AND used_at IS NULL',
                [$now, $user->id],
            );
            DB::insert(
                'INSERT INTO password_reset_tokens(user_id,token_hash,expires_at,created_at) VALUES(?,?,?,?)',
                [$user->id, hash('sha256', $token), $expiry, $now],
            );

            return ['token' => $token, 'otp' => $otp, 'user' => self::publicUser($user)];
        });
    }

    public static function resetPassword(mixed $token, mixed $password): bool
    {
        self::validatePassword($password);
        if (!is_string($token) || strlen($token) < 24 || strlen($token) > 200) {
            return false;
        }

        return DB::transaction(function () use ($token, $password): bool {
            $row = DB::selectOne(
                'SELECT id,user_id,expires_at,used_at FROM password_reset_tokens WHERE token_hash=?',
                [hash('sha256', $token)],
            );
            if (!$row || $row->used_at || $row->expires_at <= self::now()) {
                return false;
            }

            $now = self::now();
            DB::update(
                'UPDATE users SET password_hash=?,session_version=session_version+1,updated_at=? WHERE id=?',
                [self::hashPassword($password), $now, $row->user_id],
            );
            DB::update(
                'UPDATE password_reset_tokens SET used_at=? WHERE user_id=? AND used_at IS NULL',
                [$now, $row->user_id],
            );

            return true;
        });
    }

    public static function rateLimited(string $subject, int $maxAttempts, int $minutes): bool
    {
        $cutoff = gmdate('Y-m-d\TH:i:s\Z', time() - $minutes * 60);
        $row = DB::selectOne(
            'SELECT COUNT(*) AS attempts FROM auth_attempts WHERE subject_hash=? AND attempted_at>? AND success=0',
            [hash('sha256', $subject), $cutoff],
        );

        return (int) $row->attempts >= $maxAttempts;
    }

    public static function recordAuthAttempt(string $subject, bool $success): void
    {
        $now = self::now();
        DB::insert(
            'INSERT INTO auth_attempts(subject_hash,attempted_at,success) VALUES(?,?,?)',
            [hash('sha256', $subject), $now, $success ? 1 : 0],
        );
        DB::delete('DELETE FROM auth_attempts WHERE attempted_at < ?', [gmdate('Y-m-d\TH:i:s\Z', time() - 2 * 86400)]);
    }

    public static function bookmarkIds(int $userId, array $bookIds): array
    {
        if (!$bookIds) {
            return [];
        }
        $placeholders = implode(',', array_fill(0, count($bookIds), '?'));
        $rows = DB::select(
            "SELECT book_id FROM bookmarks WHERE user_id=? AND book_id IN ({$placeholders})",
            [$userId, ...$bookIds],
        );

        return array_map(static fn (object $row): int => (int) $row->book_id, $rows);
    }

    public static function addBookmark(int $userId, int $bookId): bool
    {
        if (!DB::selectOne('SELECT id FROM books WHERE id=? AND user_id=?', [$bookId, $userId])) {
            return false;
        }
        DB::table('bookmarks')->insertOrIgnore([
            'user_id' => $userId,
            'book_id' => $bookId,
            'created_at' => self::now(),
        ]);

        return true;
    }

    public static function removeBookmark(int $userId, int $bookId): void
    {
        DB::delete('DELETE FROM bookmarks WHERE user_id=? AND book_id=?', [$userId, $bookId]);
    }

    public static function listBookmarks(int $userId, int $page): array
    {
        if ($page < 1 || $page > 100000) {
            throw new \DomainException('Trang không hợp lệ.');
        }
        $total = (int) DB::scalar('SELECT COUNT(*) FROM bookmarks WHERE user_id=?', [$userId]);
        $items = DB::select(
            'SELECT b.id,b.title,b.price_pence,b.rating,b.availability,b.source_url,b.image_url,c.name AS category,
                    bk.note,bk.created_at AS bookmarked_at
             FROM bookmarks bk
             JOIN books b ON b.id=bk.book_id
             JOIN categories c ON b.category_id=c.id
             WHERE bk.user_id=? AND b.user_id=?
             ORDER BY bk.created_at DESC,bk.id DESC LIMIT 12 OFFSET ?',
            [$userId, $userId, ($page - 1) * 12],
        );

        return [
            'items' => array_map(static fn (object $row): array => (array) $row, $items),
            'total' => $total,
            'page' => $page,
            'page_size' => 12,
            'total_pages' => (int) ceil($total / 12),
        ];
    }

    public static function saveSearch(int $userId, mixed $name, mixed $query, mixed $low, mixed $high): array
    {
        if (!is_string($name) || !is_string($query) || !is_string($low) || !is_string($high)) {
            throw new \DomainException('Dữ liệu bộ lọc không hợp lệ.');
        }
        $cleanName = preg_replace('/\s+/u', ' ', trim($name)) ?? '';
        $query = (string) $query;
        $low = (string) $low;
        $high = (string) $high;
        if (mb_strlen($cleanName) < 1 || mb_strlen($cleanName) > 60 || mb_strlen($query) > 100) {
            throw new \DomainException('Tên bộ lọc hoặc từ khóa quá dài.');
        }
        $min = self::parsePrice($low, 'min_price');
        $max = self::parsePrice($high, 'max_price');
        if ($min !== null && $max !== null && $min > $max) {
            throw new \DomainException('Khoảng giá không hợp lệ.');
        }
        if ((int) DB::scalar('SELECT COUNT(*) FROM saved_searches WHERE user_id=?', [$userId]) >= 20) {
            throw new \DomainException('Tối đa 20 bộ lọc đã lưu.');
        }
        $id = DB::table('saved_searches')->insertGetId([
            'user_id' => $userId,
            'name' => $cleanName,
            'query' => $query,
            'min_price' => $low,
            'max_price' => $high,
            'created_at' => self::now(),
        ]);

        return ['id' => $id, 'name' => $cleanName];
    }

    public static function parsePrice(string $value, string $key): ?int
    {
        if ($value === '') {
            return null;
        }
        if (!preg_match('/^(?:0|[1-9]\d{0,3})(?:\.\d{1,2})?$/D', $value)) {
            throw new \DomainException("{$key} must be GBP 0–9999.99 with up to 2 decimals");
        }
        [$pounds, $pence] = array_pad(explode('.', $value, 2), 2, '0');
        $cents = (int) ($pounds * 100) + (int) str_pad($pence, 2, '0');
        if ($cents > 999999) {
            throw new \DomainException("{$key} is out of range");
        }

        return $cents;
    }

    public static function deleteSearch(int $userId, int $searchId): bool
    {
        return DB::delete('DELETE FROM saved_searches WHERE id=? AND user_id=?', [$searchId, $userId]) > 0;
    }

    private static function validateName(string $name): void
    {
        $length = mb_strlen($name);
        if ($length < 2 || $length > 100) {
            throw new \DomainException('Tên phải dài từ 2 đến 100 ký tự.');
        }
    }

    private static function validateEmail(string $email): void
    {
        if (strlen($email) > 254 || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
            throw new \DomainException('Email không hợp lệ.');
        }
    }

    private static function validatePassword(mixed $password): void
    {
        if (
            !is_string($password)
            || mb_strlen($password) < 10
            || mb_strlen($password) > 128
            || !preg_match('/[A-Za-z]/', $password)
            || !preg_match('/\d/', $password)
        ) {
            throw new \DomainException('Mật khẩu cần 10–128 ký tự, có chữ cái và số.');
        }
    }

    private static function hashPassword(string $password): string
    {
        if (defined('PASSWORD_ARGON2ID')) {
            $hash = password_hash($password, PASSWORD_ARGON2ID);
            if ($hash === false) {
                throw new \RuntimeException('Could not hash password.');
            }

            return $hash;
        }

        $salt = random_bytes(16);
        $derived = scrypt($password, $salt, self::SCRYPT_N, 8, 1, 64);

        return 'scrypt:16384:8:1$'.bin2hex($salt).'$'.$derived;
    }

    private static function verifyPassword(string $password, string $stored): bool
    {
        $parts = explode('$', $stored);
        if (count($parts) !== 3 || $parts[0] !== 'scrypt:16384:8:1') {
            return password_verify($password, $stored);
        }
        $salt = hex2bin($parts[1]);
        if (
            $salt === false
            || strlen($salt) !== 16
            || !preg_match('/^(?:[a-f0-9]{128}|[a-f0-9]{256})$/D', $parts[2])
        ) {
            return false;
        }

        $derived = scrypt($password, $salt, self::SCRYPT_N, 8, 1, 64);
        $expected = strlen($parts[2]) === 256 ? bin2hex($derived) : $derived;

        return hash_equals($parts[2], $expected);
    }
}
