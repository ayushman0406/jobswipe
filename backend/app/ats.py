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


def calculate_ats_score(resume: dict, latex: Optional[str] = None) -> dict:
    """Deterministic, comprehensive ATS score evaluation (0-100) with category breakdown."""
    if not resume:
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
    if resume.get("name"):
        contact_score += 3
    else:
        contact_feedback.append("Missing candidate name")

    if resume.get("email") and "@" in resume.get("email", ""):
        contact_score += 3
    else:
        contact_feedback.append("Add a professional email address")

    if resume.get("phone"):
        contact_score += 3
    else:
        contact_feedback.append("Add a direct contact phone number")

    if resume.get("location"):
        contact_score += 3
    else:
        contact_feedback.append("Specify your city/location")

    links = resume.get("links") or {}
    has_links = bool(links.get("linkedin") or links.get("github") or links.get("portfolio") or links.get("website"))
    if has_links:
        contact_score += 3
    else:
        contact_feedback.append("Include LinkedIn or GitHub portfolio links for recruiter credibility")

    # 2. Professional Summary (Max 15)
    summary_score = 0
    summary_feedback = []
    summary = (resume.get("summary") or "").strip()
    words = len(summary.split())
    if summary:
        summary_score += 6
        if 25 <= words <= 140:
            summary_score += 5
        elif words < 25:
            summary_feedback.append("Summary is too brief; aim for 2-3 impactful sentences")
        else:
            summary_feedback.append("Summary is lengthy; condense to high-impact keywords")

        domains = resume.get("domains") or []
        desired = resume.get("desired_roles") or []
        if domains or desired:
            summary_score += 4
    else:
        summary_feedback.append("Add an executive summary targeting your target roles")

    # 3. Work Experience & Quantifiable Impact (Max 30)
    exp_score = 0
    exp_feedback = []
    roles = resume.get("roles") or []
    if roles:
        exp_score += 8
        if len(roles) >= 2:
            exp_score += 4

        # Check for highlights and metrics
        all_highlights = []
        for r in roles:
            all_highlights.extend(r.get("highlights") or [])

        if all_highlights:
            exp_score += 6
            # Look for numbers/metrics: %, $, numbers with k/m/+, or digits
            metric_pattern = re.compile(r"(\d+%|\$\d+|\d+\+|\b\d+\b|\bincreased\b|\breduced\b|\bscaled\b|\bsaved\b)", re.IGNORECASE)
            metrics_count = sum(1 for h in all_highlights if metric_pattern.search(h))
            if metrics_count >= 3:
                exp_score += 7
            elif metrics_count >= 1:
                exp_score += 4
                exp_feedback.append("Add more quantifiable numbers, percentages, or cost/time savings to bullet points")
            else:
                exp_feedback.append("Zero metrics detected. ATS parsers strongly favor quantifiable results (% / $ / scale)")

            # Check action verbs
            action_verbs = {
                "built", "developed", "led", "managed", "designed", "implemented", "orchestrated",
                "engineered", "created", "increased", "reduced", "delivered", "optimized", "streamlined",
                "spearheaded", "directed", "analyzed", "automated", "launched", "executed"
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
    skills = resume.get("skills") or []
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

    cat_skills = resume.get("categorized_skills") or {}
    if cat_skills.get("technical") or cat_skills.get("tools_and_frameworks") or cat_skills.get("soft"):
        skills_score += 5
    else:
        skills_score += 2

    # Check desired roles alignment
    if resume.get("desired_roles"):
        skills_score += 5
    else:
        skills_score += 2

    # 5. Education, Projects & Certifications (Max 20)
    edu_score = 0
    edu_feedback = []
    education = resume.get("education") or []
    if education:
        edu_score += 8
        first_edu = education[0] if isinstance(education, list) else {}
        if first_edu.get("institution") and (first_edu.get("degree") or first_edu.get("year")):
            edu_score += 3
    else:
        edu_feedback.append("Include education credentials with degree and institution")

    certs = resume.get("certifications") or []
    projects = resume.get("projects") or []
    achievements = resume.get("achievements") or []

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
