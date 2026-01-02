"""Game service for handling game updates and score calculations."""
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.models import Game, TeamSelection, User, Week, Season


def get_week_for_date(db: Session, game_date: datetime.date) -> Optional[Week]:
    """
    Determine which week a game belongs to based on its date.

    Args:
        db: Database session
        game_date: Date of the game

    Returns:
        Week object or None if week doesn't exist
    """
    # Query weeks and find the one that contains this date
    week = db.query(Week).filter(
        and_(
            Week.start_date <= game_date,
            Week.end_date >= game_date
        )
    ).first()

    return week


def calculate_team_week_record(db: Session, team_id: str, week: Week) -> Dict:
    """
    Calculate a team's win-loss record for a specific week.

    Args:
        db: Database session
        team_id: UUID of the team
        week: Week object

    Returns:
        Dictionary with wins, losses, and games_pending
    """
    # Get all games for this team in this week
    games = db.query(Game).filter(
        and_(
            Game.date >= week.start_date,
            Game.date <= week.end_date,
            or_(
                Game.home_team_id == team_id,
                Game.away_team_id == team_id
            )
        )
    ).all()

    wins = 0
    losses = 0
    games_pending = 0

    for game in games:
        if game.winner_id is None:
            # Game not completed yet
            games_pending += 1
        elif str(game.winner_id) == str(team_id):
            wins += 1
        else:
            losses += 1

    return {
        "wins": wins,
        "losses": losses,
        "games_pending": games_pending,
        "total_games": len(games),
        "all_games_complete": games_pending == 0
    }


def calculate_selection_points(db: Session, selection: TeamSelection) -> int:
    """
    Calculate points for a team selection based on the rules.

    Rules:
    - Regular pick: 1 point per win
    - Superweek: 2 points per win (wins are doubled)
    - Shoot the Moon: If team loses ALL games, points = 2x number of losses. If they win ANY game, 0 points.

    Args:
        db: Database session
        selection: TeamSelection object

    Returns:
        Total points for this selection
    """
    week = db.query(Week).filter(Week.id == selection.week_id).first()
    if not week:
        return 0

    # Get team's record for the week
    record = calculate_team_week_record(db, selection.team_id, week)

    # If games are still pending, we can't calculate final points yet
    if not record["all_games_complete"]:
        # Return partial points for completed games (useful for live scoring)
        # But for "Shoot the Moon", we need all games complete
        if selection.is_shoot_the_moon:
            return 0  # Can't determine STM until all games are done

    # Shoot the Moon logic
    if selection.is_shoot_the_moon:
        # Must lose ALL games to get points
        if record["wins"] == 0 and record["losses"] > 0:
            # Award 2x points for number of losses
            return record["losses"] * 2
        else:
            # Won at least one game or no games played = 0 points
            return 0

    # Regular and Superweek logic
    wins = record["wins"]

    if selection.is_superweek:
        return wins * 2
    else:
        return wins


def update_game_and_recalculate_points(
    db: Session,
    game_id: str,
    home_score: int,
    away_score: int,
) -> dict:
    """
    Update a game's final score and recalculate points for all affected team selections.

    This will recalculate points for ALL selections in the week where this game occurred,
    since one game result could affect Shoot the Moon calculations.

    Args:
        db: Database session
        game_id: NBA game ID
        home_score: Final home team score
        away_score: Final away team score

    Returns:
        Dictionary with update results including affected users count
    """
    # Find the game
    game = db.query(Game).filter(Game.nba_game_id == game_id).first()
    if not game:
        raise ValueError(f"Game with ID {game_id} not found")

    # Determine winner
    if home_score > away_score:
        winner_id = game.home_team_id
    elif away_score > home_score:
        winner_id = game.away_team_id
    else:
        winner_id = None  # Tie (rare in NBA)

    # Update game
    game.home_team_score = home_score
    game.away_team_score = away_score
    game.winner_id = winner_id

    db.flush()

    # Get the week this game belongs to
    if not game.date:
        db.commit()
        return {
            "game_id": game_id,
            "winner_id": str(winner_id) if winner_id else None,
            "affected_users": 0,
            "points_awarded": 0,
            "error": "Game has no date"
        }

    week = get_week_for_date(db, game.date)
    if not week:
        db.commit()
        return {
            "game_id": game_id,
            "winner_id": str(winner_id) if winner_id else None,
            "affected_users": 0,
            "points_awarded": 0,
            "error": "Could not determine week"
        }

    # Recalculate points for ALL selections in this week
    # (because this game could affect Shoot the Moon calculations)
    team_selections = db.query(TeamSelection).filter(
        TeamSelection.week_id == week.id
    ).all()

    affected_users = set()
    total_points_awarded = 0

    for selection in team_selections:
        # Recalculate points for this selection
        new_points = calculate_selection_points(db, selection)
        selection.total_points = new_points
        total_points_awarded += new_points
        affected_users.add(str(selection.user_id))

    # Recalculate all user total points
    for user_id in affected_users:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            # Sum all points from this user's selections
            total = db.query(TeamSelection).filter(
                TeamSelection.user_id == user.id
            ).all()
            user.total_points = sum(s.total_points or 0 for s in total)

    db.commit()

    return {
        "game_id": game_id,
        "winner_id": str(winner_id) if winner_id else None,
        "week_number": week.number,
        "affected_users": len(affected_users),
        "points_awarded": total_points_awarded
    }


def recalculate_all_points(db: Session) -> dict:
    """
    Recalculate all user and team selection points from scratch based on completed games.

    This is the main backfill function that should be run to update all scores.

    Args:
        db: Database session

    Returns:
        Dictionary with recalculation statistics
    """
    # Reset all user and team selection points
    db.query(User).update({"total_points": 0})
    db.query(TeamSelection).update({"total_points": 0})
    db.flush()

    # Get all team selections (we'll recalculate points for each)
    all_selections = db.query(TeamSelection).all()

    selections_processed = 0
    total_points_awarded = 0
    users_affected = set()

    for selection in all_selections:
        # Calculate points for this selection
        points = calculate_selection_points(db, selection)
        selection.total_points = points
        total_points_awarded += points
        users_affected.add(str(selection.user_id))
        selections_processed += 1

    # Recalculate all user total points
    all_users = db.query(User).all()
    for user in all_users:
        # Sum all points from this user's selections
        user_selections = db.query(TeamSelection).filter(
            TeamSelection.user_id == user.id
        ).all()
        user.total_points = sum(s.total_points or 0 for s in user_selections)

    db.commit()

    return {
        "selections_processed": selections_processed,
        "users_affected": len(users_affected),
        "total_points_awarded": total_points_awarded
    }


def retabulate_season(db: Session, season_id: str) -> Dict:
    """
    Retabulate all team selections for a specific season.

    This function:
    1. Gets all team selections for the season
    2. Recalculates points for each selection based on game results
    3. Updates user total points
    4. Returns detailed statistics about changes

    Args:
        db: Database session
        season_id: UUID of the season to retabulate

    Returns:
        Dictionary with detailed statistics
    """
    # Verify season exists
    season = db.query(Season).filter(Season.id == season_id).first()
    if not season:
        raise ValueError(f"Season with ID {season_id} not found")

    # Get all team selections for this season
    selections = db.query(TeamSelection).filter(
        TeamSelection.season_id == season_id
    ).all()

    if not selections:
        return {
            "season_id": str(season_id),
            "season_year": season.year,
            "selections_found": 0,
            "selections_updated": 0,
            "users_affected": 0,
            "total_points_awarded": 0,
            "changes": []
        }

    # Track changes
    changes = []
    selections_updated = 0
    users_affected = set()
    total_points_awarded = 0

    # Recalculate each selection
    for selection in selections:
        old_points = selection.total_points or 0
        new_points = calculate_selection_points(db, selection)

        if old_points != new_points:
            # Get week info for better reporting
            week = db.query(Week).filter(Week.id == selection.week_id).first()
            week_number = week.number if week else None

            # Get team record for detailed info
            record = calculate_team_week_record(db, selection.team_id, week) if week else {}

            changes.append({
                "user_id": str(selection.user_id),
                "team_id": str(selection.team_id),
                "week_number": week_number,
                "old_points": old_points,
                "new_points": new_points,
                "difference": new_points - old_points,
                "is_superweek": selection.is_superweek,
                "is_shoot_the_moon": selection.is_shoot_the_moon,
                "record": f"{record.get('wins', 0)}-{record.get('losses', 0)}" if record else "Unknown"
            })
            selections_updated += 1

        # Update the selection
        selection.total_points = new_points
        total_points_awarded += new_points
        users_affected.add(str(selection.user_id))

    # Recalculate user total points
    for user_id in users_affected:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user_selections = db.query(TeamSelection).filter(
                TeamSelection.user_id == user.id
            ).all()
            user.total_points = sum(s.total_points or 0 for s in user_selections)

    db.commit()

    return {
        "season_id": str(season_id),
        "season_year": season.year,
        "selections_found": len(selections),
        "selections_updated": selections_updated,
        "users_affected": len(users_affected),
        "total_points_awarded": total_points_awarded,
        "changes": changes
    }