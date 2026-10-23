CREATE TABLE IF NOT EXISTS price_change_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    price_history_id INTEGER NOT NULL REFERENCES book_price_history(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    read_at TEXT,
    UNIQUE(user_id, price_history_id)
);

CREATE INDEX IF NOT EXISTS idx_price_notifications_user_unread
    ON price_change_notifications(user_id,read_at,id DESC);
