"""Shared text repair and skill comparison without destroying display spelling."""
import re

SKILL_SEPARATOR = r"[,;|•▪►✓\n]+|\s+/\s+"
_HYPHENATED = {
    "problem-solving", "multi-tasking", "self-motivated", "wi-fi",
    "e-commerce", "back-end", "front-end", "point-of-sale",
}


def repair_line_hyphenation(text: str) -> str:
    def join(match):
        left, right = match.groups()
        compound = f"{left}-{right}"
        return compound if compound.lower() in _HYPHENATED else left + right
    return re.sub(r"([A-Za-z]+)-[ \t]*\r?\n[ \t]*([A-Za-z]+)", join, text or "")


def normalize_skill_key(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[-–—]", " ", text.casefold())).strip()
