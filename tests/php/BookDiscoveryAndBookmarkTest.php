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
            CREATE TABLE books (
                id INTEGER PRIMARY KEY,
                category_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                price_pence INTEGER NOT NULL,
                rating INTEGER NOT NULL DEFAULT 0,
                availability TEXT NOT NULL DEFAULT 'In stock',
                image_url TEXT,
                source_url TEXT
            );
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

        DB::table('books')->insert([
            [
                'id' => 1,
                'category_id' => 1,
                'title' => 'The Great Novel',
                'price_pence' => 1500,
                'rating' => 5,
                'availability' => 'In stock',
                'image_url' => 'https://books.toscrape.com/media/novel.jpg',
                'source_url' => 'https://books.toscrape.com/catalogue/novel.html',
            ],
            [
                'id' => 2,
                'category_id' => 2,
                'title' => 'Physics Explained',
                'price_pence' => 2500,
                'rating' => 4,
                'availability' => 'In stock',
                'image_url' => 'https://books.toscrape.com/media/physics.jpg',
                'source_url' => 'https://books.toscrape.com/catalogue/physics.html',
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
}
