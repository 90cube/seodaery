"""생일 도메인 로직. 외부 프레임워크 의존 금지."""

from datetime import date

from server.data.birthday_store import (
    delete_birthday,
    get_birthday,
    get_event_db,
    get_upcoming_birthdays,
    init_birthday_tables,
    list_birthdays,
    upsert_birthday,
)


def _conn():
    conn = get_event_db()
    init_birthday_tables(conn)
    return conn


def register_birthday(user_id: str, user_name: str, birthday: str) -> None:
    """생일을 등록한다. birthday 형식: MM-DD."""
    conn = _conn()
    try:
        upsert_birthday(conn, user_id, user_name, birthday)
    finally:
        conn.close()


def get_user_birthday(user_id: str) -> dict | None:
    conn = _conn()
    try:
        return get_birthday(conn, user_id)
    finally:
        conn.close()


def get_all_birthdays() -> list[dict]:
    conn = _conn()
    try:
        return list_birthdays(conn)
    finally:
        conn.close()


def get_next_birthdays() -> list[dict]:
    """오늘 기준으로 다가오는 생일 목록을 반환한다."""
    today_mmdd = date.today().strftime("%m-%d")
    conn = _conn()
    try:
        return get_upcoming_birthdays(conn, today_mmdd)
    finally:
        conn.close()


def remove_birthday(user_id: str) -> bool:
    conn = _conn()
    try:
        return delete_birthday(conn, user_id)
    finally:
        conn.close()
