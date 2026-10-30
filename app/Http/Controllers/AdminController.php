<?php

namespace App\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class AdminController
{
    public function users(Request $request): JsonResponse
    {
        $pageValue = $request->query('page', '1');
        $query = $request->query('q', '');
        if (!\is_string($pageValue) || !ctype_digit($pageValue)
            || !\is_string($query) || mb_strlen($query) > 100) {
            return $this->error('INVALID_FILTER', 'Bộ lọc người dùng không hợp lệ.', 400);
        }
        $page = (int) $pageValue;
        if ($page < 1 || $page > 100000) {
            return $this->error('INVALID_PAGE', 'Trang không hợp lệ.', 400);
        }

        $query = trim($query);
        $where = '';
        $bindings = [];
        if ($query !== '') {
            $where = ' WHERE full_name LIKE ? OR email LIKE ?';
            $pattern = '%'.$query.'%';
            $bindings = [$pattern, $pattern];
        }
        $total = (int) DB::scalar('SELECT COUNT(*) FROM users'.$where, $bindings);
        $users = DB::select(
            'SELECT id,full_name,email,role,is_active,created_at,last_login_at FROM users'
            .$where.' ORDER BY id DESC LIMIT 20 OFFSET ?',
            [...$bindings, ($page - 1) * 20],
        );

        return response()->json([
            'items' => array_map(static fn (object $user): array => (array) $user, $users),
            'total' => $total,
            'page' => $page,
            'page_size' => 20,
            'total_pages' => (int) ceil($total / 20),
        ]);
    }

    public function updateUser(Request $request, int $userId): JsonResponse
    {
        $data = $request->json()->all();
        $hasActive = \array_key_exists('is_active', $data);
        $hasRole = \array_key_exists('role', $data);
        if ($hasActive === $hasRole
            || ($hasActive && !\is_bool($data['is_active']))
            || ($hasRole && !\in_array($data['role'], ['user', 'admin'], true))) {
            return $this->error('VALIDATION_ERROR', 'Thay đổi trạng thái hoặc quyền không hợp lệ.', 400);
        }

        $actor = $request->attributes->get('current_user');
        if ((int) $actor['id'] === $userId) {
            return $this->error('SELF_MODIFICATION_NOT_ALLOWED', 'Không thể tự thay đổi tài khoản quản trị đang sử dụng.', 400);
        }
        return DB::transaction(function () use ($userId, $hasActive, $hasRole, $data): JsonResponse {
            $target = DB::selectOne('SELECT id,role,is_active FROM users WHERE id=?', [$userId]);
            if (!$target) {
                return $this->error('USER_NOT_FOUND', 'Không tìm thấy tài khoản.', 404);
            }

            $removesActiveAdmin = $target->role === 'admin'
                && (int) $target->is_active === 1
                && (($hasActive && $data['is_active'] === false) || ($hasRole && $data['role'] === 'user'));
            if ($removesActiveAdmin
                && (int) DB::scalar("SELECT COUNT(*) FROM users WHERE role='admin' AND is_active=1") <= 1) {
                return $this->error('LAST_ADMIN', 'Không thể vô hiệu hóa hoặc hạ quyền admin đang hoạt động cuối cùng.', 409);
            }

            $updates = $hasActive ? ['is_active' => $data['is_active'] ? 1 : 0] : ['role' => $data['role']];
            $updates['session_version'] = DB::raw('session_version+1');
            $updates['updated_at'] = gmdate('Y-m-d\TH:i:s\Z');
            DB::table('users')->where('id', $userId)->update($updates);

            return response()->json([
                'user' => (array) DB::selectOne(
                    'SELECT id,full_name,email,role,is_active,created_at,last_login_at FROM users WHERE id=?',
                    [$userId],
                ),
            ]);
        });
    }

    private function error(string $code, string $message, int $status): JsonResponse
    {
        return response()->json(['error' => ['code' => $code, 'message' => $message]], $status);
    }
}
