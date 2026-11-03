"""Tools the refinement agent can call. All mutate `state` = {"filters": {...}, "focus": str}."""
from .catalog import CATEGORY_SLUGS, EMPLOYMENT_TYPES, SHIFTS

ALLOWED = {
    "remote", "locations", "min_salary", "employment_types", "min_experience_years",
    "max_experience_years", "include_keywords", "exclude_keywords",
    "categories", "shifts", "industries", "educations", "languages",
}


def set_filters(state, remove=None, **patch):
    f = state.setdefault("filters", {})
    for k in remove or []:
        f.pop(k, None)
    for k, v in patch.items():
        if k not in ALLOWED:
            return {"error": f"unknown filter {k}"}
        if k == "categories" and v:
            bad = [c for c in v if str(c).lower() not in CATEGORY_SLUGS]
            if bad:
                return {"error": f"unknown categories {bad}. use {sorted(CATEGORY_SLUGS)}"}
            v = [str(c).lower() for c in v]
        if k == "shifts" and v:
            bad = [c for c in v if str(c).lower() not in SHIFTS]
            if bad:
                return {"error": f"unknown shifts {bad}. use {SHIFTS}"}
            v = [str(c).lower() for c in v]
        if k == "employment_types" and v:
            v = [str(c).lower().replace(" ", "-") for c in v]
        if v is None or v == [] or v == "":
            f.pop(k, None)
        else:
            f[k] = v
    return {"filters": f}


def set_focus(state, query: str):
    state["focus"] = query.strip()
    return {"focus": state["focus"]}


def reset_search(state):
    state["filters"], state["focus"] = {}, ""
    return {"ok": True}


REGISTRY = {"set_filters": set_filters, "set_focus": set_focus, "reset_search": reset_search}

_CATS = ", ".join(sorted(CATEGORY_SLUGS))
_TYPES = ", ".join(EMPLOYMENT_TYPES)
_SHIFTS = ", ".join(SHIFTS)

TOOL_SPECS = [
    {"type": "function", "function": {
        "name": "set_filters",
        "description": "Add/change/remove hard filters on the job feed. Pass null/[] to clear one, or list names in `remove`.",
        "parameters": {"type": "object", "properties": {
            "remote": {"type": ["boolean", "null"]},
            "locations": {"type": "array", "items": {"type": "string"}, "description": "city names in English"},
            "min_salary": {"type": ["integer", "null"], "description": "annual, absolute number (15 LPA = 1500000)"},
            "employment_types": {"type": "array", "items": {"type": "string"},
                                 "description": _TYPES},
            "min_experience_years": {"type": ["number", "null"]},
            "max_experience_years": {"type": ["number", "null"]},
            "categories": {"type": "array", "items": {"type": "string"},
                           "description": f"job family slugs: {_CATS}"},
            "shifts": {"type": "array", "items": {"type": "string"}, "description": _SHIFTS},
            "industries": {"type": "array", "items": {"type": "string"},
                           "description": "substring of the job industry, e.g. pharma, fmcg, hospital, CA firm"},
            "educations": {"type": "array", "items": {"type": "string"},
                           "description": "substring of required education, e.g. MBBS, CA, ITI, 12th, B.Com, Diploma"},
            "languages": {"type": "array", "items": {"type": "string"},
                          "description": "spoken language the job lists: english, hindi, kannada, tamil, telugu, marathi"},
            "include_keywords": {"type": "array", "items": {"type": "string"}},
            "exclude_keywords": {"type": "array", "items": {"type": "string"}},
            "remove": {"type": "array", "items": {"type": "string"}},
        }}}},
    {"type": "function", "function": {
        "name": "set_focus",
        "description": "Set the soft semantic focus (role/skills/domain wanted) as a short ENGLISH phrase. Empty string clears it.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "reset_search", "description": "Clear all filters and focus.",
        "parameters": {"type": "object", "properties": {}}}},
]