"""Служебные функции для работы с пользователями."""

from .magic_link import issue_magic_link_and_send_email, redeem_magic_link

__all__ = [
    "issue_magic_link_and_send_email",
    "redeem_magic_link",
]
