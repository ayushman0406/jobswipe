"""Runs when a provider accepts a seeker's like (mutual match). Extend with more agentic steps."""
import secrets

from .config import settings


def meet_link(match_id: int) -> str:
    return f"{settings.jitsi_base}/jobswipe-{match_id}-{secrets.token_urlsafe(6)}"


def _step(kind: str, title: str, detail: str, match_id: int, link: bool = False) -> dict:
    step = {"kind": kind, "title": title, "detail": detail}
    if link:
        step["url"] = meet_link(match_id)
    return step


def plan_next_steps(job, match_id: int) -> list[dict]:
    cat = (getattr(job, "category", None) or "").lower()
    title = (job.title or "").lower()
    steps = [_step("intro_call", "Intro call", "Short call with the hiring team.", match_id, link=True)]
    if cat == "healthcare":
        steps += [
            _step("credential_check", "Registration and documents",
                  "Share degree, council registration (NMC or state) and a photo ID.", match_id),
            _step("clinical_discussion", "Clinical discussion",
                  "Walk through a recent case and how you would handle the ward or OPD.", match_id, link=True),
        ]
    elif cat == "finance":
        steps.append(_step(
            "case_round", "Tax or audit case",
            "A short GST, TDS or statutory-audit scenario. Bring a notebook, not a slide deck.", match_id))
    elif cat == "sales":
        steps += [
            _step("pitch", "Role-play pitch", "Fifteen minutes selling the product to a sceptical buyer.", match_id),
            _step("field_shadow", "Field shadow", "Half a day on the beat with the area manager.", match_id),
        ]
    elif cat == "retail":
        steps.append(_step("trial_shift", "Paid trial shift", "Half a day on the shop floor at the counter.", match_id))
    elif cat == "mechanical":
        steps.append(_step(
            "practical", "Shop-floor practical",
            "Read a drawing and do a short fitting, welding or maintenance task.", match_id))
    elif cat == "trades":
        steps.append(_step("site_trial", "Site trial", "A supervised job at site so the supervisor can see the work.", match_id))
    elif cat == "management":
        steps.append(_step("case", "Operations case", "How you would run this team and this shift for a week.", match_id))
    elif cat == "education":
        steps.append(_step("demo_class", "Demo class", "Teach a ten-minute sample to the panel.", match_id, link=True))
    elif cat == "hospitality":
        steps.append(_step("service_trial", "Service trial", "One meal period on the floor or in the kitchen.", match_id))
    elif cat == "legal":
        steps.append(_step("brief", "Brief review", "Mark up a short contract or notice and talk through the issues.", match_id))
    elif cat == "logistics":
        steps.append(_step("yard_walk", "Yard walkthrough", "Meet the supervisor and see the shift, route or dock.", match_id))
    elif cat == "agriculture":
        steps.append(_step("field_visit", "Field visit", "Walk the farm or the route with the supervisor.", match_id))
    elif cat == "technology" or any(w in title for w in ("engineer", "developer", "scientist", "sde", "devops")):
        if settings.coding_base_url:
            steps.append({
                "kind": "coding_round", "title": "Live coding round",
                "detail": "Shared editor session.",
                "url": f"{settings.coding_base_url}/{secrets.token_urlsafe(6)}",
            })
    else:
        steps.append(_step("hiring_manager", "Hiring manager chat", "Role, team, shift and pay.", match_id, link=True))
    return steps


def on_mutual_match(session, match, job):
    steps = plan_next_steps(job, match.id)
    match.status = "mutual"
    match.next_steps = steps
    match.meet_url = next((s.get("url") for s in steps if s.get("url")), None)
    session.add(match)
    session.commit()
    return steps