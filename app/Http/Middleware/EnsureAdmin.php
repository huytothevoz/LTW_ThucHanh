<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class EnsureAdmin
{
    public function handle(Request $request, Closure $next): Response
    {
        $user = $request->attributes->get('current_user');
        if (!$user) {
            if ($request->is('api/*')) {
                return response()->json([
                    'error' => ['code' => 'AUTH_REQUIRED', 'message' => 'Vui lòng đăng nhập để tiếp tục.'],
                ], 401);
            }

            return redirect('/login?next='.rawurlencode($request->path()));
        }
        if ($user['role'] !== 'admin') {
            if ($request->is('api/*')) {
                return response()->json([
                    'error' => ['code' => 'ADMIN_REQUIRED', 'message' => 'Bạn không có quyền quản trị.'],
                ], 403);
            }

            abort(403);
        }

        return $next($request);
    }
}
