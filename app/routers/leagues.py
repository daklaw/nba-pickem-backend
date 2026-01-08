from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, cast, Type
from uuid import UUID
from datetime import date
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.models import User, League, Season, TeamSelection, Week, Team
from app.schemas.schemas import LeagueStandingsResponse, UserStandingResponse, WeeklySelectionsResponse, UserWeeklySelectionResponse, TeamSelectionResponse
from app.utils.week_lock import is_week_locked

router = APIRouter(prefix="/leagues", tags=["leagues"])


@router.get("/seasons/{season_id}/standings", response_model=LeagueStandingsResponse)
async def get_league_standings(
    season_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the standings for a specific season.
    Returns all users in the league ranked by their total points.
    """
    # Verify season exists
    season = db.query(Season).filter(Season.id == season_id).first()
    if not season:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Season not found"
        )

    # Get the league from the season
    league = db.query(League).filter(League.id == season.league_id).first()
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found"
        )

    league_id = season.league_id

    # Get all users in the league with their total points for this season
    standings_query = db.query(
        User.id,
        User.name,
        User.email,
        func.coalesce(func.sum(TeamSelection.total_points), 0).label("season_points")
    ).filter(
        User.league_id == league_id
    ).outerjoin(
        TeamSelection,
        (TeamSelection.user_id == User.id) & (TeamSelection.season_id == season_id)
    ).group_by(
        User.id,
        User.name,
        User.email
    ).order_by(
        func.coalesce(func.sum(TeamSelection.total_points), 0).desc(),
        User.email  # Tie-breaker: alphabetical by email
    ).all()

    # Get current week based on today's date
    today = date.today()
    current_week = db.query(Week).filter(
        Week.season_id == season_id,
        Week.start_date <= today,
        Week.end_date >= today
    ).first()

    # Get all current week selections if we have a current week and it's locked
    current_week_selections = {}
    if current_week:
        is_locked, _ = is_week_locked(current_week, db)
        if is_locked:
            # Get all selections for current week
            selections = db.query(TeamSelection).filter(
                TeamSelection.season_id == season_id,
                TeamSelection.week_id == current_week.id
            ).all()

            for selection in selections:
                team = db.query(Team).filter(Team.id == selection.team_id).first()
                current_week_selections[selection.user_id] = {
                    "team_name": team.name if team else None,
                    "is_superweek": selection.is_superweek,
                    "is_shoot_the_moon": selection.is_shoot_the_moon,
                    "total_points": selection.total_points
                }

    # Format standings with rank and current week selection
    standings = []
    for rank, (user_id, name, email, season_points) in enumerate(standings_query, start=1):
        current_week_data = current_week_selections.get(user_id, {})
        standings.append(
            UserStandingResponse(
                name=name,
                rank=rank,
                user_id=user_id,
                email=email,
                season_points=int(season_points),
                current_week_team_name=current_week_data.get("team_name"),
                current_week_is_superweek=current_week_data.get("is_superweek", False),
                current_week_is_shoot_the_moon=current_week_data.get("is_shoot_the_moon", False),
                current_week_points=current_week_data.get("total_points", 0)
            )
        )

    return LeagueStandingsResponse(
        league_id=league_id,
        league_name=league.name,
        season_id=season_id,
        season_year=season.year,
        standings=standings
    )


@router.get("/seasons/{season_id}/users/{user_id}", response_model=List[TeamSelectionResponse])
async def get_user_selections(
    season_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all team selections made by a specific user in a specific season.
    Ordered by week number (ascending).

    Users can only view selections for users in their own league.
    """
    # Verify season exists
    season = db.query(Season).filter(Season.id == season_id).first()
    if not season:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Season not found"
        )

    # Verify target user exists
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify both users are in the same league
    if current_user.league_id != target_user.league_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view selections for users in other leagues"
        )

    # Verify the target user's league matches the season's league
    if target_user.league_id != season.league_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not in the league for this season"
        )

    # Get selections for the target user
    selections = db.query(TeamSelection).join(Week).filter(
        TeamSelection.user_id == user_id,
        TeamSelection.season_id == season_id
    ).order_by(Week.number.asc()).all()

    return selections


@router.get("/seasons/{season_id}/weekly-selections/{week_id}", response_model=WeeklySelectionsResponse)
async def get_weekly_selections(
    season_id: UUID,
    week_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all team selections for a specific week in a league.
    Returns all users in the league, including those who haven't made a selection yet.
    """
    # Verify season exists
    season = db.query(Season).filter(Season.id == season_id).first()
    if not season:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Season not found"
        )

    # Get the league from the season
    league_id = season.league_id
    league = db.query(League).filter(League.id == league_id).first()
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found"
        )

    # Verify week exists
    week = db.query(Week).filter(Week.id == week_id).first()
    if not week:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Week not found"
        )

    # Get all users in the league
    users = db.query(User).filter(User.league_id == league_id).all()

    # Get all selections for this week and season
    selections = db.query(TeamSelection).filter(
        TeamSelection.season_id == season_id,
        TeamSelection.week_id == week_id,
        TeamSelection.user_id.in_([user.id for user in users])
    ).all()

    # Create a mapping of user_id to selection
    selections_by_user = {selection.user_id: selection for selection in selections}

    # Build response with all users
    user_selections = []
    for user in users:
        selection = selections_by_user.get(user.id)

        if selection:
            # User has made a selection
            team = db.query(Team).filter(Team.id == selection.team_id).first()
            user_selections.append(
                UserWeeklySelectionResponse(
                    user_id=user.id,
                    name=user.name,
                    has_selected=True,
                    team_id=selection.team_id,
                    team_name=team.name if team else None,
                    team_logo=team.logo if team else None,
                    is_superweek=selection.is_superweek,
                    is_shoot_the_moon=selection.is_shoot_the_moon,
                    total_points=selection.total_points
                )
            )
        else:
            # User has not made a selection
            user_selections.append(
                UserWeeklySelectionResponse(
                    user_id=user.id,
                    name=user.name,
                    has_selected=False,
                    team_id=None,
                    team_name=None,
                    team_logo=None,
                    is_superweek=False,
                    is_shoot_the_moon=False,
                    total_points=0
                )
            )

    # Sort by name for consistency
    user_selections.sort(key=lambda x: x.name)

    return WeeklySelectionsResponse(
        league_id=league_id,
        league_name=league.name,
        season_id=season_id,
        season_year=season.year,
        week_id=week_id,
        week_number=week.number,
        selections=user_selections
    )