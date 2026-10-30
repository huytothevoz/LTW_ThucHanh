<?php

namespace Tests;

use Illuminate\Support\Facades\DB;

class BookDiscoveryAndBookmarkTest extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();

        DB::unprepared(<<<'SQL'
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_active INTEGER NOT NULL DEFAULT 1,
                session_version INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT
            );
            CREATE TABLE user_preferences (
                user_id INTEGER PRIMARY KEY,
                locale TEXT NOT NULL,
                theme TEXT NOT NULL,
                book_layout TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE categories (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE sources (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            CREATE TABLE books (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                source_id INTEGER NOT NULL DEFAULT 1,
                category_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                price_pence INTEGER NOT NULL,
                rating INTEGER NOT NULL DEFAULT 0,
                availability TEXT NOT NULL DEFAULT 'In stock',
                image_url TEXT,
                upc TEXT,
                source_url TEXT,
                first_seen_at TEXT,
                last_seen_at TEXT,
                last_crawl_job_id INTEGER
            );
            CREATE TABLE crawl_jobs (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                source_id INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL,
                max_pages INTEGER NOT NULL,
                items_saved INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                finished_at TEXT,
                last_error TEXT,
                error_count INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE crawl_events (
                id INTEGER PRIMARY KEY,
                job_id INTEGER NOT NULL,
                level TEXT NOT NULL,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE VIEW v_books_detail AS
            SELECT b.id,b.source_url,b.title,b.price_pence,
                   ROUND(b.price_pence/100.0,2) AS price_gbp,
                   b.rating,c.name AS category,b.availability,b.image_url,b.upc,
                   s.name AS source_name,b.first_seen_at,b.last_seen_at,b.last_crawl_job_id
            FROM books b JOIN categories c ON c.id=b.category_id JOIN sources s ON s.id=b.source_id;
            CREATE TABLE bookmarks (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                book_id INTEGER NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL,
                UNIQUE (user_id, book_id)
            );
        SQL);

        DB::table('users')->insert([
            'id' => 1,
            'full_name' => 'Test User',
            'email' => 'user@example.com',
            'password_hash' => 'hash',
            'created_at' => '2026-10-24T00:00:00Z',
            'updated_at' => '2026-10-24T00:00:00Z',
        ]);

        DB::table('categories')->insert([
            ['id' => 1, 'name' => 'Fiction'],
            ['id' => 2, 'name' => 'Science'],
        ]);
        DB::table('sources')->insert(['id' => 1, 'name' => 'Books to Scrape']);
        DB::table('crawl_jobs')->insert([
            'id' => 1,
            'user_id' => 1,
            'status' => 'COMPLETED',
            'max_pages' => 1,
            'items_saved' => 2,
            'created_at' => '2026-10-24T00:00:00Z',
        ]);

        DB::table('books')->insert([
            [
                'id' => 1,
                'user_id' => 1,
                'category_id' => 1,
                'title' => 'The Great Novel',
                'price_pence' => 1500,
                'rating' => 5,
                'availability' => 'In stock',
                'image_url' => 'https://books.toscrape.com/media/novel.jpg',
                'source_url' => 'https://books.toscrape.com/catalogue/novel.html',
                'first_seen_at' => '2026-10-24T00:00:00Z',
                'last_seen_at' => '2026-10-24T00:00:00Z',
            ],
            [
                'id' => 2,
                'user_id' => 1,
                'category_id' => 2,
                'title' => 'Physics Explained',
                'price_pence' => 2500,
                'rating' => 4,
                'availability' => 'In stock',
                'image_url' => 'https://books.toscrape.com/media/physics.jpg',
                'source_url' => 'https://books.toscrape.com/catalogue/physics.html',
                'first_seen_at' => '2026-10-24T00:00:00Z',
                'last_seen_at' => '2026-10-24T00:00:00Z',
            ],
        ]);
    }

    public function test_categories_endpoint_returns_category_list(): void
    {
        $response = $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->getJson('/api/categories')
            ->assertOk()
            ->assertJsonPath('items.0.name', 'Fiction')
            ->assertJsonPath('items.1.name', 'Science');
    }

    public function test_books_search_with_category_filter(): void
    {
        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->getJson('/api/books?category=Science')
            ->assertOk()
            ->assertJsonPath('total', 1)
            ->assertJsonPath('items.0.title', 'Physics Explained')
            ->assertJsonPath('items.0.category', 'Science');

        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->getJson('/api/books?category=Nonexistent')
            ->assertOk()
            ->assertJsonPath('total', 0)
            ->assertJsonPath('items', []);
    }

    public function test_bookmark_lifecycle(): void
    {
        // 1. Add bookmark for book 1
        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->postJson('/api/bookmarks/1')
            ->assertOk()
            ->assertExactJson(['book_id' => 1, 'saved' => true]);

        // 2. Discovery page reflects bookmarked_ids
        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->getJson('/api/books')
            ->assertOk()
            ->assertJsonPath('bookmarked_ids', [1]);

        // 3. Saved books list includes book 1
        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->getJson('/api/bookmarks')
            ->assertOk()
            ->assertJsonPath('total', 1)
            ->assertJsonPath('items.0.id', 1)
            ->assertJsonPath('items.0.title', 'The Great Novel');

        // 4. Remove bookmark for book 1
        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->deleteJson('/api/bookmarks/1')
            ->assertOk()
            ->assertExactJson(['book_id' => 1, 'saved' => false]);

        // 5. Saved books list is now empty
        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->getJson('/api/bookmarks')
            ->assertOk()
            ->assertJsonPath('total', 0)
            ->assertJsonPath('items', []);
    }

    public function test_books_and_summaries_are_private_to_their_owner(): void
    {
        DB::table('users')->insert([
            'id' => 2,
            'full_name' => 'Other User',
            'email' => 'other@example.com',
            'password_hash' => 'hash',
            'created_at' => '2026-10-24T00:00:00Z',
            'updated_at' => '2026-10-24T00:00:00Z',
        ]);
        DB::table('crawl_jobs')->insert([
            'id' => 2,
            'user_id' => 2,
            'status' => 'COMPLETED',
            'max_pages' => 1,
            'items_saved' => 1,
            'created_at' => '2026-10-24T00:00:00Z',
        ]);
        DB::table('categories')->insert(['id' => 3, 'name' => 'Private']);
        DB::table('books')->insert([
            'id' => 3,
            'user_id' => 2,
            'category_id' => 3,
            'title' => 'Another User Book',
            'price_pence' => 9900,
            'rating' => 5,
            'availability' => 'In stock',
            'source_url' => 'https://books.toscrape.com/catalogue/private.html',
            'first_seen_at' => '2026-10-24T00:00:00Z',
            'last_seen_at' => '2026-10-24T00:00:00Z',
        ]);

        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->getJson('/api/books')
            ->assertOk()
            ->assertJsonPath('total', 2)
            ->assertJsonMissing(['title' => 'Another User Book']);

        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->getJson('/api/books/3')
            ->assertNotFound();

        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->postJson('/api/bookmarks/3')
            ->assertNotFound()
            ->assertJsonPath('error.code', 'BOOK_NOT_FOUND');

        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->getJson('/api/summary')
            ->assertOk()
            ->assertJsonPath('total_books', 2);
    }

    public function test_create_job_max_pages_validation_up_to_5(): void
    {
        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->postJson('/api/jobs', ['max_pages' => 6])
            ->assertStatus(400)
            ->assertJsonPath('error.code', 'INVALID_MAX_PAGES');

        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->postJson('/api/jobs', ['max_pages' => 5])
            ->assertStatus(202)
            ->assertJsonPath('job.max_pages', 5);
    }

    public function test_reset_books_clears_current_user_data_safely(): void
    {
        DB::table('users')->insert([
            'id' => 2,
            'full_name' => 'Other User',
            'email' => 'other_user@example.com',
            'password_hash' => 'hash',
            'created_at' => '2026-10-24T00:00:00Z',
            'updated_at' => '2026-10-24T00:00:00Z',
        ]);
        DB::table('books')->insert([
            'id' => 3,
            'user_id' => 2,
            'category_id' => 1,
            'title' => 'Other User Book',
            'price_pence' => 2500,
            'rating' => 4,
            'availability' => 'In stock',
            'source_url' => 'https://books.toscrape.com/catalogue/other.html',
            'first_seen_at' => '2026-10-24T00:00:00Z',
            'last_seen_at' => '2026-10-24T00:00:00Z',
        ]);

        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->postJson('/api/books/reset')
            ->assertOk()
            ->assertJsonPath('ok', true)
            ->assertJsonPath('deleted_books', 2);

        $this->withSession(['user_id' => 1, 'session_version' => 0])
            ->getJson('/api/books')
            ->assertOk()
            ->assertJsonPath('total', 0);

        // User 2's books must remain intact
        $this->withSession(['user_id' => 2, 'session_version' => 0])
            ->getJson('/api/books')
            ->assertOk()
            ->assertJsonPath('total', 1);
    }
}

