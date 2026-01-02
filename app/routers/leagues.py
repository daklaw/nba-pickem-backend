from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, cast, Type
from uuid import UUID
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.models import User, League, Season, TeamSelection, Week, Team
from app.schemas.schemas import LeagueStandingsResponse, UserStandingResponse, WeeklySelectionsResponse, UserWeeklySelectionResponse, TeamSelectionResponse

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

    # Format standings with rank
    standings = []
    for rank, (user_id, name, email, season_points) in enumerate(standings_query, start=1):
        standings.append(
            UserStandingResponse(
                name=name,
                rank=rank,
                user_id=user_id,
                email=email,
                season_points=int(season_points)
            )
        )

    return LeagueStandingsResponse(
        league_id=league_id,
        league_name=league.name,
        season_id=season_id,
        season_year=season.year,
        standings=standings
    )


@router.get("/seasons/{season_id}/my-selections", response_model=List[TeamSelectionResponse])
async def get_my_selections(
    season_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all team selections made by the current user in a specific season.
    Ordered by week number (ascending).
    """
    selections = db.query(TeamSelection).join(Week).filter(
        TeamSelection.user_id == current_user.id,
        TeamSelection.season_id == season_id
    ).order_by(Week.number.asc()).all()

    # Return selections directly - Pydantic will handle serialization
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
                    email=user.email,
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
                    email=user.email,
                    has_selected=False,
                    team_id=None,
                    team_name=None,
                    team_logo=None,
                    is_superweek=False,
                    is_shoot_the_moon=False,
                    total_points=0
                )
            )

    # Sort by email for consistency
    user_selections.sort(key=lambda x: x.email)

    return WeeklySelectionsResponse(
        league_id=league_id,
        league_name=league.name,
        season_id=season_id,
        season_year=season.year,
        week_id=week_id,
        week_number=week.number,
        selections=user_selections
    )