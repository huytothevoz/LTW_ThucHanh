<?php

namespace App\Services;

use Illuminate\Support\Facades\DB;

class PriceNotificationService
{
    public static function listForUser(int $userId): array
    {
        $priceItems = DB::select(
            'SELECT n.id,n.book_id,b.title,h.old_price_pence,h.new_price_pence,n.created_at,n.read_at
             FROM price_change_notifications n
             JOIN books b ON b.id=n.book_id
             JOIN book_price_history h ON h.id=n.price_history_id
             WHERE n.user_id=? AND b.user_id=?
             ORDER BY (n.read_at IS NULL) DESC,n.id DESC
             LIMIT 20',
            [$userId, $userId],
        );
        $crawlItems = DB::select(
            "SELECT n.job_id AS job_id,'crawl' AS kind,"
            .'(SELECT COUNT(*) FROM crawl_jobs prior '
            .'WHERE prior.user_id=c.user_id AND prior.id<=c.id) AS user_job_number,'
            .'c.status,s.name AS source_name,n.created_at,n.read_at '
            .'FROM crawl_notifications n '
            .'JOIN crawl_jobs c ON c.id=n.job_id AND c.user_id=n.user_id '
            .'JOIN sources s ON s.id=c.source_id '
            .'WHERE n.user_id=? ORDER BY n.id DESC LIMIT 20',
            [$userId],
        );
        $priceItems = array_map(static function (object $row): array {
            return ['kind' => 'price'] + (array) $row;
        }, $priceItems);
        $items = array_merge(
            $priceItems,
            array_map(static function (object $row): array {
                $item = (array) $row;
                $item['id'] = 'crawl-'.$item['job_id'];
                $item['title'] = 'Crawl #'.$item['user_job_number'];

                return $item;
            }, $crawlItems),
        );
        usort($items, static function (array $left, array $right): int {
            $unreadOrder = (int) ($left['read_at'] === null) <=> (int) ($right['read_at'] === null);

            return $unreadOrder !== 0
                ? -$unreadOrder
                : strcmp((string) $right['created_at'], (string) $left['created_at']);
        });
        $items = array_slice($items, 0, 20);
        $unread = (int) DB::scalar(
            'SELECT COUNT(*) FROM price_change_notifications n JOIN books b ON b.id=n.book_id '
            .'WHERE n.user_id=? AND b.user_id=? AND n.read_at IS NULL',
            [$userId, $userId],
        ) + (int) DB::scalar(
            'SELECT COUNT(*) FROM crawl_notifications WHERE user_id=? AND read_at IS NULL',
            [$userId],
        );

        return [
            'items' => $items,
            'unread_count' => $unread,
        ];
    }

    public static function markRead(int $userId, string $notificationId): bool
    {
        if (preg_match('/^crawl-(\d+)$/', $notificationId, $matches)) {
            $changed = DB::update(
                'UPDATE crawl_notifications SET read_at=COALESCE(read_at,?) WHERE job_id=? AND user_id=?',
                [AccountService::now(), (int) $matches[1], $userId],
            );

            return $changed > 0;
        }
        if (!ctype_digit($notificationId)) {
            return false;
        }

        return DB::transaction(function () use ($userId, $notificationId): bool {
            $exists = DB::selectOne(
                'SELECT id FROM price_change_notifications WHERE id=? AND user_id=?',
                [(int) $notificationId, $userId],
            );
            if (!$exists) {
                return false;
            }
            DB::update(
                'UPDATE price_change_notifications SET read_at=COALESCE(read_at,?) WHERE id=? AND user_id=?',
                [AccountService::now(), (int) $notificationId, $userId],
            );

            return true;
        });
    }

    public static function markAllRead(int $userId): void
    {
        DB::update(
            'UPDATE price_change_notifications SET read_at=? WHERE user_id=? AND read_at IS NULL',
            [AccountService::now(), $userId],
        );
        DB::update(
            'UPDATE crawl_notifications SET read_at=? WHERE user_id=? AND read_at IS NULL',
            [AccountService::now(), $userId],
        );
    }
}
