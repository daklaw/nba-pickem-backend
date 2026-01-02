"""Team selection business logic service."""
from datetime import date, timedelta
from sqlalchemy.orm import Session
from uuid import UUID
from app.models.models import User, Week, TeamSelection, Team


def get_next_week_for_selection(season_id: UUID, user: User, db: Session) -> tuple[Week, bool, dict]:
    """
    Get the next week for making a team selection.
    Returns the week for the next Monday (or current week if today is Monday),
    along with whether the user can use superweek and their existing selection if any.

    Args:
        season_id: UUID of the season
        user: Current user
        db: Database session

    Returns:
        tuple: (Week object, can_use_superweek: bool, selection_dict)
        selection_dict contains: team_id, team_name, is_superweek, is_shoot_the_moon

    Raises:
        ValueError: If no weeks found for the season
    """
    # Get all weeks for this season, ordered by week number
    weeks = db.query(Week).filter(
        Week.season_id == season_id
    ).order_by(Week.number).all()

    if not weeks:
        raise ValueError("No weeks found for this season")

    # Find the week for the next Monday (or current week if today is Monday)
    today = date.today()

    # Calculate next Monday (0 = Monday, 6 = Sunday)
    days_until_monday = (7 - today.weekday()) % 7  # Days until next Monday
    if days_until_monday == 0:  # Today is Monday
        next_monday = today
    else:
        next_monday = today + timedelta(days=days_until_monday)

    # Find the week that starts on next_monday
    next_week = None
    for week in weeks:
        if week.start_date == next_monday:
            next_week = week
            break

    # If no exact match, find the closest upcoming week
    if not next_week:
        for week in weeks:
            if week.start_date >= next_monday:
                next_week = week
                break

    # If still no match, return the last week
    if not next_week:
        next_week = weeks[-1]

    # Check if user has already used superweek this season
    has_used_superweek = db.query(TeamSelection).filter(
        TeamSelection.user_id == user.id,
        TeamSelection.season_id == season_id,
        TeamSelection.is_superweek == True
    ).first() is not None

    can_use_superweek = not has_used_superweek

    # Check if user has already made a selection for this week
    selection = db.query(TeamSelection).filter(
        TeamSelection.user_id == user.id,
        TeamSelection.week_id == next_week.id,
        TeamSelection.season_id == season_id
    ).first()

    selection_dict = {
        "team_id": None,
        "team_name": None,
        "is_superweek": False,
        "is_shoot_the_moon": False
    }

    if selection:
        # Get team name
        team = db.query(Team).filter(Team.id == selection.team_id).first()
        selection_dict = {
            "team_id": selection.team_id,
            "team_name": team.name if team else None,
            "is_superweek": selection.is_superweek,
            "is_shoot_the_moon": selection.is_shoot_the_moon
        }

    return next_week, can_use_superweek, selection_dict


def has_user_used_superweek(user_id: UUID, season_id: UUID, db: Session) -> bool:
    """
    Check if a user has already used their superweek in a season.

    Args:
        user_id: UUID of the user
        season_id: UUID of the season
        db: Database session

    Returns:
        bool: True if user has used superweek, False otherwise
    """
    return db.query(TeamSelection).filter(
        TeamSelection.user_id == user_id,
        TeamSelection.season_id == season_id,
        TeamSelection.is_superweek == True
    ).first() is not None


def get_current_week_with_selection(season_id: UUID, user: User, db: Session) -> tuple[Week, dict, bool]:
    """
    Get the current week and the user's selection for that week.
    Returns the week that contains today's date.

    Args:
        season_id: UUID of the season
        user: Current user
        db: Database session

    Returns:
        tuple: (Week object, selection_dict, is_locked: bool)
        selection_dict contains: team_id, team_name, is_superweek, is_shoot_the_moon

    Raises:
        ValueError: If no weeks found for the season or no current week
    """
    from app.utils.week_lock import is_week_locked

    # Get all weeks for this season
    weeks = db.query(Week).filter(
        Week.season_id == season_id
    ).order_by(Week.number).all()

    if not weeks:
        raise ValueError("No weeks found for this season")

    # Find the week that contains today's date
    today = date.today()
    current_week = None

    for week in weeks:
        if week.start_date <= today <= week.end_date:
            current_week = week
            break

    # If no week contains today, use the closest week
    if not current_week:
        # Find the closest week (either upcoming or most recent)
        upcoming_weeks = [w for w in weeks if w.start_date > today]
        if upcoming_weeks:
            current_week = upcoming_weeks[0]  # Next upcoming week
        else:
            current_week = weeks[-1]  # Most recent week (season ended)

    # Check if week is locked
    locked, _ = is_week_locked(current_week, db)

    # Get user's selection for this week
    selection = db.query(TeamSelection).filter(
        TeamSelection.user_id == user.id,
        TeamSelection.week_id == current_week.id,
        TeamSelection.season_id == season_id
    ).first()

    selection_dict = {
        "team_id": None,
        "team_name": None,
        "is_superweek": False,
        "is_shoot_the_moon": False
    }

    if selection:
        # Get team name
        team = db.query(Team).filter(Team.id == selection.team_id).first()
        selection_dict = {
            "team_id": selection.team_id,
            "team_name": team.name if team else None,
            "is_superweek": selection.is_superweek,
            "is_shoot_the_moon": selection.is_shoot_the_moon
        }

    return current_week, selection_dict, locked