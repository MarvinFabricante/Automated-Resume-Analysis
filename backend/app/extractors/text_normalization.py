"""Shared text repair and skill comparison without destroying display spelling."""
import re

SKILL_SEPARATOR = r"[,;|•●◦‣▪►✓\n]+|\s+/\s+"
_HYPHENATED = {
    "problem-solving", "multi-tasking", "self-motivated", "wi-fi",
    "e-commerce", "back-end", "front-end", "full-stack", "point-of-sale",
    "cross-functional", "decision-making", "detail-oriented", "time-management",
    "follow-up", "data-driven", "user-friendly", "real-time", "hands-on",
    "on-site", "in-house", "e-mail", "high-volume", "multi-channel",
    "multi-chat", "client-facing", "customer-facing", "self-starter",
    "fast-paced", "well-organized", "result-oriented", "results-oriented",
    "goal-oriented", "team-oriented", "end-to-end", "peer-to-peer",
    "up-to-date", "day-to-day", "one-on-one", "part-time", "full-time",
    "entry-level", "mid-level", "high-level",
}


def repair_line_hyphenation(text: str) -> str:
    def join(match):
        left, right = match.groups()
        compound = f"{left}-{right}"
        return compound if compound.lower() in _HYPHENATED else left + right
    return re.sub(r"([A-Za-z]+(?:-[A-Za-z]+)*)-[ \t]*\r?\n[ \t]*([A-Za-z]+(?:-[A-Za-z]+)*)", join, text or "")


def normalize_skill_key(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[-–—]", " ", text.casefold())).strip()
