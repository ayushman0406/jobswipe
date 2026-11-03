import json

from .catalog import CATEGORY_SLUGS
from .llm import chat
from .matching import LANG_NAME
from .tools import REGISTRY, TOOL_SPECS

_CATS = ", ".join(sorted(CATEGORY_SLUGS))

SYSTEM = """You are the search-refinement agent of a job-swipe app covering every kind of work in India,
not only software: shops, sales, factories, hospitals, CA firms, hotels, schools, trades.
The user speaks English, Hindi or Kannada (native script, romanized or mixed).
Turn their request into tool calls that edit the current search. Rules:
- Only change what the user asked. Keep everything else.
- Salary is annual INR unless stated. 1 lakh (लाख / ಲಕ್ಷ) = 100000, 1 crore = 10000000, LPA = lakh per annum.
- set_focus takes a short ENGLISH phrase even if the user spoke Hindi/Kannada.
- City names go in English (ಬೆಂಗಳೂರು -> Bengaluru, मुंबई -> Mumbai).
- Job family goes in categories, using only these slugs: __CATS__.
  doctor / MBBS / nurse / pharmacist -> healthcare. CA / auditor / GST / tally / accountant -> finance.
  shop / cashier / store helper / counter -> retail. fitter / CNC / welder / maintenance / mechanic -> mechanical.
  electrician / plumber / carpenter -> trades. sales / MR / business development -> sales.
  manager / plant head / store manager -> management. teacher / tutor -> education.
  chef / hotel / housekeeping -> hospitality. driver / warehouse / delivery -> logistics.
- Education words (MBBS, CA, ITI, 12th, B.Com, Diploma) go in educations, not only keywords.
- Shifts: day, night, rotational, flexible. "night shift" -> shifts ["night"].
- "start over / sab hatao / modalinda" -> reset_search.
After the tool calls, reply with ONE short sentence in __LANG__ confirming what changed.
Current search state: __STATE__"""


def refine_search(state: dict, utterance: str, lang: str = "en", max_steps: int = 4):
    msgs = [
        {"role": "system", "content": SYSTEM.replace("__LANG__", LANG_NAME.get(lang, "English"))
                                              .replace("__CATS__", _CATS)
                                              .replace("__STATE__", json.dumps(state, ensure_ascii=False))},
        {"role": "user", "content": utterance},
    ]
    reply = ""
    for _ in range(max_steps):
        m = chat(msgs, tools=TOOL_SPECS).choices[0].message
        if not m.tool_calls:
            reply = m.content or ""
            break
        msgs.append(m.model_dump(exclude_none=True))
        for tc in m.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
                out = REGISTRY[tc.function.name](state, **args)
            except Exception as e:  # bad args / unknown tool -> let the model self-correct
                out = {"error": str(e)}
            msgs.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(out, ensure_ascii=False)})
    return state, reply