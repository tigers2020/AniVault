#!/usr/bin/env python3
"""Check database tables."""

import sqlite3

def check_tables():
    """Check existing tables in the database."""
    try:
        conn = sqlite3.connect('anivault.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print('Existing tables:', [table[0] for table in tables])
        conn.close()
    except Exception as e:
        print(f"Error checking tables: {e}")

if __name__ == "__main__":
    check_tables()
