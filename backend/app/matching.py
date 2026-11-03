import re
from typing import Optional

import numpy as np
from sqlmodel import Session, select

from .embeddings import embed, from_bytes, normalize, to_bytes
from .llm import json_chat
from .models import Job, Swipe, User

ALIASES = {
    "postgres": "postgresql", "k8s": "kubernetes", "ml": "machinelearning",
    "dl": "deeplearning", "golang": "go", "tf": "tensorflow",
    "tallyprime": "tally", "tallyerp": "tally", "tallyerp9": "tally",
    "charteredaccountant": "ca", "mbbsdoctor": "mbbs",
}
LANG_NAME = {"en": "English", "hi": "Hindi", "kn": "Kannada"}
_ROLE_STOP = {"and", "the", "for", "with", "senior", "junior", "lead", "assistant", "executive"}


def _canon(s: str) -> str:
    c = re.sub(r"[^a-z0-9+#]", "", s.lower())
    if c.endswith("js") and len(c) > 4:
        c = c[:-2]
    return ALIASES.get(c, c)


def job_to_dict(j: Job) -> dict:
    return {
        "job_id": j.id, "title": j.title, "company": j.company, "location": j.location,
        "remote": j.remote, "employment_type": j.employment_type,
        "salary_min": j.salary_min, "salary_max": j.salary_max, "currency": j.currency,
        "description": j.description, "skills": j.skills or [],
        "experience_min": j.experience_min, "experience_max": j.experience_max,
        "category": j.category or "", "industry": j.industry or "",
        "education": j.education or "", "shift": j.shift or "",
        "languages": j.languages or [], "benefits": j.benefits or [],
        "openings": j.openings or 1,
    }


def job_text(j: Job) -> str:
    return (
        f"{j.title} at {j.company}. Category: {j.category}. Industry: {j.industry}. "
        f"Education: {j.education}. Shift: {j.shift}. {j.description}\n"
        f"Skills: {', '.join(j.skills or [])}. Languages: {', '.join(j.languages or [])}."
    )


def add_job(session: Session, **data) -> Job:
    j = Job(**data)
    j.vec = to_bytes(embed([job_text(j)])[0])
    session.add(j)
    session.commit()
    session.refresh(j)
    return j


def upsert_job(session: Session, **data) -> tuple[Job, str]:
    """Insert, or refresh an existing title+company row (and its embedding) when fields change."""
    row = session.exec(
        select(Job).where(Job.title == data.get("title"), Job.company == data.get("company"))
    ).first()
    if row is None:
        return add_job(session, **data), "added"
    changed = False
    for k, v in data.items():
        if getattr(row, k) != v:
            setattr(row, k, v)
            changed = True
    if not changed and row.vec:
        return row, "unchanged"
    row.vec = to_bytes(embed([job_text(row)])[0])
    session.add(row)
    session.commit()
    session.refresh(row)
    return row, "updated"


def experience_fit(years, lo, hi) -> float:
    if years is None or (lo is None and hi is None):
        return 0.7
    lo = lo or 0
    hi = hi if hi is not None else 99
    if lo <= years <= hi:
        return 1.0
    gap = lo - years if years < lo else years - hi
    return max(0.0, 1 - 0.25 * gap)


def match_finder(job: dict, resume: dict) -> dict:
    """(job_json, resume_json) -> deterministic match json (fast, no LLM)."""
    resume_skills = resume.get("skills") or []
    rs = {_canon(s): s for s in resume_skills}
    js = {_canon(s): s for s in job.get("skills") or []}
    matched = [js[k] for k in js if k in rs]
    missing = [js[k] for k in js if k not in rs]
    if not js or not resume_skills:
        skill_score = 0.5
    else:
        skill_score = len(matched) / len(js)
    exp = experience_fit(resume.get("total_experience_years"), job.get("experience_min"), job.get("experience_max"))
    return {"skill_score": round(skill_score, 3), "experience_fit": round(exp, 3),
            "matched_skills": matched, "missing_skills": missing}


def role_fit(job: dict, resume: dict) -> float:
    """Overlap of the person's domains / past titles with this job family. Neutral if no profile."""
    has_profile = any(resume.get(k) for k in ("skills", "desired_roles", "roles", "domains", "summary"))
    if not has_profile:
        return 0.6
    score = 0.35
    cat = (job.get("category") or "").lower()
    domains = {str(d).strip().lower() for d in resume.get("domains") or []}
    if cat and cat in domains:
        score = max(score, 0.9)
    blob = f"{job.get('title', '')} {job.get('category', '')} {job.get('industry', '')}".lower()
    texts = [str(t) for t in resume.get("desired_roles") or []]
    for role in resume.get("roles") or []:
        if isinstance(role, dict) and role.get("title"):
            texts.append(str(role["title"]))
    hits = checked = 0
    for t in texts:
        words = [w for w in re.findall(r"[a-z]{3,}", t.lower()) if w not in _ROLE_STOP]
        if not words:
            continue
        checked += 1
        if any(w in blob for w in words):
            hits += 1
    if checked:
        score = max(score, hits / checked)
    return round(min(1.0, score), 3)


def explain(job: dict, resume: dict, mf: dict, lang: str = "en") -> dict:
    """LLM 'why this match / gaps / tip' in user's language. Called lazily per card."""
    system = (f"You are a career coach for jobs in India, including trades, shops, clinics, "
              f"CA firms and factories — not only software. Write in {LANG_NAME.get(lang, 'English')}. "
              'Return JSON: {"why": [max 3 short strings], "gaps": [max 3 short strings], "tip": "one short string"}.')
    user = f"RESUME: {resume}\nJOB: {job}\nMATCH: {mf}"
    return json_chat(system, user[:10000])


def passes_filters(j: Job, f: dict) -> bool:
    if not f:
        return True
    if f.get("remote") is True and not j.remote:
        return False
    locs = [l.lower() for l in f.get("locations") or []]
    if locs and not any(l in (j.location or "").lower() for l in locs):
        if not (j.remote and f.get("remote") is not False):
            return False
    if f.get("remote") is False and j.remote:
        return False
    if f.get("min_salary") and j.salary_max and j.salary_max < f["min_salary"]:
        return False
    types = [t.lower() for t in f.get("employment_types") or []]
    if types and (j.employment_type or "").lower() not in types:
        return False
    if f.get("max_experience_years") is not None and j.experience_min and j.experience_min > f["max_experience_years"]:
        return False
    if f.get("min_experience_years") is not None and j.experience_max and j.experience_max < f["min_experience_years"]:
        return False
    cats = [c.lower() for c in f.get("categories") or []]
    if cats and (j.category or "").lower() not in cats:
        return False
    shifts = [c.lower() for c in f.get("shifts") or []]
    if shifts and (j.shift or "").lower() not in shifts:
        return False
    industries = [c.lower() for c in f.get("industries") or []]
    if industries and not any(c in (j.industry or "").lower() for c in industries):
        return False
    educations = [c.lower() for c in f.get("educations") or []]
    if educations and not any(c in (j.education or "").lower() for c in educations):
        return False
    langs = [c.lower() for c in f.get("languages") or []]
    if langs:
        have = [x.lower() for x in (j.languages or [])]
        if have and not any(c in have for c in langs):
            return False
    blob = " ".join([
        j.title or "", j.description or "", j.category or "", j.industry or "",
        j.education or "", j.shift or "",
        " ".join(j.skills or []), " ".join(j.languages or []),
    ]).lower()
    if any(k.lower() in blob for k in f.get("exclude_keywords") or []):
        return False
    inc = f.get("include_keywords") or []
    if inc and not any(k.lower() in blob for k in inc):
        return False
    return True


def query_vector(user: User, state: dict):
    base = from_bytes(user.pref_vec) if user.pref_vec else None
    focus = (state or {}).get("focus")
    if focus:
        fv = embed([focus])[0]
        base = fv if base is None else base + 1.0 * fv
    if base is None:
        return None
    return normalize(base)


def rank_jobs(session: Session, user: User, limit: int = 10) -> list[dict]:
    state = user.search_state or {"filters": {}, "focus": ""}
    resume = user.resume_json or {}
    seen = {s.job_id for s in session.exec(select(Swipe).where(Swipe.user_id == user.id))}
    jobs = [j for j in session.exec(select(Job).where(Job.status == "open"))
            if j.id not in seen and passes_filters(j, state.get("filters", {}))]
    if not jobs:
        return []
    qv = query_vector(user, state)
    sems: dict[int, float] = {}
    if qv is not None:
        with_vec = [j for j in jobs if j.vec]
        if with_vec:
            sims = np.stack([from_bytes(j.vec) for j in with_vec]) @ qv
            for j, s in zip(with_vec, sims):
                sems[j.id] = float(np.clip((float(s) - 0.25) / 0.5, 0, 1))
    cards = []
    for j in jobs:
        d = job_to_dict(j)
        mf = match_finder(d, resume)
        role = role_fit(d, resume)
        sem = sems.get(j.id, 0.5)
        score = 0.50 * sem + 0.25 * mf["skill_score"] + 0.15 * mf["experience_fit"] + 0.10 * role
        d["description"] = (d["description"] or "")[:240]
        cards.append({**d, **mf, "role_fit": role, "match_pct": round(100 * score)})
    cards.sort(key=lambda c: c["match_pct"], reverse=True)
    return cards[:limit]


WEIGHTS = {"like": 0.15, "superlike": 0.35, "pass": -0.08}


def update_pref(user: User, job: Job, action: str) -> Optional[bytes]:
    if not job.vec or action not in WEIGHTS:
        return user.pref_vec
    base = from_bytes(user.pref_vec) if user.pref_vec else np.zeros_like(from_bytes(job.vec))
    return to_bytes(normalize(base + WEIGHTS[action] * from_bytes(job.vec)))