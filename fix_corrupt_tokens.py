"""
fix_corrupt_tokens.py — Run this ONCE to repair corrupt token conditions in the DB.
Usage: python fix_corrupt_tokens.py
"""
import sqlite3, json
from server.paths import DB_PATH, ensure_data_dirs

ensure_data_dirs()

if not DB_PATH.exists():
    print(f"DB not found at {DB_PATH}")
    exit(1)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

try:
    conn.setlimit(0, 1_000_000_000)
except AttributeError:
    pass

rows = conn.execute("SELECT id, name, conditions FROM tokens").fetchall()
fixed = 0
for row in rows:
    cond_raw = row["conditions"] or "[]"
    needs_fix = False
    try:
        cond = json.loads(cond_raw)
        if not isinstance(cond, list):
            needs_fix = True
            cond = []
        else:
            safe = [str(c)[:50] for c in cond if isinstance(c, str)][:20]
            if safe != cond:
                needs_fix = True
                cond = safe
    except Exception:
        needs_fix = True
        cond = []

    if len(cond_raw) > 10000:
        needs_fix = True
        cond = []
        print(f"  Corrupt token '{row['name']}' (id={row['id']}): conditions was {len(cond_raw):,} bytes → reset to []")

    if needs_fix:
        conn.execute("UPDATE tokens SET conditions=? WHERE id=?",
                     (json.dumps(cond), row["id"]))
        fixed += 1

conn.commit()
conn.close()
print(f"Done. Fixed {fixed} token(s).")
