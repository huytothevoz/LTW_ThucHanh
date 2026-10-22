<?php

namespace App\Http\Controllers;

use App\Services\AccountService;
use App\Services\BookService;
use App\Services\CrawlJobService;
use Illuminate\Database\QueryException;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Mail;
use Symfony\Component\Mailer\Exception\TransportExceptionInterface;
use Symfony\Component\HttpFoundation\StreamedResponse;

class ApiController
{
    public function health(): JsonResponse
    {
        return response()->json([
            'status' => 'ok',
            'app' => 'CrawlInsight',
            'database' => 'sqlite',
        ]);
    }

    public function whoami(Request $request): JsonResponse
    {
        $user = $this->user($request);

        return response()->json([
            'user' => $user,
            'preferences' => $user ? AccountService::preferences($user['id']) : null,
        ]);
    }

    public function register(Request $request): JsonResponse
    {
        $data = $request->json()->all();
        try {
            $user = AccountService::register(
                $data['full_name'] ?? '',
                $data['email'] ?? '',
                $data['password'] ?? '',
            );
        } catch (\DomainException $exception) {
            return $this->error('VALIDATION_ERROR', $exception->getMessage(), 400);
        } catch (QueryException $exception) {
            if (str_contains($exception->getMessage(), 'users.email')) {
                return $this->error('VALIDATION_ERROR', 'Email này đã được đăng ký.', 400);
            }
            throw $exception;
        }

        $this->loginSession($request, $user['id']);

        return response()->json([
            'user' => $user,
            'preferences' => AccountService::preferences($user['id']),
        ], 201);
    }

    public function login(Request $request): JsonResponse
    {
        $data = $request->json()->all();
        $email = substr(strtolower(trim(is_string($data['email'] ?? null) ? $data['email'] : '')), 0, 254);
        $subject = 'login:'.$email.':'.($request->ip() ?: 'local');
        if (AccountService::rateLimited($subject, 7, 15)) {
            return $this->error('TOO_MANY_ATTEMPTS', 'Thử lại sau 15 phút.', 429);
        }

        $user = AccountService::authenticate($email, $data['password'] ?? '');
        AccountService::recordAuthAttempt($subject, (bool) $user);
        if (!$user) {
            return $this->error('INVALID_CREDENTIALS', 'Email hoặc mật khẩu không chính xác.', 401);
        }

        $this->loginSession($request, $user['id']);

        return response()->json([
            'user' => $user,
            'preferences' => AccountService::preferences($user['id']),
        ]);
    }

    public function logout(Request $request): JsonResponse
    {
        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return response()->json(['ok' => true]);
    }

    public function requestReset(Request $request): JsonResponse
    {
        $data = $request->json()->all();
        $email = substr(strtolower(trim(is_string($data['email'] ?? null) ? $data['email'] : '')), 0, 254);
        $subject = 'reset:'.$email.':'.($request->ip() ?: 'local');
        if (AccountService::rateLimited($subject, 4, 30)) {
            return $this->error('TOO_MANY_ATTEMPTS', 'Thử lại sau 30 phút.', 429);
        }

        $testing = app()->environment('testing');
        $smtpReady = !$testing && $this->smtpReady();
        $localOptIn = (bool) env('ALLOW_LOCAL_RESET_LINKS', false)
            && in_array($request->ip(), ['127.0.0.1', '::1'], true);
        if (!$smtpReady && !$testing && !$localOptIn) {
            return $this->error(
                'MAIL_NOT_CONFIGURED',
                'Máy chủ chưa cấu hình email SMTP. Hãy liên hệ quản trị viên.',
                503,
            );
        }

        AccountService::recordAuthAttempt($subject, false);
        $created = AccountService::createResetToken($email);
        $response = ['message' => 'Nếu email đã tồn tại, bạn sẽ nhận được hướng dẫn khôi phục.'];
        if (!$created) {
            return response()->json($response);
        }

        $link = url('/reset-password/'.rawurlencode($created['token']));
        if ($smtpReady) {
            $name = $created['user']['full_name'];
            $locale = $request->attributes->get('locale', 'vi');
            $body = $locale === 'en'
                ? "Hello {$name},\n\nUse this link to reset your CrawlInsight password within 20 minutes:\n{$link}\n\nIf you did not request this, ignore this message."
                : "Xin chào {$name},\n\nDùng liên kết này để đặt lại mật khẩu CrawlInsight trong vòng 20 phút:\n{$link}\n\nNếu bạn không yêu cầu, hãy bỏ qua email này.";
            try {
                Mail::raw($body, static function ($message) use ($created, $locale): void {
                    $message->to($created['user']['email'])
                        ->subject($locale === 'en' ? 'CrawlInsight password reset' : 'Đặt lại mật khẩu CrawlInsight');
                });
            } catch (TransportExceptionInterface $exception) {
                Log::warning('Password-reset email delivery failed.', ['exception' => $exception]);

                return $this->error(
                    'EMAIL_DELIVERY_FAILED',
                    'Không thể gửi email. Vui lòng kiểm tra lại cấu hình SMTP.',
                    503,
                );
            }
        } elseif ($testing || $localOptIn) {
            $response['local_test_link'] = $link;
        }

        return response()->json($response);
    }

    public function resetPassword(Request $request): JsonResponse
    {
        $data = $request->json()->all();
        try {
            $valid = AccountService::resetPassword($data['token'] ?? '', $data['password'] ?? '');
        } catch (\DomainException $exception) {
            return $this->error('VALIDATION_ERROR', $exception->getMessage(), 400);
        }
        if (!$valid) {
            return $this->error('INVALID_TOKEN', 'Liên kết không hợp lệ, đã sử dụng hoặc hết hạn.', 400);
        }

        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return response()->json(['ok' => true]);
    }

    public function updateProfile(Request $request): JsonResponse
    {
        try {
            $user = AccountService::updateProfile(
                $this->user($request)['id'],
                $request->json()->all()['full_name'] ?? '',
            );
        } catch (\DomainException $exception) {
            return $this->error('VALIDATION_ERROR', $exception->getMessage(), 400);
        }

        return response()->json(['user' => $user]);
    }

    public function updatePreferences(Request $request): JsonResponse
    {
        try {
            $preferences = AccountService::updatePreferences(
                $this->user($request)['id'],
                $request->json()->all(),
            );
        } catch (\DomainException $exception) {
            return $this->error('VALIDATION_ERROR', $exception->getMessage(), 400);
        }

        return response()->json(['preferences' => $preferences]);
    }

    public function updatePassword(Request $request): JsonResponse
    {
        $data = $request->json()->all();
        try {
            AccountService::changePassword(
                $this->user($request)['id'],
                $data['current_password'] ?? '',
                $data['new_password'] ?? '',
            );
        } catch (\DomainException $exception) {
            return $this->error('VALIDATION_ERROR', $exception->getMessage(), 400);
        }
        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return response()->json(['ok' => true, 'reauth_required' => true]);
    }

    public function summary(Request $request): JsonResponse
    {
        return response()->json(BookService::userSummary($this->user($request)['id']));
    }

    public function createJob(Request $request): JsonResponse
    {
        $data = $request->json()->all();
        if (count($data) !== 1 || !array_key_exists('max_pages', $data)
            || !is_int($data['max_pages']) || !in_array($data['max_pages'], [1, 2, 3], true)) {
            return $this->error('INVALID_MAX_PAGES', 'max_pages phải là số nguyên từ 1 đến 3.', 400);
        }

        try {
            $job = CrawlJobService::create($data['max_pages'], $this->user($request)['id']);
        } catch (\DomainException $exception) {
            if ($exception->getMessage() === 'JOB_ALREADY_ACTIVE') {
                return $this->error('JOB_ALREADY_ACTIVE', 'Đang có lượt crawl khác hoạt động.', 409);
            }
            throw $exception;
        } catch (QueryException $exception) {
            if (str_contains($exception->getMessage(), 'ux_jobs_one_active')) {
                return $this->error('JOB_ALREADY_ACTIVE', 'Đang có lượt crawl khác hoạt động.', 409);
            }
            throw $exception;
        }

        try {
            CrawlJobService::launch((int) $job['id']);
        } catch (\RuntimeException $exception) {
            Log::warning('Could not launch crawler process.', ['job_id' => $job['id'], 'exception' => $exception]);
            CrawlJobService::fail((int) $job['id'], 'Crawler process could not start');

            return $this->error('CRAWLER_LAUNCH_FAILED', 'Không khởi chạy được crawler.', 503);
        }

        return response()->json(['job' => $job], 202);
    }

    public function getJob(Request $request, int $jobId): JsonResponse
    {
        $result = BookService::job($jobId, $this->user($request)['id']);
        if (!$result) {
            return $this->error('JOB_NOT_FOUND', 'Không tìm thấy lượt crawl.', 404);
        }

        return response()->json($result);
    }

    public function books(Request $request): JsonResponse
    {
        $pageValue = $request->query('page', '1');
        $page = is_string($pageValue) && ctype_digit($pageValue) ? (int) $pageValue : 0;
        $query = $request->query('q', '');
        $low = $request->query('min_price');
        $high = $request->query('max_price');
        if (!is_string($query) || ($low !== null && !is_string($low)) || ($high !== null && !is_string($high))) {
            return $this->error('INVALID_FILTER', 'Bộ lọc không hợp lệ.', 400);
        }

        try {
            $result = BookService::search($query, $low, $high, $page);
        } catch (\DomainException $exception) {
            return $this->error('INVALID_FILTER', $exception->getMessage(), 400);
        }
        $ids = array_map(static fn (array $item): int => (int) $item['id'], $result['items']);
        $result['bookmarked_ids'] = AccountService::bookmarkIds($this->user($request)['id'], $ids);

        return response()->json($result);
    }

    public function bookDetail(Request $request, int $bookId): JsonResponse
    {
        $result = BookService::bookDetail($bookId, $this->user($request)['id']);
        if (!$result) {
            return $this->error('BOOK_NOT_FOUND', 'Không tìm thấy sách.', 404);
        }

        return response()->json($result);
    }

    public function bookmark(Request $request, int $bookId): JsonResponse
    {
        $userId = $this->user($request)['id'];
        if ($request->isMethod('delete')) {
            AccountService::removeBookmark($userId, $bookId);

            return response()->json(['book_id' => $bookId, 'saved' => false]);
        }
        if (!AccountService::addBookmark($userId, $bookId)) {
            return $this->error('BOOK_NOT_FOUND', 'Không tìm thấy sách.', 404);
        }

        return response()->json(['book_id' => $bookId, 'saved' => true]);
    }

    public function bookmarks(Request $request): JsonResponse
    {
        $pageValue = $request->query('page', '1');
        if (!is_string($pageValue) || !ctype_digit($pageValue)) {
            return $this->error('INVALID_PAGE', 'Trang không hợp lệ.', 400);
        }
        try {
            return response()->json(AccountService::listBookmarks(
                $this->user($request)['id'],
                (int) $pageValue,
            ));
        } catch (\DomainException $exception) {
            return $this->error('INVALID_PAGE', $exception->getMessage(), 400);
        }
    }

    public function savedSearches(Request $request): JsonResponse
    {
        $items = DB::select(
            'SELECT id,name,query,min_price,max_price,created_at FROM saved_searches WHERE user_id=? ORDER BY id DESC',
            [$this->user($request)['id']],
        );

        return response()->json(['items' => array_map(static fn (object $row): array => (array) $row, $items)]);
    }

    public function saveSearch(Request $request): JsonResponse
    {
        $data = $request->json()->all();
        try {
            $item = AccountService::saveSearch(
                $this->user($request)['id'],
                $data['name'] ?? '',
                $data['q'] ?? '',
                $data['min_price'] ?? '',
                $data['max_price'] ?? '',
            );
        } catch (\DomainException $exception) {
            return $this->error('VALIDATION_ERROR', $exception->getMessage(), 400);
        }

        return response()->json(['item' => $item], 201);
    }

    public function deleteSearch(Request $request, int $searchId): JsonResponse
    {
        if (!AccountService::deleteSearch($this->user($request)['id'], $searchId)) {
            return $this->error('NOT_FOUND', 'Không tìm thấy bộ lọc.', 404);
        }

        return response()->json(['ok' => true]);
    }

    public function history(Request $request): JsonResponse
    {
        $items = DB::select(
            'SELECT id,status,max_pages,catalogue_pages_done,books_found,items_saved,new_books,existing_books,error_count,created_at,started_at,finished_at
             FROM crawl_jobs WHERE user_id=? ORDER BY id DESC LIMIT 100',
            [$this->user($request)['id']],
        );

        return response()->json(['items' => array_map(static fn (object $row): array => (array) $row, $items)]);
    }

    public function analytics(): JsonResponse
    {
        return response()->json(BookService::analytics());
    }

    public function sources(): JsonResponse
    {
        $items = DB::select(
            'SELECT id,name,base_url,allowed_host,is_enabled,created_at FROM sources ORDER BY id',
        );

        return response()->json(['items' => array_map(static fn (object $row): array => (array) $row, $items)]);
    }

    public function exportBooks(): StreamedResponse
    {
        return response()->streamDownload(function (): void {
            $output = fopen('php://output', 'wb');
            if ($output === false) {
                throw new \RuntimeException('Unable to open CSV output stream.');
            }
            fwrite($output, "\xEF\xBB\xBF");
            fputcsv($output, ['id', 'title', 'price_gbp', 'rating', 'category', 'availability', 'source_url']);
            foreach (BookService::exportRows() as $row) {
                fputcsv($output, [
                    $row->id,
                    $this->csvCell($row->title),
                    number_format(((int) $row->price_pence) / 100, 2, '.', ''),
                    $row->rating,
                    $this->csvCell($row->category),
                    $this->csvCell($row->availability),
                    $this->csvCell($row->source_url),
                ]);
            }
            fclose($output);
        }, 'crawlinsight-books.csv', [
            'Content-Type' => 'text/csv; charset=utf-8',
            'Cache-Control' => 'no-store',
        ]);
    }

    private function user(Request $request): array
    {
        return $request->attributes->get('current_user');
    }

    private function loginSession(Request $request, int $userId): void
    {
        $request->session()->invalidate();
        $request->session()->regenerateToken();
        $request->session()->put('user_id', $userId);
        $request->session()->put('session_version', AccountService::sessionVersion($userId));
    }

    private function smtpReady(): bool
    {
        return (string) config('mail.mailers.smtp.host') !== ''
            && (string) config('mail.mailers.smtp.username') !== ''
            && (string) config('mail.mailers.smtp.password') !== ''
            && (string) config('mail.from.address') !== '';
    }

    private function error(string $code, string $message, int $status): JsonResponse
    {
        return response()->json(['error' => ['code' => $code, 'message' => $message]], $status);
    }

    private function csvCell(string $value): string
    {
        return preg_match('/^[\x00-\x20]*[=+\-@]/u', $value) ? "'".$value : $value;
    }
}
