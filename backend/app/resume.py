import fitz  # PyMuPDF

from .llm import json_chat

SYSTEM = """Extract the resume into JSON with exactly these keys:
name, email, phone, location, summary,
total_experience_years (number),
skills (list of lowercase strings — canonical and concrete, e.g. "python", "pytorch", "tally", "gst",
"patient care", "welding", "cnc", "sales", "house wiring", "classroom management"),
roles (list of {title, company, start, end, highlights[]}),
education (list of {degree, institution, year}),
projects (list of {name, description, tech[]}),
languages (spoken languages, lowercase: english, hindi, kannada, tamil, telugu, marathi, ...),
desired_roles (list of 2-4 job titles that best fit this person),
domains (list of category slugs that fit, chosen ONLY from:
technology, sales, management, retail, mechanical, finance, healthcare, hospitality, education,
logistics, hr, marketing, support, legal, trades, agriculture, creative, operations).
Use null when missing. Never invent facts. A shop cashier, a CA, a nurse and a fitter are all valid profiles.
Output JSON only."""


def pdf_to_text(data: bytes) -> str:
    with fitz.open(stream=data, filetype="pdf") as doc:
        return "\n".join(p.get_text() for p in doc)


def resume_reader(pdf_bytes: bytes) -> dict:
    """pdf -> structured resume json"""
    text = pdf_to_text(pdf_bytes)
    if len(text.strip()) < 50:
        raise ValueError("No text layer found in PDF; OCR needed")
    r = json_chat(SYSTEM, text[:12000])
    r["skills"] = sorted({s.strip().lower() for s in (r.get("skills") or []) if s})
    r["domains"] = sorted({str(d).strip().lower() for d in (r.get("domains") or []) if d})
    return r


def resume_to_text(r: dict) -> str:
    roles = "; ".join(f"{x.get('title')} at {x.get('company')}" for x in r.get("roles") or [])
    projs = "; ".join(f"{p.get('name')}: {p.get('description')}" for p in r.get("projects") or [])
    edu = "; ".join(f"{e.get('degree')} {e.get('institution')}" for e in r.get("education") or [])
    return (
        f"{r.get('summary') or ''}\nDesired: {', '.join(r.get('desired_roles') or [])}\n"
        f"Domains: {', '.join(r.get('domains') or [])}\n"
        f"Skills: {', '.join(r.get('skills') or [])}\nEducation: {edu}\n"
        f"Experience: {roles}\nProjects: {projs}"
    )