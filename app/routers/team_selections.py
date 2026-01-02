from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.models import User, Team, TeamSelection, Season, Week
from app.schemas.schemas import TeamSelectionCreate, TeamSelectionResponse
from app.utils.week_lock import is_week_locked
from app.services.team_selection_service import has_user_used_superweek
from datetime import datetime, timezone

router = APIRouter(prefix="/team-selections", tags=["team selections"])


@router.post("/", response_model=TeamSelectionResponse, status_code=status.HTTP_201_CREATED)
async def create_team_selection(
    selection_data: TeamSelectionCreate,
    season_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Make a team selection for the current week.
    Users can only make one selection per week and can only pick each team once per season.
    """
    # Verify season exists
    season = db.query(Season).filter(Season.id == season_id).first()
    if not season:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Season not found"
        )

    # Verify user belongs to the season's league
    if current_user.league_id != season.league_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to this season's league"
        )

    # Verify team exists
    team = db.query(Team).filter(Team.id == selection_data.team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    # Verify week exists
    week = db.query(Week).filter(Week.id == selection_data.week_id).first()
    if not week:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Week not found"
        )

    # Check if the week is locked (picks close when first game starts)
    locked, lock_time = is_week_locked(week, db)
    if locked:
        lock_time_str = lock_time.strftime('%Y-%m-%d %H:%M:%S UTC') if lock_time else 'unknown'
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Picks are locked for Week {week.number}. The deadline was {lock_time_str} (first game of the week)."
        )

    # Check if user has already made a selection for this week
    existing_week_selection = db.query(TeamSelection).filter(
        TeamSelection.user_id == current_user.id,
        TeamSelection.week_id == selection_data.week_id
    ).first()

    if existing_week_selection:
        # Update existing selection instead of creating a new one

        # Check if user is trying to change to a different team
        if existing_week_selection.team_id != selection_data.team_id:
            # Check if user has already selected the new team in this season
            existing_team_selection = db.query(TeamSelection).filter(
                TeamSelection.user_id == current_user.id,
                TeamSelection.team_id == selection_data.team_id,
                TeamSelection.season_id == season_id
            ).first()

            if existing_team_selection:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"You have already selected {team.name} this season. Each team can only be selected once per season."
                )

        # Check if user is trying to enable superweek but has already used it
        if selection_data.is_superweek and not existing_week_selection.is_superweek:
            if has_user_used_superweek(current_user.id, season_id, db):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You have already used your superweek this season. Each user can only use superweek once per season."
                )

        # Update the existing selection
        existing_week_selection.team_id = selection_data.team_id
        existing_week_selection.is_superweek = selection_data.is_superweek
        existing_week_selection.is_shoot_the_moon = selection_data.is_shoot_the_moon

        db.commit()
        db.refresh(existing_week_selection)

        return existing_week_selection

    # No existing selection - check if user has already selected this team in this season
    existing_selection = db.query(TeamSelection).filter(
        TeamSelection.user_id == current_user.id,
        TeamSelection.team_id == selection_data.team_id,
        TeamSelection.season_id == season_id
    ).first()

    if existing_selection:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You have already selected {team.name} this season. Each team can only be selected once per season."
        )

    # Check if user is trying to use superweek but has already used it this season
    if selection_data.is_superweek:
        if has_user_used_superweek(current_user.id, season_id, db):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already used your superweek this season. Each user can only use superweek once per season."
            )

    # Create the team selection
    new_selection = TeamSelection(
        user_id=current_user.id,
        team_id=selection_data.team_id,
        season_id=season_id,
        week_id=selection_data.week_id,
        is_superweek=selection_data.is_superweek,
        is_shoot_the_moon=selection_data.is_shoot_the_moon,
        total_points=0
    )

    db.add(new_selection)
    db.commit()
    db.refresh(new_selection)

    return new_selection