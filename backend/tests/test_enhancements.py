import os
import sys
import unittest
from fastapi.testclient import TestClient

# Ensure app can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.ats import calculate_ats_score, generate_latex_resume, latex_escape
from app.models import Job, User
from app.matching import job_to_dict


class TestJobSwipeEnhancements(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_latex_escape(self):
        raw = "Sales & Marketing (50% growth) in $USD_INR #1 {best} ~approx^"
        escaped = latex_escape(raw)
        self.assertIn(r"\&", escaped)
        self.assertIn(r"\%", escaped)
        self.assertIn(r"\$", escaped)
        self.assertIn(r"\_", escaped)
        self.assertIn(r"\#", escaped)
        self.assertIn(r"\{", escaped)
        self.assertIn(r"\}", escaped)
        self.assertNotIn("~approx", escaped) # escaped with textasciitilde

    def test_ats_empty_resume(self):
        res = calculate_ats_score({})
        self.assertEqual(res["overall_score"], 0)
        self.assertEqual(res["rating"], "No Resume")
        self.assertTrue(len(res["improvements"]) > 0)

    def test_ats_scoring_metrics(self):
        # Weak resume
        weak_resume = {
            "name": "Jane Doe",
            "skills": ["communication"],
            "roles": [{"title": "Assistant", "company": "ABC Corp", "highlights": ["Worked on tasks"]}]
        }
        weak_ats = calculate_ats_score(weak_resume)

        # Strong resume
        strong_resume = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "+1 234 567 8900",
            "location": "Bengaluru, India",
            "links": {"linkedin": "https://linkedin.com/in/jane", "github": "https://github.com/jane"},
            "summary": "Accomplished engineering lead with 6 years experience scaling distributed Python cloud platforms.",
            "skills": ["python", "fastapi", "docker", "kubernetes", "postgresql", "aws", "redis", "terraform"],
            "categorized_skills": {
                "technical": ["python", "fastapi", "postgresql"],
                "tools_and_frameworks": ["docker", "kubernetes", "aws"]
            },
            "roles": [
                {
                    "title": "Senior Cloud Engineer",
                    "company": "TechCorp",
                    "highlights": [
                        "Architected event-driven microservices handling 50M+ requests/day with 99.99% reliability.",
                        "Reduced cloud infrastructure spend by 35% through container rightsizing and auto-scaling.",
                        "Spearheaded migration of legacy monolith to Kubernetes, accelerating release frequency by 3x."
                    ]
                }
            ],
            "education": [{"degree": "B.Tech", "institution": "IIT Madras", "year": "2018"}],
            "projects": [{"name": "CloudOps Automation", "tech": ["Python", "Terraform"], "description": "Automated deployment"}],
            "certifications": [{"name": "AWS Certified Solutions Architect - Professional", "issuer": "AWS", "year": "2023"}],
            "desired_roles": ["Senior Cloud Engineer", "Backend Lead"],
            "domains": ["technology"]
        }
        strong_ats = calculate_ats_score(strong_resume)

        self.assertGreater(strong_ats["overall_score"], weak_ats["overall_score"])
        self.assertGreaterEqual(strong_ats["overall_score"], 80)
        self.assertEqual(strong_ats["rating"], "Strong" if strong_ats["overall_score"] < 88 else "Exceptional")
        self.assertTrue(len(strong_ats["strengths"]) >= 3)

    def test_latex_generation(self):
        resume = {
            "name": "Priya Nair",
            "email": "priya@example.com",
            "phone": "+91 9123456789",
            "location": "Mumbai",
            "links": {"linkedin": "https://linkedin.com/in/priya"},
            "summary": "Senior Product Manager specializing in B2B SaaS and high-retention consumer products.",
            "skills": ["product strategy", "sql", "jira", "figma", "user research"],
            "roles": [
                {
                    "title": "Lead PM",
                    "company": "GrowthX",
                    "highlights": ["Scaled MAU from 200k to 1.2M within 14 months."]
                }
            ],
            "education": [{"degree": "MBA", "institution": "IIM Ahmedabad", "year": "2020"}]
        }
        tex = generate_latex_resume(resume)
        self.assertIn(r"\documentclass", tex)
        self.assertIn("Priya Nair", tex)
        self.assertIn("GrowthX", tex)
        self.assertIn("1.2M", tex)
        self.assertIn(r"\end{document}", tex)

    def test_job_invitation_photos_and_quotes(self):
        j = Job(
            id=999,
            title="Senior AI Engineer",
            company="NeuralLabs",
            category="technology",
            location="Bengaluru"
        )
        d = job_to_dict(j)
        self.assertTrue(d["photo_url"].startswith("http"))
        self.assertTrue(d["company_logo"].startswith("http"))
        self.assertTrue(len(d["hiring_quote"]) > 10)
        self.assertIn("team", d["hiring_quote"].lower())

    def test_api_user_and_ats_endpoints(self):
        # Create user
        res = self.client.post("/users", json={"name": "Vikram", "email": "vikram@test.com", "preferred_lang": "en"})
        self.assertEqual(res.status_code, 200)
        u = res.json()
        uid = u["id"]

        # Update LaTeX directly
        sample_tex = r"\documentclass{article}\begin{document}Vikram Resume\end{document}"
        res = self.client.put(f"/users/{uid}/resume/latex", json={"latex": sample_tex})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["latex"], sample_tex)

        # Get ATS
        res = self.client.get(f"/users/{uid}")
        self.assertEqual(res.status_code, 200)
        user_data = res.json()
        self.assertTrue(user_data["has_latex"])

    def test_parse_latex_resume_and_ats_evaluation(self):
        sample_tex = r"""\documentclass[letterpaper,10pt]{article}
\begin{document}
\begin{center}
    {\LARGE \textbf{Arjun Mehra}} \\[3pt]
    \href{mailto:arjun@example.com}{arjun@example.com} $|$ +91 9876543210 $|$ Bengaluru $|$ \href{https://linkedin.com/in/arjun}{LinkedIn} $|$ \href{https://github.com/arjun}{GitHub}
\end{center}
\section*{PROFESSIONAL SUMMARY}
Senior Backend Architect and Distributed Systems Lead with 7+ years of deep expertise designing event-driven streaming pipelines, cloud-native infrastructure, and high-concurrency microservices.
\section*{TECHNICAL \& DOMAIN SKILLS}
\textbf{Technical Skills:} python, fastapi, postgresql, redis, kafka, go, grpc \\
\textbf{Tools \& Platforms:} docker, kubernetes, aws, terraform, prometheus, grafana
\section*{WORK EXPERIENCE}
\textbf{Staff Infrastructure Engineer} $|$ \textit{CloudGrid Labs} \hfill 2021 -- Present \\
\begin{itemize}
    \item Architected real-time streaming pipeline processing 150M events/day with 99.99\% reliability.
    \item Reduced cloud infrastructure costs by 40\% (\$120,000 annual savings) via workload rightsizing.
    \item Spearheaded zero-downtime database migration to distributed PostgreSQL, accelerating queries by 3x.
\end{itemize}
\vspace{4pt}
\textbf{Senior Cloud Engineer} $|$ \textit{DataScale Tech} \hfill 2018 -- 2021 \\
\begin{itemize}
    \item Automated CI/CD deployments across 80 Kubernetes microservices reducing lead time by 65\%.
    \item Optimized Kafka consumers to handle 45,000 messages/sec with sub-50ms latency.
\end{itemize}
\section*{KEY PROJECTS}
\textbf{StreamSync Engine} $|$ \textit{Python, Rust, Kafka} \\
\begin{itemize}
    \item Built open-source telemetry engine downloaded over 20,000 times by developers worldwide.
\end{itemize}
\section*{EDUCATION}
\textbf{IIT Delhi} \hfill 2018 \\
\textit{B.Tech in Computer Science}
\section*{CERTIFICATIONS}
\begin{itemize}
    \item \textbf{AWS Certified Solutions Architect -- Professional} -- 2023
\end{itemize}
\end{document}"""

        from app.ats import parse_latex_resume
        parsed = parse_latex_resume(sample_tex)
        self.assertEqual(parsed["name"], "Arjun Mehra")
        self.assertEqual(parsed["email"], "arjun@example.com")
        self.assertEqual(parsed["phone"], "+91 9876543210")
        self.assertIn("python", parsed["skills"])
        self.assertIn("fastapi", parsed["skills"])
        self.assertIn("docker", parsed["skills"])
        self.assertEqual(len(parsed["roles"]), 2)
        self.assertEqual(parsed["roles"][0]["company"], "CloudGrid Labs")
        self.assertEqual(len(parsed["roles"][0]["highlights"]), 3)
        self.assertEqual(len(parsed["education"]), 1)
        self.assertEqual(len(parsed["projects"]), 1)
        self.assertEqual(len(parsed["certifications"]), 1)

        # ATS scoring on LaTeX directly
        ats_result = calculate_ats_score({}, latex=sample_tex)
        self.assertGreaterEqual(ats_result["overall_score"], 88)
        self.assertEqual(ats_result["rating"], "Exceptional")
        self.assertEqual(ats_result["breakdown"]["contact"]["score"], 15)
        self.assertEqual(ats_result["breakdown"]["experience"]["score"], 30)
        self.assertGreaterEqual(ats_result["breakdown"]["skills"]["score"], 15)
        self.assertGreaterEqual(ats_result["breakdown"]["education_certs"]["score"], 15)

    def test_latex_put_syncs_resume_json(self):
        res = self.client.post("/users", json={"name": "Pooja", "email": "pooja@test.com", "preferred_lang": "en"})
        uid = res.json()["id"]

        rich_tex = r"""\documentclass{article}\begin{document}
\begin{center}{\LARGE \textbf{Pooja Sundaram}}\\[3pt]\href{mailto:pooja@test.com}{pooja@test.com} $|$ +91 9876500000 $|$ Mumbai\end{center}
\section*{PROFESSIONAL SUMMARY}Principal Architect with proven track record in fintech systems.
\section*{TECHNICAL SKILLS}\textbf{Skills:} python, go, kubernetes, aws, redis
\section*{WORK EXPERIENCE}\textbf{Lead Architect} $|$ \textit{PayScale}\begin{itemize}\item Engineered payment router handling 50k TPS.\end{itemize}
\end{document}"""

        put_res = self.client.put(f"/users/{uid}/resume/latex", json={"latex": rich_tex})
        self.assertEqual(put_res.status_code, 200)
        put_data = put_res.json()
        self.assertTrue(put_data["ok"])
        self.assertGreaterEqual(put_data["ats"]["overall_score"], 40)
        self.assertIn("python", put_data["resume"]["skills"])
        self.assertEqual(put_data["resume"]["name"], "Pooja Sundaram")


if __name__ == "__main__":
    unittest.main()

