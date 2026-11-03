"""Job families the seeker can filter, and the phrase we embed when they pick one."""

CATEGORIES = [
    {"slug": "technology", "label": "Technology", "blurb": "Software, data and IT",
     "focus": "software engineer developer data IT"},
    {"slug": "sales", "label": "Sales", "blurb": "Field, inside, pharma, insurance",
     "focus": "sales executive field sales medical representative business development"},
    {"slug": "management", "label": "Managers", "blurb": "Store, plant, project, people",
     "focus": "manager team lead store plant operations people management"},
    {"slug": "retail", "label": "Shop workers", "blurb": "Floor, cashier, inventory",
     "focus": "shop cashier retail store associate billing floor staff"},
    {"slug": "mechanical", "label": "Mechanical", "blurb": "Fitting, CNC, maintenance, auto",
     "focus": "mechanical fitter CNC maintenance technician automobile workshop"},
    {"slug": "finance", "label": "CA & finance", "blurb": "CA, audit, tax, accounts",
     "focus": "chartered accountant CA audit GST tax tally accounts"},
    {"slug": "healthcare", "label": "Doctors & care", "blurb": "Doctors, nurses, pharmacy, labs",
     "focus": "doctor physician nurse pharmacist hospital clinical patient care"},
    {"slug": "hospitality", "label": "Hospitality", "blurb": "Hotels, kitchen, front office",
     "focus": "hotel chef front office housekeeping restaurant service"},
    {"slug": "education", "label": "Education", "blurb": "Teachers, trainers, tutors",
     "focus": "teacher tutor trainer school classroom education"},
    {"slug": "logistics", "label": "Logistics", "blurb": "Warehouse, delivery, fleet",
     "focus": "warehouse delivery driver logistics dispatch transport"},
    {"slug": "hr", "label": "HR", "blurb": "Hiring, payroll, HRBP",
     "focus": "human resources recruiter HR payroll employee relations"},
    {"slug": "marketing", "label": "Marketing", "blurb": "Brand, performance, content",
     "focus": "marketing brand performance ads content social media"},
    {"slug": "support", "label": "Customer support", "blurb": "Voice, chat, BPO",
     "focus": "customer support call center BPO voice process chat support"},
    {"slug": "legal", "label": "Legal", "blurb": "Counsel, compliance, drafting",
     "focus": "lawyer advocate legal counsel compliance contracts"},
    {"slug": "trades", "label": "Skilled trades", "blurb": "Electrician, plumber, carpenter",
     "focus": "electrician plumber carpenter technician site trade"},
    {"slug": "agriculture", "label": "Agriculture", "blurb": "Farm, agri inputs, dairy",
     "focus": "agriculture farm agronomist dairy crops farmer"},
    {"slug": "creative", "label": "Creative", "blurb": "Design, video, photo",
     "focus": "designer graphic video editor photographer creative"},
    {"slug": "operations", "label": "Operations", "blurb": "Admin, process, facilities",
     "focus": "operations admin process executive facilities back office"},
]

CATEGORY_SLUGS = {c["slug"] for c in CATEGORIES}
SHIFTS = ["day", "night", "rotational", "flexible"]
EMPLOYMENT_TYPES = ["full-time", "part-time", "contract", "internship", "articleship"]


def focus_for(slugs: list[str]) -> str:
    by = {c["slug"]: c["focus"] for c in CATEGORIES}
    return " ".join(by[s] for s in slugs if s in by)