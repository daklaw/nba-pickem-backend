from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Dict
from uuid import UUID
from datetime import datetime, timedelta, date
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.models import User, Game, Team
from app.schemas.schemas import NextWeekGameSchedule
from app.services.schedule_service import get_week_schedule_by_teams

router = APIRouter(prefix="/api/teams", tags=["teams"])


def get_next_monday():
    """
    Get the date of the next Monday (not including today if today is Monday).
    """
    today = datetime.now().date()
    # Calculate days until next Monday (0 = Monday, 6 = Sunday)
    days_ahead = (7 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7  # If today is Monday, get next Monday
    next_monday = today + timedelta(days=days_ahead)
    return next_monday


@router.get("/{team_id}/next-week-schedule", response_model=List[NextWeekGameSchedule])
async def get_team_next_week_schedule(
    team_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the schedule for a team for the next week (next Monday to Sunday).
    Returns a list of games with opponent name, date, and whether the team is away.
    """
    # Verify team exists
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    # Calculate next week's date range
    next_monday = get_next_monday()
    next_sunday = next_monday + timedelta(days=6)

    # Get all games where the team is either home or away in the next week
    games = db.query(Game).filter(
        Game.date >= next_monday,
        Game.date <= next_sunday,
        or_(
            Game.home_team_id == team_id,
            Game.away_team_id == team_id
        )
    ).order_by(Game.date).all()

    # Format response
    schedule = []
    for game in games:
        is_away = game.away_team_id == team_id
        opponent_id = game.home_team_id if is_away else game.away_team_id
        opponent = db.query(Team).filter(Team.id == opponent_id).first()

        if opponent:
            schedule.append(
                NextWeekGameSchedule(
                    opponent_name=opponent.name,
                    opponent_abbreviation=opponent.abbreviation,
                    date=game.date,
                    is_away=is_away
                )
            )

    return schedule


@router.get("/week-schedule", response_model=Dict[str, List[NextWeekGameSchedule]])
async def get_week_schedule_all_teams(
    reference_date: date = Query(default=None, description="Date within the week to query (defaults to today)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the entire week's schedule for all teams.

    Returns a dictionary with team names as keys and their schedules as values.
    The week is defined as Monday to Sunday containing the reference date.

    Args:
        reference_date: Any date within the week (defaults to today)

    Returns:
        Dictionary mapping team names to their list of games for the week
    """
    # Use today if no date provided
    if reference_date is None:
        reference_date = datetime.now().date()

    # Get schedule from service
    schedule = get_week_schedule_by_teams(db, reference_date)

    return schedule