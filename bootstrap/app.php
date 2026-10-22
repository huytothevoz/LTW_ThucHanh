<?php

use App\Http\Middleware\ResolveIdentity;
use App\Http\Middleware\SecurityHeaders;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Illuminate\Http\Request;
use Illuminate\Session\TokenMismatchException;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        commands: __DIR__.'/../routes/console.php',
        health: '/up',
    )
    ->withMiddleware(function (Middleware $middleware): void {
        $middleware->web(append: [ResolveIdentity::class, SecurityHeaders::class]);
        $middleware->alias([
            'authenticated' => \App\Http\Middleware\EnsureAuthenticated::class,
        ]);
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        $exceptions->render(function (TokenMismatchException $exception, Request $request) {
            if ($request->is('api/*')) {
                return response()->json([
                    'error' => [
                        'code' => 'INVALID_CSRF',
                        'message' => 'Phiên bảo mật không hợp lệ. Vui lòng tải lại trang.',
                    ],
                ], 403);
            }

            return null;
        });
    })->create();
