<?php

namespace App\Services;

use Illuminate\Support\Facades\DB;

class BookService
{
    public static function summary(): array
    {
        $total = (int) DB::scalar('SELECT COUNT(*) FROM books');
        $completed = (int) DB::scalar("SELECT COUNT(*) FROM crawl_jobs WHERE status='COMPLETED'");
        $recent = DB::select('SELECT id,status,max_pages,items_saved,created_at FROM crawl_jobs ORDER BY id DESC LIMIT 5');
        $last = DB::selectOne('SELECT id,status,created_at FROM crawl_jobs ORDER BY id DESC LIMIT 1');
        $ratings = DB::select('SELECT rating,COUNT(*) AS count FROM books GROUP BY rating');
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

    public static function search(string $query, ?string $minPrice, ?string $maxPrice, int $page): array
    {
        if (mb_strlen($query) > 100) {
            throw new \DomainException('q must be <=100 characters');
        }
        if ($page < 1 || $page > 100000) {
            throw new \DomainException('page must be between 1 and 100000');
        }

        $low = AccountService::parsePrice($minPrice ?? '', 'min_price');
        $high = AccountService::parsePrice($maxPrice ?? '', 'max_price');
        if ($low !== null && $high !== null && $low > $high) {
            throw new \DomainException('min_price must be <= max_price');
        }

        $conditions = [];
        $bindings = [];
        if (trim($query) !== '') {
            $escaped = str_replace(['\\', '%', '_'], ['\\\\', '\\%', '\\_'], trim($query));
            $conditions[] = "b.title LIKE ? ESCAPE '\\' COLLATE NOCASE";
            $bindings[] = '%'.$escaped.'%';
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
            .$join.$where.' ORDER BY b.id DESC LIMIT 12 OFFSET ?',
            [...$bindings, ($page - 1) * 12],
        );

        return [
            'items' => array_map(static fn (object $row): array => (array) $row, $items),
            'page' => $page,
            'page_size' => 12,
            'total' => $total,
            'total_pages' => (int) ceil($total / 12),
        ];
    }

    public static function userSummary(int $userId): array
    {
        $result = self::summary();
        $result['completed_jobs'] = (int) DB::scalar(
            "SELECT COUNT(*) FROM crawl_jobs WHERE user_id=? AND status='COMPLETED'",
            [$userId],
        );
        $result['recent_jobs'] = array_map(
            static fn (object $row): array => (array) $row,
            DB::select(
                'SELECT id,status,max_pages,items_saved,created_at FROM crawl_jobs WHERE user_id=? ORDER BY id DESC LIMIT 5',
                [$userId],
            ),
        );
        $last = DB::selectOne(
            'SELECT id,status,created_at FROM crawl_jobs WHERE user_id=? ORDER BY id DESC LIMIT 1',
            [$userId],
        );
        $result['last_job'] = $last ? (array) $last : null;
        $result['saved_books'] = (int) DB::scalar(
            'SELECT COUNT(*) FROM bookmarks WHERE user_id=?',
            [$userId],
        );

        return $result;
    }

    public static function job(int $jobId, int $userId): ?array
    {
        $job = DB::selectOne('SELECT * FROM crawl_jobs WHERE id=? AND user_id=?', [$jobId, $userId]);
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
        $book = DB::selectOne('SELECT * FROM v_books_detail WHERE id=?', [$bookId]);
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

    public static function analytics(): array
    {
        $categories = DB::select(
            'SELECT category,total_books,average_price_gbp FROM v_category_summary ORDER BY total_books DESC,category LIMIT 12',
        );
        $prices = DB::selectOne(
            'SELECT MIN(price_pence) AS minimum,MAX(price_pence) AS maximum,ROUND(AVG(price_pence)) AS average,COUNT(*) AS total FROM books',
        );

        return [
            'categories' => array_map(static fn (object $row): array => (array) $row, $categories),
            'prices' => (array) $prices,
            'rating_distribution' => self::summary()['rating_distribution'],
        ];
    }

    public static function exportRows(): iterable
    {
        return DB::cursor(
            'SELECT b.id,b.title,b.price_pence,b.rating,c.name AS category,b.availability,b.source_url
             FROM books b JOIN categories c ON c.id=b.category_id ORDER BY b.id',
        );
    }
}
