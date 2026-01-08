#!/usr/bin/env python3
"""
Recalculate wins and losses for all team selections
"""
from app.core.database import SessionLocal
from app.models.models import TeamSelection, Game
from sqlalchemy import and_, or_

def recalculate_wins_losses():
    """Recalculate wins and losses for all team selections based on game results"""
    db = SessionLocal()

    try:
        # Get all team selections
        selections = db.query(TeamSelection).all()

        print(f"Found {len(selections)} team selections to process")
        print()

        updated_count = 0

        for selection in selections:
            # Get all games for this team in this week
            games = db.query(Game).filter(
                Game.week_id == selection.week_id,
                or_(
                    Game.home_team_id == selection.team_id,
                    Game.away_team_id == selection.team_id
                )
            ).all()

            wins = 0
            losses = 0

            for game in games:
                # Only count games that have been completed (have a winner)
                if game.winner_id is not None:
                    if game.winner_id == selection.team_id:
                        wins += 1
                    else:
                        losses += 1

            # Update the selection if values changed
            if selection.wins != wins or selection.losses != losses:
                old_wins = selection.wins
                old_losses = selection.losses
                selection.wins = wins
                selection.losses = losses
                updated_count += 1

                print(f"Updated selection {selection.id}:")
                print(f"  User: {selection.user.name}")
                print(f"  Team: {selection.team.name}")
                print(f"  Week: {selection.week.number}")
                print(f"  Wins: {old_wins} -> {wins}")
                print(f"  Losses: {old_losses} -> {losses}")
                print()

        # Commit all changes
        db.commit()

        print("=" * 60)
        print(f"Recalculation complete!")
        print(f"Updated {updated_count} out of {len(selections)} selections")
        print("=" * 60)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    recalculate_wins_losses()