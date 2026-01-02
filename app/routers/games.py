from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
from uuid import UUID
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.models import User, Game, Team, Week
from app.schemas.schemas import TeamGamesResponse

router = APIRouter(prefix="/games", tags=["games"])


@router.get("/", response_model=List[TeamGamesResponse])
async def get_team_games(
    team_id: UUID,
    week_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all games for a specific team in a specific week.
    Returns games where the team is either home or away.
    """
    # Verify team exists
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    # Verify week exists
    week = db.query(Week).filter(Week.id == week_id).first()
    if not week:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Week not found"
        )

    # Get all games where the team is either home or away in this week
    games = db.query(Game).filter(
        Game.week_id == week_id,
        or_(
            Game.home_team_id == team_id,
            Game.away_team_id == team_id
        )
    ).order_by(Game.game_datetime).all()

    # Format response
    games_response = []
    for game in games:
        home_team = db.query(Team).filter(Team.id == game.home_team_id).first()
        away_team = db.query(Team).filter(Team.id == game.away_team_id).first()
        winner_team = None
        if game.winner_id:
            winner_team = db.query(Team).filter(Team.id == game.winner_id).first()

        games_response.append(
            TeamGamesResponse(
                id=game.id,
                week_id=game.week_id,
                date=game.date,
                game_datetime=game.game_datetime,
                home_team_id=game.home_team_id,
                home_team_name=home_team.name if home_team else None,
                home_team_score=game.home_team_score,
                away_team_id=game.away_team_id,
                away_team_name=away_team.name if away_team else None,
                away_team_score=game.away_team_score,
                winner_id=game.winner_id,
                winner_name=winner_team.name if winner_team else None,
                nba_game_id=game.nba_game_id
            )
        )

    return games_response