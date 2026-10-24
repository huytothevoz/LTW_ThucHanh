<?php

namespace App\Services;

use Illuminate\Support\Facades\DB;

class PriceNotificationService
{
    public static function listForUser(int $userId): array
    {
        $items = DB::select(
            'SELECT n.id,n.book_id,b.title,h.old_price_pence,h.new_price_pence,n.created_at,n.read_at
             FROM price_change_notifications n
             JOIN books b ON b.id=n.book_id
             JOIN book_price_history h ON h.id=n.price_history_id
             WHERE n.user_id=? AND b.user_id=?
             ORDER BY (n.read_at IS NULL) DESC,n.id DESC
             LIMIT 20',
            [$userId, $userId],
        );
        $unread = (int) DB::scalar(
            'SELECT COUNT(*) FROM price_change_notifications n JOIN books b ON b.id=n.book_id '
            .'WHERE n.user_id=? AND b.user_id=? AND n.read_at IS NULL',
            [$userId, $userId],
        );

        return [
            'items' => array_map(static fn (object $row): array => (array) $row, $items),
            'unread_count' => $unread,
        ];
    }

    public static function markRead(int $userId, int $notificationId): bool
    {
        return DB::transaction(function () use ($userId, $notificationId): bool {
            $exists = DB::selectOne(
                'SELECT id FROM price_change_notifications WHERE id=? AND user_id=?',
                [$notificationId, $userId],
            );
            if (!$exists) {
                return false;
            }
            DB::update(
                'UPDATE price_change_notifications SET read_at=COALESCE(read_at,?) WHERE id=? AND user_id=?',
                [AccountService::now(), $notificationId, $userId],
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
    }
}
