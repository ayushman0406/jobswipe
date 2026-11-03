import fitz  # PyMuPDF

from .llm import json_chat

SYSTEM = """Extract the resume into comprehensive JSON with exactly these keys:
name, email, phone, location, summary,
links ({linkedin: string or null, github: string or null, portfolio: string or null, website: string or null}),
total_experience_years (number),
skills (list of lowercase strings — canonical and concrete, e.g. "python", "pytorch", "tally", "gst",
"patient care", "welding", "cnc", "sales", "house wiring", "classroom management", "docker", "fastapi"),
categorized_skills ({
  technical: list of strings,
  tools_and_frameworks: list of strings,
  soft: list of strings,
  domain_expertise: list of strings
}),
roles (list of {title, company, location, start, end, is_current (boolean), highlights[]}),
education (list of {degree, institution, field_of_study, grade_or_gpa, start_year, year}),
projects (list of {name, description, tech[], link, highlights[]}),
certifications (list of {name, issuer, year}),
achievements (list of {title, description, year}),
publications (list of {title, publisher, year}),
volunteer_work (list of {role, organization, description}),
interests (list of lowercase strings),
languages (spoken languages, lowercase: english, hindi, kannada, tamil, telugu, marathi, ...),
desired_roles (list of 2-4 job titles that best fit this person),
domains (list of category slugs that fit, chosen ONLY from:
technology, sales, management, retail, mechanical, finance, healthcare, hospitality, education,
logistics, hr, marketing, support, legal, trades, agriculture, creative, operations).
Use null or empty lists when missing. Never invent facts. A shop cashier, a CA, a nurse, a software engineer and a fitter are all valid profiles.
Output JSON only."""


def pdf_to_text(data: bytes) -> str:
    with fitz.open(stream=data, filetype="pdf") as doc:
        return "\n".join(p.get_text() for p in doc)


def resume_reader(pdf_bytes: bytes) -> dict:
    """pdf -> comprehensive structured resume json"""
    text = pdf_to_text(pdf_bytes)
    if len(text.strip()) < 50:
        raise ValueError("No text layer found in PDF; OCR needed")
    r = json_chat(SYSTEM, text[:15000])

    # Normalization & Deduplication
    r["skills"] = sorted({s.strip().lower() for s in (r.get("skills") or []) if s})
    r["domains"] = sorted({str(d).strip().lower() for d in (r.get("domains") or []) if d})
    r["languages"] = sorted({str(l).strip().lower() for l in (r.get("languages") or []) if l})

    if not isinstance(r.get("links"), dict):
        r["links"] = {}
    if not isinstance(r.get("categorized_skills"), dict):
        r["categorized_skills"] = {
            "technical": r["skills"],
            "tools_and_frameworks": [],
            "soft": [],
            "domain_expertise": [],
        }

    # Ensure list types
    for key in ("roles", "education", "projects", "certifications", "achievements", "publications", "volunteer_work", "interests", "desired_roles"):
        if not isinstance(r.get(key), list):
            r[key] = []

    return r


def resume_to_text(r: dict) -> str:
    roles = "; ".join(
        f"{x.get('title')} at {x.get('company')}" + (f" ({', '.join(x.get('highlights') or [])})" if x.get('highlights') else "")
        for x in r.get("roles") or []
    )
    projs = "; ".join(
        f"{p.get('name')}: {p.get('description')}" + (f" [Tech: {', '.join(p.get('tech') or [])}]" if p.get('tech') else "")
        for p in r.get("projects") or []
    )
    edu = "; ".join(
        f"{e.get('degree')} at {e.get('institution')}" + (f" in {e.get('field_of_study')}" if e.get('field_of_study') else "")
        for e in r.get("education") or []
    )
    certs = "; ".join(
        f"{c.get('name')}" + (f" by {c.get('issuer')}" if c.get('issuer') else "")
        for c in r.get("certifications") or []
    )
    achievements = "; ".join(
        f"{a.get('title')}: {a.get('description')}" if a.get('description') else str(a.get('title', ''))
        for a in r.get("achievements") or []
    )

    cat_skills = r.get("categorized_skills") or {}
    all_skills = sorted(set(
        (r.get("skills") or [])
        + (cat_skills.get("technical") or [])
        + (cat_skills.get("tools_and_frameworks") or [])
        + (cat_skills.get("domain_expertise") or [])
    ))

    parts = [
        r.get("summary") or "",
        f"Desired Roles: {', '.join(r.get('desired_roles') or [])}",
        f"Domains: {', '.join(r.get('domains') or [])}",
        f"Skills: {', '.join(all_skills)}",
        f"Experience: {roles}",
        f"Projects: {projs}",
        f"Education: {edu}",
    ]
    if certs:
        parts.append(f"Certifications: {certs}")
    if achievements:
        parts.append(f"Achievements: {achievements}")
    if r.get("languages"):
        parts.append(f"Languages: {', '.join(r.get('languages') or [])}")

    return "\n".join(p for p in parts if p)