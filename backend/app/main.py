import copy
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session, select

from . import agent, ats as ats_mod, matching, postmatch, voice
from . import resume as resume_mod
from .catalog import CATEGORIES, CATEGORY_SLUGS, EMPLOYMENT_TYPES, SHIFTS, focus_for
from .config import settings
from .db import get_session, init_db
from .embeddings import embed, to_bytes
from .models import Job, Match, Swipe, User


@asynccontextmanager
async def lifespan(app):
    init_db()
    yield


app = FastAPI(title="JobSwipe - job seeker API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _user(s: Session, uid: int) -> User:
    u = s.get(User, uid)
    if not u:
        raise HTTPException(404, "user not found")
    return u


def _check_slugs(slugs: Optional[list[str]], allowed: set[str], label: str):
    if not slugs:
        return
    bad = [c for c in slugs if c.lower() not in allowed]
    if bad:
        raise HTTPException(422, f"unknown {label}: {bad}")


@app.get("/")
def root():
    return {"service": "JobSwipe", "docs": "/docs", "meta": "/meta"}


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/meta")
def meta(s: Session = Depends(get_session)):
    jobs = list(s.exec(select(Job).where(Job.status == "open")))
    counts: dict[str, int] = {}
    cities = set()
    for j in jobs:
        key = j.category or "other"
        counts[key] = counts.get(key, 0) + 1
        if j.location:
            cities.add(j.location)
    return {
        "categories": [{**c, "count": counts.get(c["slug"], 0)} for c in CATEGORIES],
        "shifts": SHIFTS,
        "employment_types": EMPLOYMENT_TYPES,
        "cities": sorted(cities),
        "jobs": len(jobs),
    }


class UserIn(BaseModel):
    name: str = ""
    email: str = ""
    preferred_lang: str = "en"


def _user_out(u: User) -> dict:
    resume = u.resume_json or {}
    return {
        "id": u.id, "name": u.name, "email": u.email, "preferred_lang": u.preferred_lang,
        "has_resume": bool(u.resume_json or u.resume_latex),
        "ats_score": u.ats_score,
        "has_latex": bool(u.resume_latex),
        "resume_latex": u.resume_latex,
        "search_state": u.search_state or {"filters": {}, "focus": ""},
        "resume": {
            "name": resume.get("name") or u.name,
            "email": resume.get("email") or u.email,
            "phone": resume.get("phone"),
            "location": resume.get("location"),
            "summary": resume.get("summary"),
            "links": resume.get("links") or {},
            "desired_roles": resume.get("desired_roles") or [],
            "domains": resume.get("domains") or [],
            "total_experience_years": resume.get("total_experience_years"),
            "skills": resume.get("skills") or [],
            "categorized_skills": resume.get("categorized_skills") or {},
            "roles": resume.get("roles") or [],
            "education": resume.get("education") or [],
            "projects": resume.get("projects") or [],
            "certifications": resume.get("certifications") or [],
            "achievements": resume.get("achievements") or [],
            "languages": resume.get("languages") or [],
        },
    }


@app.post("/users")
def create_user(body: UserIn, s: Session = Depends(get_session)):
    if body.preferred_lang not in ("en", "hi", "kn"):
        raise HTTPException(422, "preferred_lang must be en, hi or kn")
    u = User(**body.model_dump())
    s.add(u); s.commit(); s.refresh(u)
    return _user_out(u)


@app.get("/users/{uid}")
def get_user(uid: int, s: Session = Depends(get_session)):
    return _user_out(_user(s, uid))


@app.post("/users/{uid}/resume")
def upload_resume(uid: int, file: UploadFile = File(...), s: Session = Depends(get_session)):
    u = _user(s, uid)
    try:
        r = resume_mod.resume_reader(file.file.read())
    except ValueError as e:
        raise HTTPException(422, str(e))
    vec = to_bytes(embed([resume_mod.resume_to_text(r)])[0])
    latex = ats_mod.generate_latex_resume(r)
    ats_score = ats_mod.calculate_ats_score(r, latex)
    u.resume_json = r
    u.resume_vec = vec
    u.pref_vec = vec
    u.ats_score = ats_score
    u.resume_latex = latex
    s.add(u); s.commit()
    return {"resume": r, "ats": ats_score, "latex": latex}


@app.get("/users/{uid}/resume/ats")
def get_resume_ats(uid: int, s: Session = Depends(get_session)):
    u = _user(s, uid)
    if not u.resume_json and not u.resume_latex:
        raise HTTPException(404, "No resume uploaded yet")
    if not u.ats_score or not u.resume_latex:
        latex = u.resume_latex or ats_mod.generate_latex_resume(u.resume_json or {})
        score = ats_mod.calculate_ats_score(u.resume_json or {}, latex)
        u.resume_latex = latex
        u.ats_score = score
        s.add(u); s.commit()
    return {"ats": u.ats_score, "latex": u.resume_latex, "resume": _user_out(u)["resume"]}


class LatexIn(BaseModel):
    latex: str


@app.put("/users/{uid}/resume/latex")
def update_resume_latex(uid: int, body: LatexIn, s: Session = Depends(get_session)):
    u = _user(s, uid)
    u.resume_latex = body.latex
    parsed = ats_mod.parse_latex_resume(body.latex)
    curr = dict(u.resume_json or {})
    for k in ("name", "email", "phone", "location", "summary", "roles", "education", "projects", "certifications"):
        if parsed.get(k):
            curr[k] = parsed[k]
    if parsed.get("skills"):
        curr["skills"] = parsed["skills"]
    if parsed.get("categorized_skills"):
        curr["categorized_skills"] = parsed["categorized_skills"]
    if parsed.get("links"):
        curr["links"] = {**(curr.get("links") or {}), **parsed["links"]}
    u.resume_json = curr
    u.ats_score = ats_mod.calculate_ats_score(curr, body.latex)
    try:
        vec_text = resume_mod.resume_to_text(curr)
        if len(vec_text.strip()) > 20:
            vec = to_bytes(embed([vec_text])[0])
            u.resume_vec = vec
            u.pref_vec = vec
    except Exception:
        pass
    s.add(u); s.commit()
    return {"ok": True, "ats": u.ats_score, "latex": u.resume_latex, "resume": _user_out(u)["resume"]}


class ResumeChatIn(BaseModel):
    message: str
    chat_history: list = []
    current_latex: Optional[str] = None


@app.post("/users/{uid}/resume/improve-chat")
def improve_resume_chat(uid: int, body: ResumeChatIn, s: Session = Depends(get_session)):
    u = _user(s, uid)
    latex = body.current_latex or u.resume_latex or ats_mod.generate_latex_resume(u.resume_json or {})
    result = ats_mod.chat_improve_resume(body.message, latex, u.resume_json or {}, body.chat_history)
    u.resume_latex = result["latex"]

    parsed = ats_mod.parse_latex_resume(result["latex"])
    curr = dict(u.resume_json or {})
    for k in ("name", "email", "phone", "location", "summary", "roles", "education", "projects", "certifications"):
        if parsed.get(k):
            curr[k] = parsed[k]
    if parsed.get("skills"):
        curr["skills"] = parsed["skills"]
    if parsed.get("categorized_skills"):
        curr["categorized_skills"] = parsed["categorized_skills"]
    if parsed.get("links"):
        curr["links"] = {**(curr.get("links") or {}), **parsed["links"]}
    u.resume_json = curr

    new_ats = ats_mod.calculate_ats_score(curr, result["latex"])
    if result.get("estimated_score") and result["estimated_score"] > new_ats["overall_score"]:
        new_ats["overall_score"] = min(100, max(new_ats["overall_score"], int(result["estimated_score"])))
        if new_ats["overall_score"] >= 88:
            new_ats["rating"] = "Exceptional"
        elif new_ats["overall_score"] >= 75:
            new_ats["rating"] = "Strong"
        elif new_ats["overall_score"] >= 60:
            new_ats["rating"] = "Good"
        else:
            new_ats["rating"] = "Needs Work"
    u.ats_score = new_ats

    try:
        vec_text = resume_mod.resume_to_text(curr)
        if len(vec_text.strip()) > 20:
            vec = to_bytes(embed([vec_text])[0])
            u.resume_vec = vec
            u.pref_vec = vec
    except Exception:
        pass

    s.add(u); s.commit()
    return {**result, "ats": new_ats, "latex": u.resume_latex, "resume": _user_out(u)["resume"]}


def _can_rank(u: User) -> bool:
    state = u.search_state or {}
    filters = state.get("filters") or {}
    return bool(u.pref_vec or (state.get("focus") or "").strip() or filters)


@app.get("/users/{uid}/feed")
def feed(uid: int, limit: int = 10, s: Session = Depends(get_session)):
    u = _user(s, uid)
    state = u.search_state or {"filters": {}, "focus": ""}
    if not _can_rank(u):
        raise HTTPException(409, "upload a resume, pick a category, or set a search focus first")
    return {"cards": matching.rank_jobs(s, u, limit), "state": state}


@app.get("/users/{uid}/jobs/{jid}/why")
def why(uid: int, jid: int, s: Session = Depends(get_session)):
    u, j = _user(s, uid), s.get(Job, jid)
    if not j:
        raise HTTPException(404, "job not found")
    jd, r = matching.job_to_dict(j), u.resume_json or {}
    mf = matching.match_finder(jd, r)
    try:
        extra = matching.explain(jd, r, mf, u.preferred_lang)
    except Exception:
        why_bullets = []
        if mf.get("matched_skills"):
            why_bullets.append(f"Strong overlap in core skills: {', '.join(mf['matched_skills'][:4])}.")
        if mf.get("experience_fit", 0) >= 0.7:
            why_bullets.append("Your career background aligns with the target experience range.")
        if not why_bullets:
            why_bullets.append("Profile matches the baseline functional requirements for this role.")

        gaps = mf.get("missing_skills") or []
        tip = f"Highlight your experience with {gaps[0]} or related workflows in your application note." if gaps else "Emphasize your proven impact and project achievements during discussions."
        extra = {
            "why": why_bullets,
            "gaps": gaps[:3],
            "tip": tip,
            "coach_error": None,
        }
    return {**mf, "role_fit": matching.role_fit(jd, r), **extra}


class SwipeIn(BaseModel):
    job_id: int
    action: str  # like | pass | superlike


@app.post("/users/{uid}/swipe")
def swipe(uid: int, body: SwipeIn, s: Session = Depends(get_session)):
    if body.action not in matching.WEIGHTS:
        raise HTTPException(422, "action must be like|pass|superlike")
    u, j = _user(s, uid), s.get(Job, body.job_id)
    if not j:
        raise HTTPException(404, "job not found")
    if s.exec(select(Swipe).where(Swipe.user_id == uid, Swipe.job_id == j.id)).first():
        raise HTTPException(409, "already swiped")
    s.add(Swipe(user_id=uid, job_id=j.id, action=body.action))
    u.pref_vec = matching.update_pref(u, j, body.action)
    s.add(u)
    match_id = None
    if body.action in ("like", "superlike"):
        m = Match(user_id=uid, job_id=j.id)
        s.add(m); s.commit(); s.refresh(m)
        match_id = m.id
    else:
        s.commit()
    return {"ok": True, "match_id": match_id}


@app.get("/users/{uid}/matches")
def matches(uid: int, s: Session = Depends(get_session)):
    _user(s, uid)
    out = []
    for m in s.exec(select(Match).where(Match.user_id == uid)):
        j = s.get(Job, m.job_id)
        if not j:
            continue
        out.append({
            "match_id": m.id, "status": m.status, "job_id": j.id,
            "title": j.title, "company": j.company, "location": j.location,
            "category": j.category, "salary_min": j.salary_min, "salary_max": j.salary_max,
            "meet_url": m.meet_url, "next_steps": m.next_steps,
        })
    return out


def _refine(s: Session, u: User, text: str, lang: str):
    state = copy.deepcopy(u.search_state or {"filters": {}, "focus": ""})
    state, reply = agent.refine_search(state, text, lang)
    u.search_state = state
    s.add(u); s.commit()
    return {"reply": reply, "state": state, "cards": matching.rank_jobs(s, u, 15)}


class RefineIn(BaseModel):
    text: str


@app.post("/users/{uid}/search/refine")
def refine_text(uid: int, body: RefineIn, s: Session = Depends(get_session)):
    u = _user(s, uid)
    return _refine(s, u, body.text, u.preferred_lang)


class BrowseIn(BaseModel):
    categories: Optional[list[str]] = None
    locations: Optional[list[str]] = None
    remote: Optional[bool] = None
    min_salary: Optional[int] = None
    employment_types: Optional[list[str]] = None
    shifts: Optional[list[str]] = None
    educations: Optional[list[str]] = None
    industries: Optional[list[str]] = None
    languages: Optional[list[str]] = None
    focus: Optional[str] = None
    clear: bool = False


_LIST_FILTERS = (
    "categories", "locations", "employment_types", "shifts",
    "educations", "industries", "languages",
)


@app.post("/users/{uid}/browse")
def browse(uid: int, body: BrowseIn, limit: int = 15, s: Session = Depends(get_session)):
    u = _user(s, uid)
    data = body.model_dump(exclude_unset=True)
    _check_slugs(data.get("categories"), CATEGORY_SLUGS, "category")
    _check_slugs(data.get("shifts"), set(SHIFTS), "shift")
    state = {"filters": {}, "focus": ""} if data.get("clear") else copy.deepcopy(
        u.search_state or {"filters": {}, "focus": ""})
    f = state.setdefault("filters", {})
    for key in _LIST_FILTERS:
        if key not in data:
            continue
        value = data[key] or []
        if key == "employment_types":
            value = [str(v).lower().replace(" ", "-") for v in value]
        elif key in ("categories", "shifts", "languages"):
            value = [str(v).lower() for v in value]
        if value:
            f[key] = value
        else:
            f.pop(key, None)
    if "remote" in data:
        if data["remote"] is None:
            f.pop("remote", None)
        else:
            f["remote"] = data["remote"]
    if "min_salary" in data:
        if data["min_salary"]:
            f["min_salary"] = data["min_salary"]
        else:
            f.pop("min_salary", None)
    if "focus" in data:
        state["focus"] = (data["focus"] or "").strip()
    elif "categories" in data and not u.pref_vec:
        state["focus"] = focus_for(f.get("categories") or [])
    u.search_state = state
    s.add(u); s.commit(); s.refresh(u)
    if not _can_rank(u):
        return {"state": state, "cards": []}
    return {"state": state, "cards": matching.rank_jobs(s, u, limit)}


@app.post("/users/{uid}/search/voice")
def refine_voice(uid: int, audio: UploadFile = File(...), lang: Optional[str] = None,
                 s: Session = Depends(get_session)):
    u = _user(s, uid)
    suffix = os.path.splitext(audio.filename or "")[1] or ".webm"
    text, detected = voice.transcribe(audio.file.read(), lang, u.preferred_lang, suffix)
    if not text:
        raise HTTPException(422, "no speech detected")
    out = _refine(s, u, text, detected if detected in voice.SUPPORTED else u.preferred_lang)
    return {"transcript": text, "detected_lang": detected, **out}


@app.delete("/users/{uid}/search")
def reset(uid: int, s: Session = Depends(get_session)):
    u = _user(s, uid)
    u.search_state = {"filters": {}, "focus": ""}
    s.add(u); s.commit()
    cards = matching.rank_jobs(s, u, 15) if u.pref_vec else []
    return {"state": u.search_state, "cards": cards}


class JobIn(BaseModel):
    title: str
    company: str = ""
    location: str = ""
    remote: bool = False
    employment_type: str = "full-time"
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = "INR"
    description: str = ""
    skills: list[str] = []
    experience_min: Optional[float] = None
    experience_max: Optional[float] = None
    category: str = ""
    industry: str = ""
    education: str = ""
    shift: str = ""
    languages: list[str] = []
    benefits: list[str] = []
    openings: int = 1
    photo_url: Optional[str] = None
    company_logo: Optional[str] = None
    hiring_quote: Optional[str] = None


@app.post("/admin/jobs")
def add_job(body: JobIn, s: Session = Depends(get_session)):
    if body.category and body.category.lower() not in CATEGORY_SLUGS:
        raise HTTPException(422, f"unknown category. use one of: {sorted(CATEGORY_SLUGS)}")
    data = body.model_dump()
    if data.get("category"):
        data["category"] = data["category"].lower()
    if data.get("shift"):
        data["shift"] = data["shift"].lower()
    return {"id": matching.add_job(s, **data).id}


@app.post("/dev/matches/{mid}/provider-accept")
def provider_accept(mid: int, s: Session = Depends(get_session)):
    if not settings.dev_mode:
        raise HTTPException(404)
    m = s.get(Match, mid)
    if not m:
        raise HTTPException(404, "match not found")
    return {"status": "mutual", "next_steps": postmatch.on_mutual_match(s, m, s.get(Job, m.job_id))}