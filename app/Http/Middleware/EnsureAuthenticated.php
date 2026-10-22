<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class EnsureAuthenticated
{
    public function handle(Request $request, Closure $next): Response
    {
        if (!$request->attributes->get('current_user')) {
            if ($request->is('api/*')) {
                return response()->json([
                    'error' => [
                        'code' => 'AUTH_REQUIRED',
                        'message' => 'Vui lòng đăng nhập để tiếp tục.',
                    ],
                ], 401);
            }

            return redirect('/login?next='.rawurlencode($request->path()));
        }

        return $next($request);
    }
}
