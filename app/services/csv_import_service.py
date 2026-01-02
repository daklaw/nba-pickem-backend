"""CSV import service for loading historical pick'em data."""
import csv
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import User, Team, Week, TeamSelection, League, Season


def parse_team_selection(selection_text: str) -> Optional[Dict]:
    """
    Parse a team selection string into components.

    Format examples:
    - "Los Angeles Clippers - 2 (2-1)"
    - "Oklahoma City Thunder (SW) - 8 (4-0)"
    - "Washington Wizards (STM) - 6 (0-4)"
    - "Denver Nuggets" (no points yet)
    - "Indiana Pacers (STM)" (no points yet)

    Returns:
        Dict with keys: team_name, points, is_superweek, is_shoot_the_moon
        or None if empty/invalid
    """
    if not selection_text or selection_text.strip() == "":
        return None

    # Check for modifiers
    is_superweek = "(SW)" in selection_text
    is_shoot_the_moon = "(STM)" in selection_text

    # Remove modifiers to parse the rest
    clean_text = selection_text.replace("(SW)", "").replace("(STM)", "").strip()

    # Pattern: "Team Name - points (W-L)" or just "Team Name"
    # Match pattern with points and record
    match = re.match(r"^(.+?)\s*-\s*(\d+)\s*\(\d+-\d+\)$", clean_text)

    if match:
        team_name = match.group(1).strip()
        points = int(match.group(2))
        return {
            "team_name": team_name,
            "points": points,
            "is_superweek": is_superweek,
            "is_shoot_the_moon": is_shoot_the_moon,
            "completed": True
        }
    else:
        # No points/record yet (future week)
        team_name = clean_text.strip()
        if team_name:
            return {
                "team_name": team_name,
                "points": 0,
                "is_superweek": is_superweek,
                "is_shoot_the_moon": is_shoot_the_moon,
                "completed": False
            }

    return None


def import_csv_data(db: Session, csv_path: str, league_name: str = "Default League") -> Dict:
    """
    Import pick'em data from CSV file.

    Args:
        db: Database session
        csv_path: Path to CSV file
        league_name: Name of the league to use/create

    Returns:
        Dictionary with import statistics
    """
    # Get or create league
    league = db.query(League).filter(League.name == league_name).first()
    if not league:
        league = League(name=league_name)
        db.add(league)
        db.flush()
    db.commit()

    # Read CSV
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)

    if len(rows) < 3:
        raise ValueError("CSV must have at least 3 rows (names, emails, week data)")

    # Parse header rows
    names_row = rows[0][1:]  # Skip first column
    emails_row = rows[1][1:]  # Skip first column

    if len(names_row) != len(emails_row):
        raise ValueError("Names and emails rows must have same length")

    # Statistics
    stats = {
        "users_created": 0,
        "users_updated": 0,
        "weeks_created": 0,
        "selections_created": 0,
        "errors": []
    }

    # Get or create season for 2024-25 (use ending year as integer)
    season = db.query(Season).filter(Season.year == 2025).first()
    if not season:
        season = Season(year=2025, league_id=league.id)
        db.add(season)
        db.flush()
    db.commit()

    # Get all teams for lookup
    teams = db.query(Team).all()
    team_lookup = {team.name: team for team in teams}

    # Add alternate team name mappings for backwards compatibility
    # Both "LA Clippers" and "Los Angeles Clippers" should map to the same team
    for team in teams:
        if team.name == "Los Angeles Clippers":
            team_lookup["LA Clippers"] = team
        elif team.name == "LA Clippers":
            # Legacy support if database still has old name
            team_lookup["Los Angeles Clippers"] = team

    # Create/update users
    user_lookup = {}
    for i, (name, email) in enumerate(zip(names_row, emails_row)):
        if not email or email.strip() == "":
            continue

        email = email.strip()
        existing_user = db.query(User).filter(User.email == email).first()

        if existing_user:
            user_lookup[i] = existing_user
            stats["users_updated"] += 1
        else:
            # Create new user with default password (they should reset it)
            from app.core.security import get_password_hash
            new_user = User(
                name=name,
                email=email,
                hashed_password=get_password_hash("pass1234"),  # Default password
                league_id=league.id,
                total_points=0
            )
            db.add(new_user)
            db.flush()
            user_lookup[i] = new_user
            stats["users_created"] += 1
    db.commit()

    # Process week rows
    week_rows = rows[2:]  # All rows after names and emails
    for row in week_rows:
        if not row or row[0].strip() == "" or row[0] == "Total":
            continue

        week_label = row[0].strip()

        # Extract week number (e.g., "W1" -> 1)
        week_match = re.match(r"W(\d+)", week_label)
        if not week_match:
            continue

        week_number = int(week_match.group(1))

        # Get or create week
        week = db.query(Week).filter(
            Week.number == week_number,
            Week.season_id == season.id
        ).first()
        if not week:
            # Calculate week dates based on 2025-26 NBA season
            # Season started October 22, 2025 (Week 1 = Oct 20-27, 2025)
            season_start = datetime(2025, 10, 20).date()  # Monday before opening day

            # Calculate start date (Monday of this week)
            start_date = season_start + timedelta(weeks=week_number - 1)

            # Calculate end date (Sunday of this week)
            end_date = start_date + timedelta(days=6)

            # Set lock time to Monday 7:00 PM ET (default game time)
            # Store as UTC (ET is UTC-5 in winter, so 7pm ET = midnight UTC)
            lock_time = datetime.combine(
                start_date,
                datetime.min.time()
            ).replace(hour=0, minute=0, second=0, tzinfo=timezone.utc)  # Midnight UTC = 7pm ET previous day

            week = Week(
                number=week_number,
                season_id=season.id,
                start_date=start_date,
                end_date=end_date,
                lock_time=lock_time
            )
            db.add(week)
            db.flush()
            stats["weeks_created"] += 1

        # Process each user's selection for this week
        selections = row[1:]  # Skip week label column
        for user_idx, selection_text in enumerate(selections):
            if user_idx not in user_lookup:
                continue

            user = user_lookup[user_idx]
            selection_data = parse_team_selection(selection_text)

            if not selection_data:
                continue

            # Look up team
            team = team_lookup.get(selection_data["team_name"])
            if not team:
                stats["errors"].append(
                    f"Week {week_number}, {user.email}: Team '{selection_data['team_name']}' not found"
                )
                continue

            # Check if selection already exists
            existing_selection = db.query(TeamSelection).filter(
                TeamSelection.user_id == user.id,
                TeamSelection.team_id == team.id,
                TeamSelection.season_id == season.id,
                TeamSelection.week_id == week.id
            ).first()

            if existing_selection:
                # Update existing selection
                existing_selection.is_superweek = selection_data["is_superweek"]
                existing_selection.is_shoot_the_moon = selection_data["is_shoot_the_moon"]
                existing_selection.total_points = selection_data["points"]
            else:
                # Create new selection
                new_selection = TeamSelection(
                    user_id=user.id,
                    team_id=team.id,
                    season_id=season.id,
                    week_id=week.id,
                    is_superweek=selection_data["is_superweek"],
                    is_shoot_the_moon=selection_data["is_shoot_the_moon"],
                    total_points=selection_data["points"]
                )
                db.add(new_selection)
                stats["selections_created"] += 1
            db.commit()

    # Update user total points based on their team selections
    for user in user_lookup.values():
        total_points = db.query(TeamSelection).filter(
            TeamSelection.user_id == user.id
        ).with_entities(
            func.sum(TeamSelection.total_points)
        ).scalar() or 0

        user.total_points = total_points

    db.commit()

    return stats