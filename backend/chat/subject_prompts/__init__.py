"""
Subject-specific prompt injection for Lumina.

Each subject module lives in this package and is lazy-imported only when
the student's active course matches. Zero overhead for unrelated subjects.

To add a new subject:
  1. Create chat/subject_prompts/your_subject.py
  2. Implement inject_if_match(course_name: str, extra: str) -> str
  3. Add one entry to _REGISTRY below

engine.py never needs to change.
"""

# Registry: (keywords_tuple, module_path)
# Keywords are checked as substrings against the lowercased course name.
_REGISTRY = [
    (("economics", "econ", "micro", "macro"),  "chat.subject_prompts.economics"),
    (("math", "maths", "calculus", "algebra", "statistics", "ibdp math", "ap calc"),
                                                "chat.subject_prompts.mathematics"),
    (("physics", "phys"),                       "chat.subject_prompts.physics"),
    (("chemistry", "chem"),                     "chat.subject_prompts.chemistry"),
    (("biology", "bio"),                        "chat.subject_prompts.biology"),
]


def inject_subject_prompt(course_name: str | None, extra: str) -> str:
    """
    Called once per chat request from engine._build_system_prompt.
    Lazy-imports only the modules whose keywords match the course name.
    """
    if not course_name:
        return extra

    name_lower = course_name.lower()

    for keywords, module_path in _REGISTRY:
        if any(k in name_lower for k in keywords):
            try:
                import importlib
                mod = importlib.import_module(module_path)
                extra = mod.inject_if_match(course_name, extra)
            except ModuleNotFoundError:
                pass  # stub not yet implemented — silently skip
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    "Subject prompt injection failed (%s): %s", module_path, e
                )

    return extra
