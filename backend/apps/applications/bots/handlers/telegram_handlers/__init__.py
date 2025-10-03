"""Backward-compatible import shim for telegram handlers.

The Telegram bot code lives in :mod:`applications.bots.telegram`. This
package is kept to avoid ImportError in legacy scripts.
"""

from applications.bots.telegram.handlers import *  # noqa: F401,F403
