import json
import sqlite3

db = sqlite3.connect("data/academic_memory.db")

rows = db.execute(
    "SELECT id, metadata FROM documents"
).fetchall()

test_ids = []

for row_id, metadata in rows:
    try:
        data = json.loads(metadata)
        if data.get("test_data") is True:
            test_ids.append((row_id,))
    except (json.JSONDecodeError, TypeError):
        continue

if test_ids:
    db.executemany(
        "DELETE FROM documents WHERE id = ?",
        test_ids
    )

db.commit()

remaining = db.execute(
    "SELECT COUNT(*) FROM documents"
).fetchone()[0]

print("Test records removed:", len(test_ids))
print("Remaining documents:", remaining)

db.close()
