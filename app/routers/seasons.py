from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.models import User, Team, TeamSelection, Season
from app.schemas.schemas import TeamResponse

router = APIRouter(prefix="/seasons", tags=["seasons"])


@router.get("/{season_id}/available-teams", response_model=List[TeamResponse])
async def get_available_teams(
    season_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all teams that the user has not selected in the current season.
    These are the teams available for the user to pick.
    """
    # Verify season exists
    season = db.query(Season).filter(Season.id == season_id).first()
    if not season:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Season not found"
        )

    # Get all teams that the user has already selected in this season
    selected_team_ids = db.query(TeamSelection.team_id).filter(
        TeamSelection.user_id == current_user.id,
        TeamSelection.season_id == season_id
    ).all()
    selected_team_ids = [team_id for (team_id,) in selected_team_ids]

    # Get all teams that are NOT in the selected list
    available_teams = db.query(Team).filter(
        Team.id.notin_(selected_team_ids)
    ).all()

    return available_teams