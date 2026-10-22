<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Symfony\Component\HttpFoundation\Response;

class ResolveIdentity
{
    public function handle(Request $request, Closure $next): Response
    {
        $user = null;
        $userId = $request->session()->get('user_id');

        if (is_int($userId) || (is_string($userId) && ctype_digit($userId))) {
            $user = DB::selectOne(
                'SELECT id,full_name,email,created_at,last_login_at,is_active,session_version FROM users WHERE id=? AND is_active=1',
                [(int) $userId],
            );

            if (!$user || (int) $request->session()->get('session_version', -1) !== (int) $user->session_version) {
                $request->session()->invalidate();
                $request->session()->regenerateToken();
                $user = null;
            }
        }

        $preferences = $user
            ? $this->preferences((int) $user->id)
            : $this->guestPreferences($request);

        $request->attributes->set('current_user', $user ? $this->publicUser($user) : null);
        $request->attributes->set('preferences', $preferences);
        $request->attributes->set('locale', $preferences['locale']);
        app()->setLocale($preferences['locale']);

        if (!$user && in_array($request->query('lang'), ['vi', 'en'], true)) {
            $request->attributes->set('guest_locale_cookie', $request->query('lang'));
        }

        return $next($request);
    }

    private function preferences(int $userId): array
    {
        $row = DB::selectOne(
            'SELECT locale,theme,book_layout FROM user_preferences WHERE user_id=?',
            [$userId],
        );

        return $row ? (array) $row : ['locale' => 'vi', 'theme' => 'system', 'book_layout' => 'grid'];
    }

    private function guestPreferences(Request $request): array
    {
        $locale = $request->query('lang') ?? $request->cookie('ci_guest_lang', 'vi');

        return [
            'locale' => $locale === 'en' ? 'en' : 'vi',
            'theme' => 'system',
            'book_layout' => 'grid',
        ];
    }

    private function publicUser(object $user): array
    {
        return [
            'id' => (int) $user->id,
            'full_name' => $user->full_name,
            'email' => $user->email,
            'created_at' => $user->created_at,
            'last_login_at' => $user->last_login_at,
            'is_active' => (int) $user->is_active,
        ];
    }
}
