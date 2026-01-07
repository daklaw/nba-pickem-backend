#!/usr/bin/env python3
"""
Assign games to weeks and update lock times using EST boundaries
"""
from app.core.database import SessionLocal
from app.models.models import Week, Game
from sqlalchemy import and_
from datetime import datetime, timedelta, timezone as dt_timezone


def fix_week_assignments():
    """Assign games to weeks using EST boundaries and update lock times"""
    db = SessionLocal()

    try:
        # EST is UTC-5
        EST = dt_timezone(timedelta(hours=-5))

        weeks = db.query(Week).order_by(Week.number).all()

        print(f"Processing {len(weeks)} weeks using EST boundaries...")
        print()

        total_games_assigned = 0
        weeks_updated = 0

        for week in weeks:
            # Calculate week boundaries in EST
            # Monday 00:00:00 EST to Sunday 23:59:59 EST
            week_start_est = datetime.combine(week.start_date, datetime.min.time()).replace(tzinfo=EST)
            week_end_est = datetime.combine(week.end_date, datetime.max.time()).replace(tzinfo=EST)

            # Convert to UTC for comparison
            week_start_utc = week_start_est.astimezone(dt_timezone.utc)
            week_end_utc = week_end_est.astimezone(dt_timezone.utc)

            # Find all games that fall within this week's EST boundaries
            games_in_week = db.query(Game).filter(
                and_(
                    Game.game_datetime >= week_start_utc,
                    Game.game_datetime <= week_end_utc
                )
            ).all()

            if games_in_week:
                # Assign games to this week
                for game in games_in_week:
                    game.week_id = week.id

                # Find the first game (by game_datetime) to set as lock time
                first_game = min(
                    (g for g in games_in_week if g.game_datetime),
                    key=lambda g: g.game_datetime,
                    default=None
                )

                if first_game:
                    old_lock_time = week.lock_time
                    week.lock_time = first_game.game_datetime
                    weeks_updated += 1

                    print(f"Week {week.number} ({week.start_date} to {week.end_date})")
                    print(f"  Games assigned: {len(games_in_week)}")
                    print(f"  Old lock time: {old_lock_time}")
                    print(f"  New lock time: {week.lock_time}")
                    print()

                    total_games_assigned += len(games_in_week)
                else:
                    print(f"Week {week.number}: {len(games_in_week)} games but no game_datetime")
            else:
                print(f"Week {week.number}: No games found")

        # Commit all changes
        db.commit()

        print("=" * 60)
        print(f"Summary:")
        print(f"  Weeks processed: {len(weeks)}")
        print(f"  Weeks updated: {weeks_updated}")
        print(f"  Total games assigned: {total_games_assigned}")
        print("=" * 60)

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    fix_week_assignments()