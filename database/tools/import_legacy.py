"""Safely IMPORT old in-repository SQLite DB into the protected V3 location.

Explicit action only. Copies with SQLite backup API (handles WAL snapshot), never
removes the original, and refuses to overwrite an existing target database.

Windows:
 python -m database.tools.import_legacy --source "C:\\xampp\\htdocs\\LTW-TH\\data\\crawlinsight.db"
"""
from __future__ import annotations
import argparse
import os
import sqlite3
from pathlib import Path
from src import db
from src.database.connection import ROOT


def import_database(source:Path,target:Path)->Path:
    source=source.expanduser().resolve()
    target=target.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f'Old database not found: {source}')
    if source==target:
        raise ValueError('Source and destination are identical')
    if target.exists():
        raise FileExistsError(f'Refusing to replace an existing database: {target}')
    target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_name(target.name+'.import-in-progress')
    if temp.exists():
        raise FileExistsError(f'Temporary import exists; inspect first: {temp}')
    try:
        # Source URI mode=ro avoids silently creating an empty database.
        original = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)
        try:
            copy = sqlite3.connect(str(temp))
            try:
                original.backup(copy)
                if copy.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise RuntimeError('Copied SQLite database failed integrity_check')
            finally:
                copy.close()
        finally:
            original.close()
        os.replace(temp, target)
        # The upgrade mechanism will make its own .before-v3 backup if needed.
        previous=os.environ.get('CRAWLINSIGHT_DB_PATH')
        os.environ['CRAWLINSIGHT_DB_PATH']=str(target)
        try:
            db.init_db()
        finally:
            if previous is None:os.environ.pop('CRAWLINSIGHT_DB_PATH',None)
            else:os.environ['CRAWLINSIGHT_DB_PATH']=previous
        return target
    finally:
        # If the import fails before replace, do not leave a half-imported file.
        # Import never deletes a pre-existing file. `temp` was exclusively created above.
        if temp.exists():temp.unlink()


def main():
    p=argparse.ArgumentParser(description='Non-destructive old SQLite DB importer for LTW-TH')
    p.add_argument('--source',type=Path,default=ROOT/'data'/'crawlinsight.db')
    p.add_argument('--target',type=Path,default=db.DEFAULT_DB)
    args=p.parse_args()
    print('Imported:',import_database(args.source,args.target))
    print('Original remains untouched:',args.source)

if __name__=='__main__':
    main()
