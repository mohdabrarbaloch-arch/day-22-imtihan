"""Exam code generation — short, readable, unguessable-enough codes."""

import secrets
import string

ALPHABET = string.ascii_uppercase + string.digits
# Avoid confusing characters
ALPHABET = ALPHABET.replace("O", "").replace("0", "").replace("I", "").replace("1", "")


def generate_exam_code(length: int = 8) -> str:
    """Generate an 8-char code like 'K7M2P9QX'."""
    return "".join(secrets.choice(ALPHABET) for _ in range(length))
