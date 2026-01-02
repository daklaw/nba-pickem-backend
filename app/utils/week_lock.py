from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.models import Week, Game


def is_week_locked(week: Week, db: Session) -> tuple[bool, datetime | None]:
    """
    Check if a week is locked for team selections.
    A week is locked when the first game on Monday starts.

    Args:
        week: The Week object to check
        db: Database session

    Returns:
        tuple: (is_locked: bool, lock_time: datetime | None)
               - is_locked: True if picks are locked, False if still open
               - lock_time: The datetime of the first game (lock time), or None if no games found
    """
    # Find the first game on Monday of this week (by game_datetime)
    first_game = db.query(Game).filter(
        Game.week_id == week.id,
        Game.game_datetime.isnot(None)
    ).order_by(Game.game_datetime.asc()).first()

    if not first_game or not first_game.game_datetime:
        # If no games found or no datetime, use the lock_time from the week if it exists
        if hasattr(week, 'lock_time') and week.lock_time:
            lock_time = week.lock_time.replace(tzinfo=timezone.utc)
            current_time = datetime.now(timezone.utc)
            return current_time >= lock_time, lock_time
        # If no lock_time either, picks are not locked
        return False, None

    # Get the lock time (start of first game)
    lock_time = first_game.game_datetime.replace(tzinfo=timezone.utc)
    current_time = datetime.now(timezone.utc)

    # Check if current time is past the lock time
    is_locked = current_time >= lock_time

    return is_locked, lock_time


def get_week_lock_time(week: Week, db: Session) -> datetime | None:
    """
    Get the lock time for a week (time of first game).

    Args:
        week: The Week object
        db: Database session

    Returns:
        datetime | None: The lock time, or None if no games found
    """
    first_game = db.query(Game).filter(
        Game.week_id == week.id,
        Game.game_datetime.isnot(None)
    ).order_by(Game.game_datetime.asc()).first()

    if not first_game or not first_game.game_datetime:
        # Fallback to lock_time field if it exists
        if hasattr(week, 'lock_time') and week.lock_time:
            return week.lock_time.replace(tzinfo=timezone.utc)
        return None

    return first_game.game_datetime.replace(tzinfo=timezone.utc)