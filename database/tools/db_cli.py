"""CrawlInsight MySQL toolbox. Use `python -m database.tools.db_cli --help`."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

from src import db


def object_name(con, name: str) -> str:
    if not name or name.startswith(('mysql_', 'performance_schema', 'information_schema')):
        raise ValueError('System tables and unknown names are not available')
    row = con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema=DATABASE() AND table_name=?",
        (name,),
    ).fetchone()
    if row is None:
        raise ValueError(f'Unknown table/view: {name}')
    return '`' + row['table_name'].replace('`', '``') + '`'


def pretty(rows: list[dict], limit: int = 40) -> None:
    if not rows:
        print('(empty)')
        return
    columns = list(rows[0])
    widths = {
        column: min(48, max(len(column), *(len(str(row.get(column))) for row in rows)))
        for column in columns
    }
    print(' | '.join(column[:widths[column]].ljust(widths[column]) for column in columns))
    print('-+-'.join('-' * widths[column] for column in columns))
    for row in rows[:limit]:
        print(' | '.join(str(row.get(column, ''))[:widths[column]].ljust(widths[column]) for column in columns))


def rows_of(con, name: str, limit: int = 12) -> list[dict]:
    safe_name = object_name(con, name)
    return [dict(row) for row in con.execute(f'SELECT * FROM {safe_name} LIMIT ?', (limit,))]


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description='Initialize and inspect the CrawlInsight MySQL database')
    subcommands = parser.add_subparsers(dest='command', required=True)
    subcommands.add_parser('init', help='Create the MySQL schema and import the legacy SQLite DB once')
    subcommands.add_parser('tables', help='List MySQL tables/views and row counts')
    describe = subcommands.add_parser('describe', help='Show columns and foreign keys')
    describe.add_argument('table')
    rows = subcommands.add_parser('rows', help='Read the first N rows of a table/view')
    rows.add_argument('table')
    rows.add_argument('--limit', type=int, default=12)
    subcommands.add_parser('check', help='Check schema objects and applied migrations')
    export = subcommands.add_parser('export', help='Export one table/view as CSV/JSON')
    export.add_argument('table')
    export.add_argument('--format', choices=('csv', 'json'), default='csv')
    export.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)

    if args.command == 'init':
        db.init_db()
        print('MySQL database initialized; legacy SQLite rows are imported once when present.')
        return

    with db.connect() as con:
        if args.command == 'tables':
            objects = con.execute(
                'SELECT table_name,table_type FROM information_schema.tables '
                'WHERE table_schema=DATABASE() ORDER BY table_type,table_name'
            )
            for row in objects:
                safe_name = '`' + row['table_name'].replace('`', '``') + '`'
                count = con.execute(f'SELECT COUNT(*) FROM {safe_name}').fetchone()[0]
                print(f"{row['table_type']:5s} {row['table_name']:32s} {count:>8} rows")
        elif args.command == 'describe':
            safe_name = object_name(con, args.table)
            pretty([dict(row) for row in con.execute(f'SHOW COLUMNS FROM {safe_name}')])
            foreign_keys = con.execute(
                'SELECT constraint_name,column_name,referenced_table_name,referenced_column_name '
                'FROM information_schema.key_column_usage WHERE table_schema=DATABASE() '
                'AND table_name=? AND referenced_table_name IS NOT NULL',
                (args.table,),
            )
            print('\nForeign keys:')
            pretty([dict(row) for row in foreign_keys])
        elif args.command == 'rows':
            if not 1 <= args.limit <= 500:
                raise ValueError('--limit must be 1..500')
            pretty(rows_of(con, args.table, args.limit))
        elif args.command == 'check':
            objects = con.execute(
                "SELECT COUNT(*) AS total FROM information_schema.tables "
                "WHERE table_schema=DATABASE() AND table_name IN "
                "('users','books','crawl_jobs','sources','schema_migrations')"
            ).fetchone()
            migrations = rows_of(con, 'schema_migrations', 50)
            print('Required tables:', f"{objects['total']}/5")
            print('Schema migrations:')
            pretty(migrations)
            if objects['total'] != 5 or not migrations:
                raise SystemExit(2)
        elif args.command == 'export':
            safe_name = object_name(con, args.table)
            result = [dict(row) for row in con.execute(f'SELECT * FROM {safe_name}')]
            args.output.parent.mkdir(parents=True, exist_ok=True)
            if args.format == 'json':
                args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            else:
                with args.output.open('w', newline='', encoding='utf-8-sig') as output:
                    writer = csv.DictWriter(output, fieldnames=list(result[0]) if result else [])
                    if result:
                        writer.writeheader()
                        writer.writerows(result)
            print(f'Exported {len(result)} rows to {args.output}')


if __name__ == '__main__':
    main()
