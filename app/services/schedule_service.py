"""Schedule service for handling team schedule queries."""
from datetime import date, timedelta
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.models import Team, Game
from app.schemas.schemas import NextWeekGameSchedule


def get_week_dates(reference_date: date) -> tuple[date, date]:
    """
    Get the Monday and Sunday for the week containing the reference date.

    Args:
        reference_date: Any date within the week

    Returns:
        Tuple of (monday, sunday) dates
    """
    # Calculate Monday of the week (0 = Monday, 6 = Sunday)
    days_since_monday = reference_date.weekday()
    monday = reference_date - timedelta(days=days_since_monday)
    sunday = monday + timedelta(days=6)

    return monday, sunday


def get_week_schedule_by_teams(db: Session, reference_date: date) -> Dict[str, List[NextWeekGameSchedule]]:
    """
    Get the entire week's schedule grouped by team name.

    Args:
        db: Database session
        reference_date: Any date within the week to query

    Returns:
        Dictionary with team names as keys and list of NextWeekGameSchedule as values
    """
    # Get the week boundaries
    monday, sunday = get_week_dates(reference_date)

    # Get all teams
    teams = db.query(Team).all()

    # Initialize result dictionary with all teams
    schedule_by_team: Dict[str, List[NextWeekGameSchedule]] = {}

    for team in teams:
        # Get all games for this team during the week
        games = db.query(Game).filter(
            Game.date >= monday,
            Game.date <= sunday,
            or_(
                Game.home_team_id == team.id,
                Game.away_team_id == team.id
            )
        ).order_by(Game.date).all()

        # Build schedule for this team
        team_schedule = []
        for game in games:
            is_away = game.away_team_id == team.id
            opponent_id = game.home_team_id if is_away else game.away_team_id
            opponent = db.query(Team).filter(Team.id == opponent_id).first()

            if opponent:
                team_schedule.append(
                    NextWeekGameSchedule(
                        opponent_name=opponent.name,
                        opponent_abbreviation=opponent.abbreviation,
                        date=game.date,
                        is_away=is_away
                    )
                )

        schedule_by_team[team.name] = team_schedule

    return schedule_by_team