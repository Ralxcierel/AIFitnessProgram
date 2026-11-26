"""Input guardrails that run before any model call (Step C3, DESIGN.md §8).

- Length limits for the profile chat (used by the request model in profile.py).
- A prompt-injection screen based on a pattern list. No model call is made;
  the optional cheap classification call in DESIGN.md §8 is not used.
- A size check for uploaded .ics files (for workstream B's POST /api/calendar).
- A health red-flag finder (for workstream B's plan notes).

A pattern list is a first line of defence, not a complete one: the tests in
backend/tests/test_guardrails.py list what it catches and what it lets through.
Nothing here logs or returns the text it checks.
"""

import re
from collections.abc import Iterable

MAX_MESSAGE_CHARS = 2000
MAX_CHAT_MESSAGES = 40
MAX_ICS_BYTES = 200 * 1024

PROFILE_REFUSAL = (
    "Sorry, I can only help with building your fitness profile. "
    "Please rephrase your message."
)

_FLAGS = re.IGNORECASE | re.MULTILINE

# Invisible characters that could split a phrase ("ig​nore") to dodge the screen.
_ZERO_WIDTH = re.compile("[​‌‍⁠﻿­]")

# Chat-format control tokens. A model never writes these in a normal reply, so
# they are checked in every message, including "assistant" ones. All gaps are
# bounded so long runs of spaces cannot slow the check down.
_CONTROL_TOKEN_PATTERNS = [
    r"<\|/?[ \t]{0,3}(im_start|im_end|endoftext|system|assistant)[ \t]{0,3}\|>",
    r"<[ \t]{0,3}/?[ \t]{0,3}(im_start|im_end|endoftext)[ \t]{0,3}>",
    r"\[/?[ \t]{0,3}(INST|SYS)[ \t]{0,3}\]",
    r"<<[ \t]{0,3}/?[ \t]{0,3}SYS[ \t]{0,3}>>",
]

# Role lines and tags that a normal reply could contain by chance ("### System:"),
# so they are checked in "user" messages only.
_ROLE_LINE_PATTERNS = [
    r"^[ \t]{0,10}#{1,6}[ \t]{0,3}(system|assistant|developer)[ \t]{0,3}:",
    r"^[ \t]{0,10}(system|developer)[ \t]{0,3}(message|prompt)?[ \t]{0,3}:[ \t]{0,3}"
    r"(you\b|the\s(user|assistant)\b|ignore\b|from\snow\b|new\sinstructions\b)",
    r"</?[ \t]{0,3}(system|assistant)[ \t]{0,3}>",
]

# Phrases that try to change or reveal the assistant's instructions. Checked in
# "user" messages only, on text with runs of spaces collapsed to one space.
# Each needs a word like previous / above / your / system, so normal
# corrections ("forget what I said before", "ignore my old rules") pass.
_INSTRUCTION_NOUN = (
    r"(instructions?|prompts?|directives?|directions|guidelines|rules|commands?|messages|context)"
)
_PHRASE_PATTERNS = [
    r"\b(ignore|disregard|forget|override|bypass)\s(?:(?:all|any|of|these|those)\s){0,2}"
    r"(?:the\s)?(?:(?:previous|prior|above|earlier|preceding|original|initial|system)\s"
    r"|your\s(?:(?:previous|prior|original|initial|system)\s)?)" + _INSTRUCTION_NOUN + r"\b",
    r"\b(ignore|disregard|forget)\s(everything|anything|all)\s(above|before|previously"
    r"|you\s(were|have\sbeen|'ve\sbeen)\stold|i\s(told|said\sto)\syou)\b",
    r"\b(ignore|disregard|forget)\swhat\syou('ve|\shave|\swere)\s(been\s)?told\b",
    r"\b(ignore|disregard)\s(the\s)?above\b",
    r"\bsystem[\s_-]?(prompt|message|instructions?)\b",
    r"\b(reveal|show|print|repeat|output|display|leak|summari[sz]e|translate|tell\sme)\b"
    r"[^.?!\n]{0,20}?\b(your|the\s(system|hidden|original|initial))\s"
    r"((system|initial|original|hidden)\s)?(instructions?|prompts?)\b(?!\s(for|on|about|to)\b)",
    r"\b(instructions?|prompts?)\s(you\swere|you've\sbeen|you\shave\sbeen)\sgiven\b",
    r"\brepeat\s(the\s)?(text|words|message)\sabove\b",
    r"\byou\sare\s(now|no\slonger)\s(a|an|in|DAN|free|unrestricted|unfiltered|jailbroken)\b",
    r"\bfrom\snow\son,?\syou\s(are|will\sbe|must\sbe)\s"
    r"(a|an|no|not|DAN|free|unrestricted|unfiltered|jailbroken)\b",
    r"\bpretend\s(you\sare|you're|to\sbe)\s(a|an)\s(\w+\s){0,2}"
    r"(ai|assistant|model|bot|chatbot|system|developer|admin|hacker)\b",
    r"\bact\sas\s(the\s|a\s|an\s)?(system|developer|admin|administrator|unfiltered|jailbroken)\b",
    r"\bnew\s(instructions|rules|system\sprompt)\s?:\s?"
    r"(you|reply|respond|answer|ignore|always|never|act|pretend|from\snow)\b",
    r"\b(developer|admin|god|jailbreak|DAN)\smode\b",
]

_CONTROL_TOKENS = [re.compile(p, _FLAGS) for p in _CONTROL_TOKEN_PATTERNS]
_ROLE_LINES = [re.compile(p, _FLAGS) for p in _ROLE_LINE_PATTERNS]
_PHRASES = [re.compile(p, _FLAGS) for p in _PHRASE_PATTERNS]
_SPACES = re.compile(r"\s+")

# Serious health signals (DESIGN.md §8). Labels, in a fixed order.
_HEALTH_FLAGS = {
    "chest_pain": r"\bchest\s+(pain|pains|tightness|pressure)\b",
    "heart_condition": r"\bheart\s+(condition|disease|problems?|attack|failure|surgery)\b"
    r"|\b(arrhythmia|cardiac|palpitations|hypertension)\b"
    r"|\b(had|have|having|suffered)\s+(a\s+)?(mini[\s-]?)?stroke\b"
    r"|\bhigh\s+blood\s+pressure\b",
    "fainting": r"\b(faint(ed|ing|s)?|pass(ed|ing)?\s+out|black(ed|ing)?\s+out)\b",
    "pregnancy": r"\bpregnan(t|cy)\b",
    "serious_injury": r"\b(fractures?|fractured"
    r"|(broke\s+my|broken)\s+(left\s+|right\s+)?(arm|leg|wrist|ankle|foot|hand|rib|ribs|back"
    r"|neck|toe|finger|collarbone|hip|nose|jaw|elbow|knee|shoulder)"
    r"|torn\s+(acl|mcl|ligament|meniscus|labrum|rotator\s+cuff|muscle|tendon)"
    r"|herniated|slipped\s+disc|concussion|dislocated)\b",
    "eating_disorder": r"\b(anorexi\w*|bulimi\w*|eating\s+disorder|binge\s+eating"
    r"|purging\s+(after|food|meals)|starv(e|ing)\s+myself)\b",
}
_HEALTH = {label: re.compile(p, re.IGNORECASE) for label, p in _HEALTH_FLAGS.items()}


def has_control_tokens(text: str) -> bool:
    """True if the text contains chat-format control tokens such as <|im_start|>."""
    text = _ZERO_WIDTH.sub("", text)
    return any(pattern.search(text) for pattern in _CONTROL_TOKENS)


def looks_like_injection(text: str) -> bool:
    """True if user text tries to change or reveal the assistant's instructions."""
    text = _ZERO_WIDTH.sub("", text)
    if has_control_tokens(text) or any(p.search(text) for p in _ROLE_LINES):
        return True
    flat = _SPACES.sub(" ", text)
    return any(pattern.search(flat) for pattern in _PHRASES)


def chat_is_flagged(messages: Iterable[tuple[str, str]]) -> bool:
    """True if any (role, content) message in the chat should be refused.

    The browser sends the whole history and a client could edit it, so every
    message is checked: user messages for everything, assistant messages for
    control tokens only (a normal reply never contains them, so it cannot
    lock the chat on the next turn).
    """
    for role, content in messages:
        if role == "user" and looks_like_injection(content):
            return True
        if role != "user" and has_control_tokens(content):
            return True
    return False


def ics_is_too_large(size_in_bytes: int) -> bool:
    """True if an uploaded .ics file is over the 200 KB limit."""
    return size_in_bytes > MAX_ICS_BYTES


def health_flags(text: str) -> list[str]:
    """Labels for serious health signals in the text, in a fixed order.

    The plan step uses these to add a "check with a doctor or physical
    therapist" note and to avoid loading the affected area. It never diagnoses.
    Negations ("not pregnant") are not detected; a false alarm only adds a note.
    """
    return [label for label, pattern in _HEALTH.items() if pattern.search(text)]
