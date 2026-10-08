"""Dependency-free SQLite read bridge for the mixed-evidence subject."""

import json
import sqlite3
import sys


def main() -> None:
    with sqlite3.connect(sys.argv[1]) as connection:
        rows = connection.execute("select name from users order by id").fetchall()
    print(json.dumps([row[0] for row in rows]))


if __name__ == "__main__":
    main()
