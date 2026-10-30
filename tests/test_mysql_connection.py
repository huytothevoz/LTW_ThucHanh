from src.database.connection import MYSQL_SCHEMA_PATH, MySQLConnection


def test_mysql_adapter_translates_legacy_sql_fragments():
    assert MySQLConnection._sql(
        'SELECT id FROM books WHERE user_id IS ? AND name=? COLLATE NOCASE'
    ) == 'SELECT id FROM books WHERE user_id <=> %s AND name=%s '
    assert MySQLConnection._sql(
        "INSERT OR IGNORE INTO bookmarks(user_id,book_id) VALUES(?,?)"
    ) == "INSERT IGNORE INTO bookmarks(user_id,book_id) VALUES(%s,%s)"
    assert MySQLConnection._sql('SELECT last_insert_rowid()') == 'SELECT LAST_INSERT_ID()'


def test_mysql_schema_contains_runtime_tables_and_innodb():
    schema = MYSQL_SCHEMA_PATH.read_text(encoding='utf-8').upper()
    for table in (
        'USERS', 'USER_PREFERENCES', 'BOOKS', 'CRAWL_JOBS', 'CRAWL_PAGES',
        'CRAWL_JOB_BOOKS', 'BOOK_PRICE_HISTORY', 'BOOKMARKS',
        'PRICE_CHANGE_NOTIFICATIONS', 'SAVED_SEARCHES', 'PASSWORD_RESET_TOKENS',
        'AUTH_ATTEMPTS', 'SOURCES', 'CATEGORIES', 'CRAWL_EVENTS',
    ):
        assert f'CREATE TABLE IF NOT EXISTS {table}' in schema
    assert 'ENGINE=INNODB' in schema
    assert 'SOURCE_URL_HASH' in schema
    assert 'ACTIVE_USER_KEY' in schema
    assert 'PRAGMA ' not in schema
