from __future__ import annotations

MESSAGES = {
    "en": {
        "matched": "Matched {matches}",
        "no_route": "No category hint matched; read root routing only.",
        "category_shape": "Category must look like 'engineering/backend' or 'projects/engineering/backend'",
        "unknown_placeholder": "Unknown historyTemplate placeholder: {name}",
    },
    "ko": {
        "matched": "\uc77c\uce58\ud55c \ud78c\ud2b8: {matches}",
        "no_route": "\uc77c\uce58\ud558\ub294 \uce74\ud14c\uace0\ub9ac \ud78c\ud2b8 \uc5c6\uc74c. \ub8e8\ud2b8 \ub77c\uc6b0\ud305\ub9cc \uc77d\uc73c\uc138\uc694.",
        "category_shape": "\uce74\ud14c\uace0\ub9ac\ub294 'engineering/backend' \ub610\ub294 'projects/engineering/backend' \ud615\uc2dd\uc774\uc5b4\uc57c \ud569\ub2c8\ub2e4.",
        "unknown_placeholder": "\uc54c \uc218 \uc5c6\ub294 historyTemplate \uc790\ub9ac\ud45c\uc2dc\uc790: {name}",
    },
}


def normalize_language(language: str | None) -> str:
    if not language:
        return "en"
    value = language.strip().casefold()
    if value in {"ko", "kr", "kor", "korean", "\ud55c\uad6d\uc5b4"}:
        return "ko"
    return "en"


def message(language: str | None, key: str, **values: object) -> str:
    lang = normalize_language(language)
    template = MESSAGES.get(lang, MESSAGES["en"]).get(key, MESSAGES["en"][key])
    return template.format(**values)
