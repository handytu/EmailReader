from __future__ import annotations

import re
from html import unescape

from app.models.message import MailMessage

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")

# Phrases commonly used around one-time login / verification codes.
_CODE_HINT = re.compile(
    r"(?i)\b(?:verification|confirmation|verify|login|sign[ -]?in|security|authentication|auth|one[ -]?time|single[ -]?use|otp|passcode|access)\b.{0,28}\bcode\b"
    r"|\bcode\b.{0,28}\b(?:verification|verify|login|sign[ -]?in|security|authentication|auth|one[ -]?time|otp|passcode|access)\b"
    r"|\b(?:otp|passcode)\b"
)

# Prefer the common 6-digit OTP shape, then allow 4-8 digits when a code hint exists.
_SIX_DIGIT = re.compile(r"(?<![\w.])(\d{6})(?![\w.]|[-/]\d)")
_URL = re.compile(r"https?://\S+|\b[\w.+-]+@[\w.-]+", re.IGNORECASE)

# Keep context windows fairly small to avoid grabbing order numbers farther away.
_NEAR_HINT_FORWARD = re.compile(
    r"(?i)\b(?:code|otp|passcode)\b\s*(?:(?:is|is as follows|for you is)\s*)?[:：=–-]?\s*(?<![\w.])(\d{4,8})(?![\w.]|[-/]\d)"
)
_NEAR_HINT_REVERSE = re.compile(
    r"(?i)(?<![\w.])(\d{4,8})(?![\w.]|[-/]\d)\s*(?:is\s+)?(?:your\s+)?(?:verification|confirmation|login|security|one[ -]?time)\s+code\b"
)


def _plain_html(value: str) -> str:
    if not value:
        return ""
    value = re.sub(r"(?is)<(style|script)[^>]*>.*?</\1>", " ", value)
    return _SPACE_RE.sub(" ", unescape(_TAG_RE.sub(" ", value))).strip()


def extract_verification_code(message: MailMessage) -> str | None:
    """Return the most likely one-time/login code from a message.

    This is intentionally conservative: it first searches close to verification
    labels in the subject, then in text and HTML. A bare six-digit fallback must
    be unique and accompanied by verification language.
    """
    subject = message.subject or ""
    # Search each source separately: a truncated text part must not hide the HTML.
    sources = [subject, message.body_text or "", _plain_html(message.body_html), message.preview or ""]
    for text in sources:
        text = _URL.sub(" ", text)
        for pattern in (_NEAR_HINT_FORWARD, _NEAR_HINT_REVERSE):
            match = pattern.search(text)
            if match:
                return match.group(1)

    # A separate code heading is acceptable only when the six-digit token is unique.
    # Never fall back to incidental four-digit years, IPs or account identifiers.
    for text in sources:
        if _CODE_HINT.search(subject) or _CODE_HINT.search(text[:700]):
            candidates = set(_SIX_DIGIT.findall(_URL.sub(" ", text)))
            if len(candidates) == 1:
                return candidates.pop()

    return None
