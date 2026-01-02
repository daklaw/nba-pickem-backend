from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.models import User, Season
from app.schemas.schemas import NextWeekResponse, NextWeekSelectionResponse, CurrentWeekResponse, CurrentWeekSelectionResponse
from app.services.team_selection_service import get_next_week_for_selection, get_current_week_with_selection

router = APIRouter(prefix="/weeks", tags=["weeks"])


@router.get("/next-week", response_model=NextWeekResponse)
async def get_next_available_week(
    season_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the next available week for making a team selection.
    Returns the week for the next Monday (or current week if today is Monday),
    along with whether the user can use superweek this week.
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

    # Get next week, superweek availability, and existing selection from service
    try:
        next_week, can_use_superweek, selection_dict = get_next_week_for_selection(season_id, current_user, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    # Serialize and return response
    return NextWeekResponse(
        id=next_week.id,
        number=next_week.number,
        start_date=next_week.start_date,
        end_date=next_week.end_date,
        lock_time=next_week.lock_time,
        season_id=next_week.season_id,
        can_use_superweek=can_use_superweek,
        selection=NextWeekSelectionResponse(**selection_dict)
    )


@router.get("/current-week", response_model=CurrentWeekResponse)
async def get_current_week(
    season_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current week information along with the user's selection for this week.
    Returns the week that contains today's date.
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

    # Get current week, selection, and lock status from service
    try:
        current_week, selection_dict, is_locked = get_current_week_with_selection(season_id, current_user, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    # Serialize and return response
    return CurrentWeekResponse(
        id=current_week.id,
        number=current_week.number,
        start_date=current_week.start_date,
        end_date=current_week.end_date,
        lock_time=current_week.lock_time,
        season_id=current_week.season_id,
        is_locked=is_locked,
        selection=CurrentWeekSelectionResponse(**selection_dict)
    )