import json
import pathlib
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from sqlmodel import Session  # noqa: E402

from app.catalog import CATEGORY_SLUGS  # noqa: E402
from app.db import engine, init_db  # noqa: E402
from app.matching import upsert_job  # noqa: E402

init_db()
jobs = json.loads((pathlib.Path(__file__).parent.parent / "data" / "jobs_seed.json").read_text())
bad = [j.get("title") for j in jobs if j.get("category") not in CATEGORY_SLUGS]
if bad:
    raise SystemExit(f"jobs with unknown category: {bad}")
counts = Counter()
with Session(engine) as s:
    for j in jobs:
        _, status = upsert_job(s, **j)
        counts[status] += 1
print(f"seeded {len(jobs)} jobs ({counts['added']} added, {counts['updated']} updated, {counts['unchanged']} unchanged)")