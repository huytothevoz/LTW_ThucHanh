<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Cookie;
use Symfony\Component\HttpFoundation\Response;

class SecurityHeaders
{
    public function handle(Request $request, Closure $next): Response
    {
        $response = $next($request);
        $response->headers->set('X-Content-Type-Options', 'nosniff');
        $response->headers->set('Referrer-Policy', 'strict-origin-when-cross-origin');
        $response->headers->set('X-Frame-Options', 'DENY');
        $response->headers->set(
            'Content-Security-Policy',
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' https://books.toscrape.com data:; font-src 'self'; connect-src 'self'; form-action 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
        );

        if ($request->is('api/*') || $request->is('reset-password/*')) {
            $response->headers->set('Cache-Control', 'no-store');
        }

        $locale = $request->attributes->get('guest_locale_cookie');
        if ($locale && !$request->attributes->get('current_user')) {
            $response->headers->setCookie(Cookie::create(
                'ci_guest_lang',
                $locale,
                time() + 31536000,
                '/',
                null,
                (bool) config('session.secure'),
                false,
                false,
                'lax',
            ));
        }

        return $response;
    }
}
