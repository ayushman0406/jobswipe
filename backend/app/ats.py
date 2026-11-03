import json
import re
from typing import Optional

from .llm import chat, safe_json


def latex_escape(s: str) -> str:
    """Escape LaTeX special characters."""
    if not s:
        return ""
    text = str(s)
    # Map of characters to replace
    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def latex_unescape(text: str) -> str:
    """Unescape LaTeX special characters back to readable text."""
    if not text:
        return ""
    replacements = [
        (r"\&", "&"),
        (r"\%", "%"),
        (r"\$", "$"),
        (r"\_", "_"),
        (r"\#", "#"),
        (r"\{", "{"),
        (r"\}", "}"),
        (r"\textasciitilde{}", "~"),
        (r"\textasciicircum{}", "^"),
        (r"\textbackslash{}", "\\"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def strip_latex_formatting(text: str) -> str:
    """Strip LaTeX tags and environments, returning clean text."""
    if not text:
        return ""
    text = re.sub(r"(?<!\\)%.*$", "", text, flags=re.M)
    text = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)
    text = re.sub(
        r"\\(?:vspace|hspace|geometry|documentclass|usepackage|titleformat|titlespacing|pagestyle|hypersetup)\*?(?:\[[^\]]*\])?\{[^}]*\}",
        "",
        text,
    )
    text = re.sub(r"\\(?:begin|end)\{[^}]*\}(?:\[[^\]]*\])?", "", text)
    text = re.sub(r"\\(?:hfill|titlerule|centering|large|LARGE|Huge|bfseries|uppercase|small|normalsize)", "", text)
    text = text.replace(r"\\", "\n")
    return latex_unescape(text).strip()


def parse_latex_resume(tex: str) -> dict:
    """Parse structured candidate details from LaTeX resume source."""
    result = {
        "name": "",
        "email": "",
        "phone": "",
        "location": "",
        "links": {},
        "summary": "",
        "skills": [],
        "categorized_skills": {"technical": [], "tools_and_frameworks": [], "soft": [], "domain_expertise": []},
        "roles": [],
        "projects": [],
        "education": [],
        "certifications": [],
        "achievements": [],
        "desired_roles": [],
        "domains": [],
    }
    if not tex or not tex.strip():
        return result

    # 1. Contact info
    emails = re.findall(r"mailto:([\w\.-]+@[\w\.-]+\.\w+)", tex) or re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", tex)
    if emails:
        result["email"] = emails[0].strip()

    phones = re.findall(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", tex) or re.findall(
        r"(?:\+?91[\-\s]?)?[6-9]\d{9}", tex
    )
    if phones:
        result["phone"] = phones[0].strip()

    li = re.findall(r"\\href\{([^}]*linkedin\.com[^}]*)\}", tex, re.IGNORECASE) or re.findall(
        r"https?://(?:www\.)?linkedin\.com/in/[\w\-]+", tex
    )
    if li:
        result["links"]["linkedin"] = li[0].strip()

    gh = re.findall(r"\\href\{([^}]*github\.com[^}]*)\}", tex, re.IGNORECASE) or re.findall(
        r"https?://(?:www\.)?github\.com/[\w\-]+", tex
    )
    if gh:
        result["links"]["github"] = gh[0].strip()

    port = re.findall(r"\\href\{([^}]+)\}\{(?:Portfolio|Website)\}", tex, re.IGNORECASE)
    if port:
        result["links"]["portfolio"] = port[0].strip()

    # Name
    name_m = re.search(r"\\begin\{center\}[\s\S]*?\{\\(?:LARGE|Large|Huge)\s*\\textbf\{([^}]+)\}\}", tex)
    if not name_m:
        name_m = re.search(r"\{\\(?:LARGE|Large|Huge)\s*\\textbf\{([^}]+)\}\}", tex)
    if not name_m:
        name_m = re.search(r"\\textbf\{([^}]+)\}", tex)
    if name_m:
        result["name"] = latex_unescape(name_m.group(1)).strip()

    # Location in header
    header_block = tex[:1200]
    loc_m = re.search(r"\$\|\$\s*([A-Za-z\s,]+?)\s*\$\|\$", header_block)
    if loc_m:
        cand_loc = loc_m.group(1).strip()
        if not any(k in cand_loc.lower() for k in ["http", "@", "github", "linkedin", "phone", "email"]):
            result["location"] = cand_loc

    # Sections
    sections = re.split(r"\\section\*?\{([^}]+)\}", tex)
    for i in range(1, len(sections), 2):
        sec_title = sections[i].upper().strip()
        sec_content = sections[i + 1] if i + 1 < len(sections) else ""

        if any(k in sec_title for k in ("SUMMARY", "PROFILE", "OBJECTIVE")):
            result["summary"] = strip_latex_formatting(sec_content)

        elif any(k in sec_title for k in ("SKILL", "COMPETENC")):
            cleaned = strip_latex_formatting(sec_content)
            latex_junk = {"document", "article", "center", "itemize", "enumerate", "table", "tabular", "minipage"}
            for line in cleaned.split("\n"):
                line = re.sub(r"^\d+pt\b", "", line).strip()
                if not line:
                    continue
                parts = re.split(r"[:\-]\s*", line, maxsplit=1)
                sub_skills = [
                    s.strip().lower()
                    for s in re.split(r"[,•|;]+", parts[-1])
                    if s.strip()
                    and s.strip().lower() not in latex_junk
                    and not s.strip().endswith("pt")
                    and len(s.strip()) > 1
                ]
                if len(parts) > 1:
                    header = parts[0].lower()
                    if any(w in header for w in ("tech", "language", "stack")):
                        result["categorized_skills"]["technical"].extend(sub_skills)
                    elif any(w in header for w in ("tool", "platform", "framework", "cloud")):
                        result["categorized_skills"]["tools_and_frameworks"].extend(sub_skills)
                    elif any(w in header for w in ("soft", "competenc", "lead")):
                        result["categorized_skills"]["soft"].extend(sub_skills)
                    else:
                        result["categorized_skills"]["domain_expertise"].extend(sub_skills)
                result["skills"].extend(sub_skills)
            result["skills"] = sorted(set(result["skills"]))

        elif any(k in sec_title for k in ("EXPERIENCE", "WORK", "EMPLOYMENT", "HISTORY")):
            role_blocks = re.split(r"\\vspace\{[^}]*\}|(?=\\textbf\{[^}]+\}\s*(?:\$\|\$|\|)\s*\\textit\{)", sec_content)
            for rb in role_blocks:
                rb = rb.strip()
                if not rb or rb.startswith("%"):
                    continue
                tc_m = re.search(r"\\textbf\{([^}]+)\}\s*(?:\$\|\$|\|)\s*\\textit\{([^}]+)\}(?:[^\\]*?\\hfill\s*([^\\]+))?", rb)
                raw_items = re.findall(r"\\item\s*(.+?)(?=\\item|\n\s*\\end|\Z)", rb, flags=re.S)
                items = [strip_latex_formatting(h) for h in raw_items if strip_latex_formatting(h)]
                if tc_m:
                    title = latex_unescape(tc_m.group(1)).strip()
                    company = latex_unescape(tc_m.group(2)).strip()
                    dates = latex_unescape(tc_m.group(3) or "").strip()
                    result["roles"].append({
                        "title": title,
                        "company": company,
                        "start": dates,
                        "highlights": items,
                    })
                elif items:
                    result["roles"].append({
                        "title": "Role",
                        "company": "",
                        "highlights": items,
                    })

        elif "PROJECT" in sec_title:
            p_blocks = re.split(r"\\vspace\{[^}]*\}|(?=\\textbf\{[^}]+\}(?:\$\|\$|\||\\\\))", sec_content)
            for pb in p_blocks:
                pb = pb.strip()
                if not pb or pb.startswith("%"):
                    continue
                pname_m = re.search(r"\\textbf\{([^}]+)\}", pb)
                raw_items = re.findall(r"\\item\s*(.+?)(?=\\item|\n\s*\\end|\Z)", pb, flags=re.S)
                items = [strip_latex_formatting(h) for h in raw_items if strip_latex_formatting(h)]
                if pname_m:
                    result["projects"].append({
                        "name": latex_unescape(pname_m.group(1)).strip(),
                        "description": " ".join(items) if items else strip_latex_formatting(pb),
                        "highlights": items,
                    })

        elif "EDUCATION" in sec_title:
            edu_blocks = re.split(r"\\vspace\{[^}]*\}|(?=\\textbf\{[^}]+\}\s*\\hfill)", sec_content)
            for eb in edu_blocks:
                eb = eb.strip()
                if not eb or eb.startswith("%"):
                    continue
                inst_m = re.search(r"\\textbf\{([^}]+)\}(?:[^\\]*?\\hfill\s*([^\\]+))?", eb)
                deg_m = re.search(r"\\textit\{([^}]+)\}", eb)
                if inst_m:
                    result["education"].append({
                        "institution": latex_unescape(inst_m.group(1)).strip(),
                        "year": latex_unescape(inst_m.group(2) or "").strip(),
                        "degree": latex_unescape(deg_m.group(1) if deg_m else "").strip(),
                    })

        elif any(k in sec_title for k in ("CERTIFICATION", "ACHIEVEMENT")):
            raw_items = re.findall(r"\\item\s*(.+?)(?=\\item|\n\s*\\end|\Z)", sec_content, flags=re.S)
            for itm in raw_items:
                clean_itm = strip_latex_formatting(itm)
                if clean_itm:
                    result["certifications"].append({"name": clean_itm})

    return result


def calculate_ats_score(resume: dict, latex: Optional[str] = None) -> dict:
    """Deterministic, comprehensive ATS score evaluation (0-100) with category breakdown."""
    res = dict(resume or {})

    # If LaTeX is provided, merge and enrich extracted fields
    if latex and latex.strip():
        parsed = parse_latex_resume(latex)
        if not res.get("name") and parsed.get("name"):
            res["name"] = parsed["name"]
        if not res.get("email") and parsed.get("email"):
            res["email"] = parsed["email"]
        if not res.get("phone") and parsed.get("phone"):
            res["phone"] = parsed["phone"]
        if not res.get("location") and parsed.get("location"):
            res["location"] = parsed["location"]
        if not res.get("summary") and parsed.get("summary"):
            res["summary"] = parsed["summary"]

        merged_links = dict(res.get("links") or {})
        for k, v in (parsed.get("links") or {}).items():
            if v and not merged_links.get(k):
                merged_links[k] = v
        res["links"] = merged_links

        existing_skills = set(res.get("skills") or [])
        latex_skills = set(parsed.get("skills") or [])
        res["skills"] = sorted(existing_skills | latex_skills)

        res_cat = dict(res.get("categorized_skills") or {})
        parsed_cat = parsed.get("categorized_skills") or {}
        for cat_k in ("technical", "tools_and_frameworks", "soft", "domain_expertise"):
            res_cat[cat_k] = sorted(set(res_cat.get(cat_k) or []) | set(parsed_cat.get(cat_k) or []))
        res["categorized_skills"] = res_cat

        if parsed.get("roles"):
            if not res.get("roles") or len(parsed["roles"]) >= len(res.get("roles") or []):
                res["roles"] = parsed["roles"]

        if parsed.get("education") and not res.get("education"):
            res["education"] = parsed["education"]
        if parsed.get("projects") and not res.get("projects"):
            res["projects"] = parsed["projects"]
        if parsed.get("certifications") and not res.get("certifications"):
            res["certifications"] = parsed["certifications"]

    has_substance = bool(
        res.get("name")
        or res.get("skills")
        or res.get("roles")
        or res.get("education")
        or res.get("summary")
        or (latex and len(latex.strip()) > 80)
    )

    if not has_substance:
        return {
            "overall_score": 0,
            "rating": "No Resume",
            "breakdown": {
                "contact": {"score": 0, "max": 15, "feedback": "Missing contact information"},
                "summary": {"score": 0, "max": 15, "feedback": "Missing professional summary"},
                "experience": {"score": 0, "max": 30, "feedback": "No work experience listed"},
                "skills": {"score": 0, "max": 20, "feedback": "No skills extracted"},
                "education_certs": {"score": 0, "max": 20, "feedback": "No education or certifications found"},
            },
            "strengths": [],
            "improvements": [
                {
                    "title": "Upload your resume",
                    "description": "Upload a PDF resume to calculate your personalized ATS score.",
                    "priority": "high",
                    "prompt": "How can I build an ATS-friendly resume from scratch?",
                }
            ],
        }

    # 1. Contact & Links (Max 15)
    contact_score = 0
    contact_feedback = []
    if res.get("name"):
        contact_score += 3
    else:
        contact_feedback.append("Missing candidate name")

    if res.get("email") and "@" in res.get("email", ""):
        contact_score += 3
    else:
        contact_feedback.append("Add a professional email address")

    if res.get("phone"):
        contact_score += 3
    else:
        contact_feedback.append("Add a direct contact phone number")

    if res.get("location"):
        contact_score += 3
    else:
        contact_feedback.append("Specify your city/location")

    links = res.get("links") or {}
    has_links = bool(links.get("linkedin") or links.get("github") or links.get("portfolio") or links.get("website"))
    if has_links:
        contact_score += 3
    else:
        contact_feedback.append("Include LinkedIn or GitHub portfolio links for recruiter credibility")

    # 2. Professional Summary (Max 15)
    summary_score = 0
    summary_feedback = []
    summary = (res.get("summary") or "").strip()
    words = len(summary.split())
    if summary:
        summary_score += 6
        if 20 <= words <= 150:
            summary_score += 5
        elif words < 20:
            summary_feedback.append("Summary is too brief; aim for 2-3 impactful sentences")
        else:
            summary_feedback.append("Summary is lengthy; condense to high-impact keywords")

        domains = res.get("domains") or []
        desired = res.get("desired_roles") or []
        if domains or desired:
            summary_score += 4
        else:
            summary_score += 2
    else:
        summary_feedback.append("Add an executive summary targeting your target roles")

    # 3. Work Experience & Quantifiable Impact (Max 30)
    exp_score = 0
    exp_feedback = []
    roles = res.get("roles") or []
    if roles:
        exp_score += 8
        if len(roles) >= 2:
            exp_score += 4

        all_highlights = []
        for r in roles:
            all_highlights.extend(r.get("highlights") or [])

        if all_highlights:
            exp_score += 6
            metric_pattern = re.compile(r"(\d+%|\$\d+|\d+\+|\b\d+\b|\bincreased\b|\breduced\b|\bscaled\b|\bsaved\b)", re.IGNORECASE)
            metrics_count = sum(1 for h in all_highlights if metric_pattern.search(h))
            if metrics_count >= 3:
                exp_score += 7
            elif metrics_count >= 1:
                exp_score += 4
                exp_feedback.append("Add more quantifiable numbers, percentages, or cost/time savings to bullet points")
            else:
                exp_feedback.append("Zero metrics detected. ATS parsers strongly favor quantifiable results (% / $ / scale)")

            action_verbs = {
                "built", "developed", "led", "managed", "designed", "implemented", "orchestrated",
                "engineered", "created", "increased", "reduced", "delivered", "optimized", "streamlined",
                "spearheaded", "directed", "analyzed", "automated", "launched", "executed", "architected"
            }
            has_action_verbs = any(any(h.lower().strip().startswith(v) for v in action_verbs) for h in all_highlights)
            if has_action_verbs:
                exp_score += 5
            else:
                exp_feedback.append("Start each bullet point with strong action verbs (e.g. Engineered, Spearheaded, Optimized)")
        else:
            exp_feedback.append("Add bullet point achievements to your job roles")
    else:
        exp_feedback.append("No roles listed. Detail your work experience, internships, or relevant leadership")

    # 4. Skills & Keywords (Max 20)
    skills_score = 0
    skills_feedback = []
    skills = res.get("skills") or []
    if len(skills) >= 10:
        skills_score += 10
    elif len(skills) >= 5:
        skills_score += 7
        skills_feedback.append("Include more specific tools and technical proficiencies")
    elif len(skills) > 0:
        skills_score += 4
        skills_feedback.append("Add at least 8-12 relevant industry skills")
    else:
        skills_feedback.append("Add a dedicated skills section with key tools and technologies")

    cat_skills = res.get("categorized_skills") or {}
    if cat_skills.get("technical") or cat_skills.get("tools_and_frameworks") or cat_skills.get("soft"):
        skills_score += 5
    else:
        skills_score += 2

    if res.get("desired_roles"):
        skills_score += 5
    elif len(skills) >= 6:
        skills_score += 3
    else:
        skills_score += 1

    # 5. Education, Projects & Certifications (Max 20)
    edu_score = 0
    edu_feedback = []
    education = res.get("education") or []
    if education:
        edu_score += 8
        first_edu = education[0] if isinstance(education, list) else {}
        if first_edu.get("institution") and (first_edu.get("degree") or first_edu.get("year")):
            edu_score += 3
    else:
        edu_feedback.append("Include education credentials with degree and institution")

    certs = res.get("certifications") or []
    projects = res.get("projects") or []
    achievements = res.get("achievements") or []

    if certs:
        edu_score += 5
    elif projects:
        edu_score += 4
    else:
        edu_feedback.append("Add relevant industry certifications or standout side projects")

    if achievements or len(projects) >= 2:
        edu_score += 4
    elif projects:
        edu_score += 2

    total_score = min(100, contact_score + summary_score + exp_score + skills_score + edu_score)

    if total_score >= 88:
        rating = "Exceptional"
    elif total_score >= 75:
        rating = "Strong"
    elif total_score >= 60:
        rating = "Good"
    else:
        rating = "Needs Work"

    strengths = []
    if contact_score >= 12:
        strengths.append("Complete contact details with active professional links")
    if summary_score >= 11:
        strengths.append("Clear executive summary with strategic role alignment")
    if exp_score >= 20:
        strengths.append("Detailed work history with quantifiable impact metrics")
    if skills_score >= 15:
        strengths.append("Strong keyword diversity across tools and frameworks")
    if edu_score >= 15:
        strengths.append("Well-documented education and certifications profile")
    if not strengths:
        strengths.append("Clean foundation ready for targeted optimization")

    improvements = []
    if exp_feedback:
        improvements.append({
            "title": "Quantify Role Impact",
            "description": exp_feedback[0],
            "priority": "high",
            "prompt": "Rewrite my work experience bullet points to include specific percentages, metrics, and strong action verbs.",
        })
    if skills_feedback:
        improvements.append({
            "title": "Expand Core Keywords",
            "description": skills_feedback[0],
            "priority": "high" if skills_score < 10 else "medium",
            "prompt": "Suggest the top 8 technical and domain skills I should add to pass ATS filters for my desired roles.",
        })
    if contact_feedback:
        improvements.append({
            "title": "Enhance Professional Links",
            "description": contact_feedback[0],
            "priority": "medium",
            "prompt": "Add my LinkedIn, GitHub, and portfolio links cleanly into the LaTeX header.",
        })
    if summary_feedback:
        improvements.append({
            "title": "Refine Executive Summary",
            "description": summary_feedback[0],
            "priority": "medium",
            "prompt": "Write a punchy 3-sentence executive summary tailored for high ATS matching.",
        })
    if edu_feedback:
        improvements.append({
            "title": "Highlight Certifications & Projects",
            "description": edu_feedback[0],
            "priority": "low",
            "prompt": "Add a dedicated Certifications & Key Projects section to boost ATS credentials.",
        })

    return {
        "overall_score": total_score,
        "rating": rating,
        "breakdown": {
            "contact": {"score": contact_score, "max": 15, "feedback": "; ".join(contact_feedback) or "Good"},
            "summary": {"score": summary_score, "max": 15, "feedback": "; ".join(summary_feedback) or "Good"},
            "experience": {"score": exp_score, "max": 30, "feedback": "; ".join(exp_feedback) or "Good"},
            "skills": {"score": skills_score, "max": 20, "feedback": "; ".join(skills_feedback) or "Good"},
            "education_certs": {"score": edu_score, "max": 20, "feedback": "; ".join(edu_feedback) or "Good"},
        },
        "strengths": strengths,
        "improvements": improvements,
    }


def generate_latex_resume(resume: dict) -> str:
    """Generate clean, ATS-compliant single-column LaTeX resume."""
    name = latex_escape(resume.get("name") or "Your Name")
    email = latex_escape(resume.get("email") or "")
    phone = latex_escape(resume.get("phone") or "")
    location = latex_escape(resume.get("location") or "")
    links = resume.get("links") or {}
    linkedin = latex_escape(links.get("linkedin") or "")
    github = latex_escape(links.get("github") or "")
    portfolio = latex_escape(links.get("portfolio") or links.get("website") or "")

    contact_parts = []
    if email:
        contact_parts.append(r"\href{mailto:" + email + r"}{" + email + r"}")
    if phone:
        contact_parts.append(phone)
    if location:
        contact_parts.append(location)
    if linkedin:
        contact_parts.append(r"\href{" + linkedin + r"}{LinkedIn}")
    if github:
        contact_parts.append(r"\href{" + github + r"}{GitHub}")
    if portfolio:
        contact_parts.append(r"\href{" + portfolio + r"}{Portfolio}")

    contact_line = " $|$ ".join(contact_parts) if contact_parts else "Email $|$ Phone $|$ Location"

    summary = latex_escape(resume.get("summary") or "")

    # Skills
    skills = [latex_escape(s) for s in (resume.get("skills") or [])]
    skills_line = ", ".join(skills) if skills else "Technical Skills"

    cat_skills = resume.get("categorized_skills") or {}
    tech_skills = ", ".join(latex_escape(s) for s in cat_skills.get("technical") or [])
    tools_skills = ", ".join(latex_escape(s) for s in cat_skills.get("tools_and_frameworks") or [])
    soft_skills = ", ".join(latex_escape(s) for s in cat_skills.get("soft") or [])

    # Roles
    roles = resume.get("roles") or []
    roles_latex = []
    for r in roles:
        title = latex_escape(r.get("title") or "Role")
        company = latex_escape(r.get("company") or "Company")
        start = latex_escape(r.get("start") or "")
        end = latex_escape(r.get("end") or "Present")
        date_str = f"{start} -- {end}".strip(" -") if start or end else ""
        loc = latex_escape(r.get("location") or "")

        highlights = r.get("highlights") or []
        items = "\n".join(f"    \\item {latex_escape(h)}" for h in highlights if h)
        if not items:
            items = "    \\item Contributed to core business objectives and project deliverables."

        role_block = f"""\\textbf{{{title}}} $|$ \\textit{{{company}}} \\hfill {date_str} \\\\
\\begin{{itemize}}[leftmargin=1.5em, topsep=2pt, itemsep=1.5pt]
{items}
\\end{{itemize}}"""
        roles_latex.append(role_block)

    roles_body = "\n\\vspace{4pt}\n".join(roles_latex) if roles_latex else "% No prior roles listed"

    # Projects
    projects = resume.get("projects") or []
    projects_latex = []
    for p in projects:
        pname = latex_escape(p.get("name") or "Project")
        tech = ", ".join(latex_escape(t) for t in (p.get("tech") or []))
        tech_str = f" $|$ \\textit{{{tech}}}" if tech else ""
        desc = latex_escape(p.get("description") or "")
        highlights = p.get("highlights") or []
        items = "\n".join(f"    \\item {latex_escape(h)}" for h in highlights if h)
        if not items and desc:
            items = f"    \\item {desc}"
        if not items:
            items = "    \\item Developed scalable solution adhering to best software practices."

        p_block = f"""\\textbf{{{pname}}}{tech_str} \\\\
\\begin{{itemize}}[leftmargin=1.5em, topsep=2pt, itemsep=1.5pt]
{items}
\\end{{itemize}}"""
        projects_latex.append(p_block)

    projects_body = "\n\\vspace{4pt}\n".join(projects_latex) if projects_latex else ""

    # Education
    education = resume.get("education") or []
    edu_latex = []
    for e in education:
        deg = latex_escape(e.get("degree") or "Degree")
        inst = latex_escape(e.get("institution") or "University")
        year = latex_escape(str(e.get("year") or ""))
        field = latex_escape(e.get("field_of_study") or "")
        grade = latex_escape(e.get("grade") or e.get("grade_or_gpa") or "")
        extra = f" -- {field}" if field else ""
        if grade:
            extra += f" (GPA: {grade})"

        edu_block = f"""\\textbf{{{inst}}} \\hfill {year} \\\\
\\textit{{{deg}{extra}}}"""
        edu_latex.append(edu_block)

    edu_body = "\n\\vspace{4pt}\n".join(edu_latex) if edu_latex else "% Education details"

    # Certifications & Achievements
    certs = resume.get("certifications") or []
    achievements = resume.get("achievements") or []
    cert_items = []
    for c in certs:
        cname = latex_escape(c.get("name") if isinstance(c, dict) else str(c))
        cissuer = latex_escape(c.get("issuer") or "") if isinstance(c, dict) else ""
        cyear = latex_escape(str(c.get("year") or "")) if isinstance(c, dict) else ""
        details = f" ({cissuer})" if cissuer else ""
        if cyear:
            details += f" -- {cyear}"
        cert_items.append(f"\\item \\textbf{{{cname}}}{details}")

    for a in achievements:
        aname = latex_escape(a.get("title") if isinstance(a, dict) else str(a))
        adesc = latex_escape(a.get("description") or "") if isinstance(a, dict) else ""
        cert_items.append(f"\\item \\textbf{{{aname}}}: {adesc}" if adesc else f"\\item \\textbf{{{aname}}}")

    cert_section = ""
    if cert_items:
        cert_items_joined = "\n".join("    " + ci for ci in cert_items)
        cert_section = f"""\\section*{{CERTIFICATIONS \\& ACHIEVEMENTS}}
\\begin{{itemize}}[leftmargin=1.5em, topsep=2pt, itemsep=1.5pt]
{cert_items_joined}
\\end{{itemize}}
\\vspace{{6pt}}"""

    # Skills block
    skills_block = ""
    if tech_skills or tools_skills or soft_skills:
        skill_lines = []
        if tech_skills:
            skill_lines.append(f"\\textbf{{Technical Skills:}} {tech_skills}")
        if tools_skills:
            skill_lines.append(f"\\textbf{{Tools \\& Platforms:}} {tools_skills}")
        if soft_skills:
            skill_lines.append(f"\\textbf{{Core Competencies:}} {soft_skills}")
        skills_block = " \\\\\n".join(skill_lines)
    else:
        skills_block = f"\\textbf{{Skills:}} {skills_line}"

    summary_section = ""
    if summary:
        summary_section = f"""\\section*{{PROFESSIONAL SUMMARY}}
{summary}
\\vspace{{6pt}}"""

    projects_section = ""
    if projects_body:
        projects_section = f"""\\section*{{KEY PROJECTS}}
{projects_body}
\\vspace{{6pt}}"""

    template = f"""\\documentclass[letterpaper,10pt]{{article}}
\\usepackage[top=0.6in, bottom=0.6in, left=0.6in, right=0.6in]{{geometry}}
\\usepackage{{hyperref}}
\\usepackage{{enumitem}}
\\usepackage{{titlesec}}
\\usepackage{{palatino}}

\\hypersetup{{
    colorlinks=true,
    linkcolor=black,
    filecolor=black,
    urlcolor=blue,
}}

\\titleformat{{\\section*}}{{\\large\\bfseries\\uppercase}}{{}}{{0em}}{{}}[\\titlerule]
\\titlespacing*{{\\section*}}{{0pt}}{{6pt}}{{4pt}}
\\pagestyle{{empty}}

\\begin{{document}}

% HEADER
\\begin{{center}}
    {{\\LARGE \\textbf{{{name}}}}} \\\\[3pt]
    {contact_line}
\\end{{center}}
\\vspace{{4pt}}

{summary_section}
\\section*{{TECHNICAL \\& DOMAIN SKILLS}}
{skills_block}
\\vspace{{6pt}}

\\section*{{WORK EXPERIENCE}}
{roles_body}
\\vspace{{6pt}}

{projects_section}
\\section*{{EDUCATION}}
{edu_body}
\\vspace{{6pt}}

{cert_section}

\\end{{document}}"""

    return template.strip()


SYSTEM_IMPROVE = """You are an elite ATS Resume Optimization Consultant and LaTeX typesetting specialist.
Your goal is to help the job seeker improve their resume to maximize ATS (Applicant Tracking System) scores,
readability, and recruiter conversion.

You will receive:
1. The user's input request / question
2. The current LaTeX resume code
3. Parsed resume structured metadata
4. Chat conversation history

Instructions:
1. Make targeted, high-impact improvements to the LaTeX document based on the user's request.
2. Ensure the output LaTeX is syntactically valid, adheres to single-column ATS guidelines, and compiles cleanly.
3. Escape all LaTeX special characters properly (&, %, $, #, _, {, }).
4. Emphasize quantifiable metrics (% improvements, cost savings, user scale) and strong action verbs (Engineered, Spearheaded, Optimized).
5. Return ONLY a valid JSON object with EXACTLY these keys:
   - "reply": Clear, encouraging explanation of the changes made and how they boost ATS performance.
   - "latex": The complete, updated LaTeX resume document.
   - "changes_made": List of concise strings detailing what was updated.
   - "estimated_score": Updated estimated ATS score (integer between 0 and 100).
   - "quick_prompts": 3 relevant, actionable follow-up prompt strings the user can click next.
Output JSON only."""


def chat_improve_resume(user_message: str, current_latex: str, resume_dict: dict, chat_history: list = None) -> dict:
    """Chat with AI resume coach to iteratively refine and optimize the LaTeX resume."""
    history = chat_history or []
    messages = [{"role": "system", "content": SYSTEM_IMPROVE}]

    # Include recent chat history
    for turn in history[-6:]:
        messages.append({"role": turn.get("role", "user"), "content": turn.get("content", "")})

    user_payload = {
        "user_request": user_message,
        "current_latex": current_latex,
        "candidate_summary": {
            "name": resume_dict.get("name"),
            "desired_roles": resume_dict.get("desired_roles"),
            "domains": resume_dict.get("domains"),
            "total_experience_years": resume_dict.get("total_experience_years"),
        },
    }

    messages.append({"role": "user", "content": json.dumps(user_payload)})
    r = chat(messages, json_mode=True, temperature=0.2)
    result = safe_json(r.choices[0].message.content)

    # Sanity defaults
    if "latex" not in result or not result["latex"].strip():
        result["latex"] = current_latex
    if "reply" not in result:
        result["reply"] = "I've reviewed and updated your resume based on ATS best practices."
    if "changes_made" not in result:
        result["changes_made"] = ["Updated LaTeX structure for ATS parsing"]
    if "quick_prompts" not in result:
        result["quick_prompts"] = [
            "Add more quantifiable metrics to bullet points",
            "Tailor skills keywords for my target roles",
            "Condense to exactly 1 page",
        ]

    return result
