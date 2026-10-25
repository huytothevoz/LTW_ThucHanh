<?php

namespace App\Services;

use Illuminate\Support\Facades\DB;

class BookService
{
    public static function summary(int $userId): array
    {
        $total = (int) DB::scalar('SELECT COUNT(*) FROM books WHERE user_id=?', [$userId]);
        $completed = (int) DB::scalar("SELECT COUNT(*) FROM crawl_jobs WHERE user_id=? AND status='COMPLETED'", [$userId]);
        $recent = DB::select(
            'SELECT c.id, c.status, c.max_pages, c.items_saved, c.created_at,
                    (SELECT COUNT(*) FROM crawl_jobs t WHERE t.user_id = c.user_id AND t.id <= c.id) AS user_job_number
             FROM crawl_jobs c WHERE c.user_id=? ORDER BY c.id DESC LIMIT 5',
            [$userId],
        );
        $last = DB::selectOne(
            'SELECT c.id, c.status, c.created_at,
                    (SELECT COUNT(*) FROM crawl_jobs t WHERE t.user_id = c.user_id AND t.id <= c.id) AS user_job_number
             FROM crawl_jobs c WHERE c.user_id=? ORDER BY c.id DESC LIMIT 1',
            [$userId],
        );
        $ratings = DB::select('SELECT rating,COUNT(*) AS count FROM books WHERE user_id=? GROUP BY rating', [$userId]);
        $counts = [];
        foreach ($ratings as $row) {
            $counts[(int) $row->rating] = (int) $row->count;
        }

        return [
            'total_books' => $total,
            'completed_jobs' => $completed,
            'last_job' => $last ? (array) $last : null,
            'recent_jobs' => array_map(static fn (object $row): array => (array) $row, $recent),
            'rating_distribution' => array_map(
                static fn (int $rating): array => ['rating' => $rating, 'count' => $counts[$rating] ?? 0],
                range(1, 5),
            ),
        ];
    }

    public static function categories(int $userId): array
    {
        $rows = DB::select(
            'SELECT DISTINCT c.id,c.name FROM categories c JOIN books b ON b.category_id=c.id WHERE b.user_id=? ORDER BY c.name ASC',
            [$userId],
        );
        return array_map(static fn (object $row): array => (array) $row, $rows);
    }

    public static function search(int $userId, string $query, ?string $minPrice, ?string $maxPrice, int $page, ?string $category = null): array
    {
        if (mb_strlen($query) > 100) {
            throw new \DomainException('q must be <=100 characters');
        }
        if ($category !== null && mb_strlen($category) > 100) {
            throw new \DomainException('category must be <=100 characters');
        }
        if ($page < 1 || $page > 100000) {
            throw new \DomainException('page must be between 1 and 100000');
        }

        $low = AccountService::parsePrice($minPrice ?? '', 'min_price');
        $high = AccountService::parsePrice($maxPrice ?? '', 'max_price');
        if ($low !== null && $high !== null && $low > $high) {
            throw new \DomainException('min_price must be <= max_price');
        }

        $conditions = ['b.user_id=?'];
        $bindings = [$userId];
        if (trim($query) !== '') {
            $escaped = str_replace(['!', '%', '_'], ['!!', '!%', '!_'], trim($query));
            $conditions[] = "b.title LIKE ? ESCAPE '!'";
            $bindings[] = '%'.$escaped.'%';
        }
        if ($category !== null && trim($category) !== '') {
            $conditions[] = 'c.name = ?';
            $bindings[] = trim($category);
        }
        if ($low !== null) {
            $conditions[] = 'b.price_pence>=?';
            $bindings[] = $low;
        }
        if ($high !== null) {
            $conditions[] = 'b.price_pence<=?';
            $bindings[] = $high;
        }
        $where = $conditions ? ' WHERE '.implode(' AND ', $conditions) : '';
        $join = ' FROM books b JOIN categories c ON c.id=b.category_id';
        $total = (int) DB::scalar('SELECT COUNT(*)'.$join.$where, $bindings);
        $items = DB::select(
            'SELECT b.id,b.title,b.price_pence,b.rating,c.name AS category,b.availability,b.image_url,b.source_url'
            .$join.$where.' ORDER BY b.id DESC LIMIT 20 OFFSET ?',
            [...$bindings, ($page - 1) * 20],
        );

        return [
            'items' => array_map(static fn (object $row): array => (array) $row, $items),
            'page' => $page,
            'page_size' => 20,
            'total' => $total,
            'total_pages' => (int) ceil($total / 20),
        ];
    }

    public static function userSummary(int $userId): array
    {
        $result = self::summary($userId);
        $result['saved_books'] = (int) DB::scalar(
            'SELECT COUNT(*) FROM bookmarks bk JOIN books b ON b.id=bk.book_id WHERE bk.user_id=? AND b.user_id=?',
            [$userId, $userId],
        );

        return $result;
    }

    public static function job(int $jobId, int $userId): ?array
    {
        $job = DB::selectOne(
            'SELECT c.*, (SELECT COUNT(*) FROM crawl_jobs t WHERE t.user_id = c.user_id AND t.id <= c.id) AS user_job_number
             FROM crawl_jobs c WHERE c.id=? AND c.user_id=?',
            [$jobId, $userId],
        );
        if (!$job) {
            return null;
        }
        $events = DB::select(
            'SELECT id,job_id,level,event_type,message,created_at FROM crawl_events WHERE job_id=? ORDER BY id DESC LIMIT 30',
            [$jobId],
        );

        return [
            'job' => (array) $job,
            'events' => array_map(static fn (object $row): array => (array) $row, $events),
        ];
    }

    public static function bookDetail(int $bookId, int $userId): ?array
    {
        $book = DB::selectOne(
            'SELECT d.* FROM v_books_detail d JOIN books b ON b.id=d.id WHERE d.id=? AND b.user_id=?',
            [$bookId, $userId],
        );
        if (!$book) {
            return null;
        }
        $history = DB::select(
            'SELECT old_price_pence,new_price_pence,changed_at FROM book_price_history WHERE book_id=? ORDER BY id DESC LIMIT 30',
            [$bookId],
        );

        return [
            'book' => (array) $book,
            'is_bookmarked' => in_array($bookId, AccountService::bookmarkIds($userId, [$bookId]), true),
            'price_history' => array_map(static fn (object $row): array => (array) $row, $history),
        ];
    }

    public static function analytics(int $userId): array
    {
        $categories = DB::select(
            'SELECT c.name AS category,COUNT(b.id) AS total_books,ROUND(AVG(b.price_pence)/100.0,2) AS average_price_gbp '
            .'FROM books b JOIN categories c ON c.id=b.category_id WHERE b.user_id=? '
            .'GROUP BY c.id,c.name ORDER BY total_books DESC,category LIMIT 12',
            [$userId],
        );
        $prices = DB::selectOne(
            'SELECT MIN(price_pence) AS minimum,MAX(price_pence) AS maximum,ROUND(AVG(price_pence)) AS average,COUNT(*) AS total FROM books WHERE user_id=?',
            [$userId],
        );

        return [
            'categories' => array_map(static fn (object $row): array => (array) $row, $categories),
            'prices' => (array) $prices,
            'rating_distribution' => self::summary($userId)['rating_distribution'],
        ];
    }

    public static function exportRows(int $userId): iterable
    {
        return DB::cursor(
            'SELECT b.id,b.title,b.price_pence,b.rating,c.name AS category,b.availability,b.source_url
             FROM books b JOIN categories c ON c.id=b.category_id WHERE b.user_id=? ORDER BY b.id',
            [$userId],
        );
    }

    public static function resetCrawledBooks(int $userId): array
    {
        return DB::transaction(function () use ($userId): array {
            $activeJob = DB::selectOne(
                "SELECT id FROM crawl_jobs WHERE user_id=? AND status IN ('PENDING','RUNNING') LIMIT 1",
                [$userId],
            );
            if ($activeJob) {
                throw new \DomainException('JOB_ALREADY_ACTIVE');
            }

            $bookIds = DB::table('books')->where('user_id', $userId)->pluck('id')->all();
            $bookCount = count($bookIds);

            if ($bookCount > 0) {
                foreach (['bookmarks', 'price_change_notifications', 'book_price_history', 'crawl_job_books'] as $table) {
                    if (\Illuminate\Support\Facades\Schema::hasTable($table)) {
                        DB::table($table)->whereIn('book_id', $bookIds)->delete();
                    }
                }
                DB::table('books')->where('user_id', $userId)->delete();
            }

            $jobIds = DB::table('crawl_jobs')->where('user_id', $userId)->pluck('id')->all();
            if (count($jobIds) > 0) {
                foreach (['crawl_events', 'crawl_pages'] as $table) {
                    if (\Illuminate\Support\Facades\Schema::hasTable($table)) {
                        DB::table($table)->whereIn('job_id', $jobIds)->delete();
                    }
                }
                DB::table('crawl_jobs')->where('user_id', $userId)->delete();
            }

            return [
                'ok' => true,
                'deleted_books' => $bookCount,
                'deleted_jobs' => count($jobIds),
            ];
        });
    }
}

