<?php

use App\Http\Controllers\ApiController;
use App\Http\Controllers\AdminController;
use App\Http\Controllers\PageController;
use App\Http\Controllers\StaticAssetController;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;

Route::get('/static/{path}', StaticAssetController::class)->where('path', '.*');

Route::get('/', fn (Request $request, PageController $pages) => $pages->show($request, 'index.html'))
    ->name('home');
Route::get('/login', [PageController::class, 'login']);
Route::get('/register', [PageController::class, 'register']);
Route::get('/forgot-password', fn (Request $request, PageController $pages) => $pages->show($request, 'auth.html', null, ['mode' => 'forgot']));
Route::get('/reset-password/{token}', fn (Request $request, PageController $pages, string $token) => $pages->show($request, 'auth.html', null, ['mode' => 'reset', 'reset_token' => $token]));

Route::middleware('authenticated')->group(function (): void {
    Route::get('/workspace', fn (Request $request, PageController $pages) => $pages->show($request, 'dashboard.html', 'overview'));
    Route::get('/books', fn (Request $request, PageController $pages) => $pages->show($request, 'books.html', 'catalog'));
    Route::get('/saved', fn (Request $request, PageController $pages) => $pages->show($request, 'saved.html', 'bookmarks'));
    Route::get('/history', fn (Request $request, PageController $pages) => $pages->show($request, 'history.html', 'history'));
    Route::get('/analytics', fn (Request $request, PageController $pages) => $pages->show($request, 'analytics.html', 'analytics'));
    Route::get('/sources', fn (Request $request, PageController $pages) => $pages->show($request, 'sources.html', 'sources'));
    Route::get('/settings', fn (Request $request, PageController $pages) => $pages->show($request, 'settings.html', 'settings'));
    Route::get('/help', fn (Request $request, PageController $pages) => $pages->show($request, 'help.html', 'guide'));
});

Route::get('/admin/users', fn (Request $request, PageController $pages) => $pages->show($request, 'admin/users.html', 'admin-users'))
    ->middleware('admin');

Route::get('/api/health', [ApiController::class, 'health']);
Route::get('/api/auth/me', [ApiController::class, 'whoami']);
Route::post('/api/auth/register', [ApiController::class, 'register']);
Route::post('/api/auth/login', [ApiController::class, 'login']);
Route::post('/api/auth/logout', [ApiController::class, 'logout'])->middleware('authenticated');
Route::post('/api/auth/request-reset', [ApiController::class, 'requestReset']);
Route::post('/api/auth/reset-password', [ApiController::class, 'resetPassword']);
Route::patch('/api/me/profile', [ApiController::class, 'updateProfile'])->middleware('authenticated');
Route::patch('/api/me/preferences', [ApiController::class, 'updatePreferences'])->middleware('authenticated');
Route::post('/api/me/password', [ApiController::class, 'updatePassword'])->middleware('authenticated');

Route::middleware('authenticated')->group(function (): void {
    Route::get('/api/summary', [ApiController::class, 'summary']);
    Route::post('/api/jobs', [ApiController::class, 'createJob']);
    Route::get('/api/jobs/{jobId}', [ApiController::class, 'getJob'])->whereNumber('jobId');
    Route::get('/api/categories', [ApiController::class, 'categories']);
    Route::get('/api/books', [ApiController::class, 'books']);
    Route::get('/api/books/{bookId}', [ApiController::class, 'bookDetail'])->whereNumber('bookId');
    Route::match(['post', 'delete'], '/api/bookmarks/{bookId}', [ApiController::class, 'bookmark'])->whereNumber('bookId');
    Route::get('/api/bookmarks', [ApiController::class, 'bookmarks']);
    Route::get('/api/saved-searches', [ApiController::class, 'savedSearches']);
    Route::post('/api/saved-searches', [ApiController::class, 'saveSearch']);
    Route::delete('/api/saved-searches/{searchId}', [ApiController::class, 'deleteSearch'])->whereNumber('searchId');
    Route::get('/api/history', [ApiController::class, 'history']);
    Route::get('/api/notifications', [ApiController::class, 'notifications']);
    Route::patch('/api/notifications/read', [ApiController::class, 'markAllNotificationsRead']);
    Route::patch('/api/notifications/{notificationId}/read', [ApiController::class, 'markNotificationRead'])->whereNumber('notificationId');
    Route::get('/api/analytics', [ApiController::class, 'analytics']);
    Route::get('/api/sources', [ApiController::class, 'sources']);
    Route::get('/api/exports/books.csv', [ApiController::class, 'exportBooks']);
});

Route::middleware('admin')->prefix('api/admin')->group(function (): void {
    Route::get('/users', [AdminController::class, 'users']);
    Route::patch('/users/{userId}', [AdminController::class, 'updateUser'])->whereNumber('userId');
});

Route::fallback(function (Request $request, PageController $pages) {
    if ($request->is('api/*')) {
        return response()->json([
            'error' => ['code' => 'NOT_FOUND', 'message' => 'Đường dẫn API không tồn tại.'],
        ], 404);
    }

    return $pages->show($request, '404.html')->setStatusCode(404);
});
