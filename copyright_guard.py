"""
copyright_guard.py – Copyright integrity verification for Disk Dumper.

© 2026 Murthy Sai Krishna. All rights reserved.
Unauthorized modification or removal of this notice is prohibited.

This module provides tamper-resistant copyright protection. The application
will refuse to start if the copyright information is modified or removed.
"""

import hmac
import hashlib
import sys

# ─── Copyright Information (DO NOT MODIFY) ────────────────────────────────────
# Any modification to these values will cause the application to refuse to start.

AUTHOR = "Murthy Sai Krishna"
COPYRIGHT_YEAR = "2026"
PROJECT_NAME = "Disk Dumper"
COPYRIGHT_NOTICE = f"© {COPYRIGHT_YEAR} {AUTHOR}. All rights reserved."

# ─── Integrity Verification ──────────────────────────────────────────────────
# HMAC-based tamper detection using a derived key. This ensures that if
# AUTHOR, COPYRIGHT_YEAR, or COPYRIGHT_NOTICE are modified, the application
# will detect the change and refuse to start.

_INTEGRITY_KEY = b"DiskDumper_Copyright_Integrity_2026_MSK"
_EXPECTED_SIGNATURE = "e3a7c1d9f5b2a4e6c8d0f1a3b5c7d9e1"  # placeholder


def _compute_signature() -> str:
    """Compute HMAC signature from the current copyright data."""
    payload = f"{AUTHOR}|{COPYRIGHT_YEAR}|{PROJECT_NAME}|{COPYRIGHT_NOTICE}".encode("utf-8")
    return hmac.new(_INTEGRITY_KEY, payload, hashlib.sha256).hexdigest()


# Compute the real expected signature at module definition time from the
# ORIGINAL, unmodified values. We store this as a constant derived from
# the exact original strings so we can verify later.
_ORIGINAL_AUTHOR = "Murthy Sai Krishna"
_ORIGINAL_YEAR = "2026"
_ORIGINAL_PROJECT = "Disk Dumper"
_ORIGINAL_NOTICE = f"© {_ORIGINAL_YEAR} {_ORIGINAL_AUTHOR}. All rights reserved."
_VALID_SIGNATURE = hmac.new(
    _INTEGRITY_KEY,
    f"{_ORIGINAL_AUTHOR}|{_ORIGINAL_YEAR}|{_ORIGINAL_PROJECT}|{_ORIGINAL_NOTICE}".encode("utf-8"),
    hashlib.sha256,
).hexdigest()


def verify_copyright() -> bool:
    """
    Verify that the copyright information has not been tampered with.

    Returns True if the copyright is intact. If tampered, prints an error
    and returns False. The calling application should exit immediately.
    """
    current_sig = _compute_signature()
    if not hmac.compare_digest(current_sig, _VALID_SIGNATURE):
        return False
    return True


def get_copyright_text() -> str:
    """Return the full copyright notice string."""
    return COPYRIGHT_NOTICE


def get_author() -> str:
    """Return the author name."""
    return AUTHOR


def enforce_copyright(is_gui: bool = False):
    """
    Verify copyright and exit the application if tampered.

    Args:
        is_gui: If True, show a GUI error dialog instead of console output.
    """
    if not verify_copyright():
        msg = (
            "FATAL ERROR: Copyright integrity check failed.\n\n"
            f"This software is the intellectual property of {_ORIGINAL_AUTHOR}.\n"
            "Unauthorized modification of copyright information is prohibited.\n\n"
            "The application cannot start."
        )
        if is_gui:
            try:
                import tkinter as tk
                from tkinter import messagebox
                _root = tk.Tk()
                _root.withdraw()
                messagebox.showerror("Copyright Violation", msg)
                _root.destroy()
            except Exception:
                print(f"\n  ❌ {msg}")
        else:
            print(f"\n  ❌ {msg}")
        sys.exit(1)
