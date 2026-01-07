#!/usr/bin/env python3
"""
Management CLI for NBA Pick'em API
Similar to Django's manage.py

Usage:
    python manage.py [COMMAND] [OPTIONS]

Examples:
    python manage.py create-superuser
    python manage.py seed-teams
    python manage.py ingest-games
    python manage.py import-csv data/nba-pickem.csv
    python manage.py update-game-score 0022500123 110 105
    python manage.py recalculate-points
    python manage.py db-shell
"""
import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy.orm import Session
from getpass import getpass
import sys
import requests
from datetime import datetime
from typing import Optional, Annotated

app = typer.Typer(
    name="NBA Pick'em Management",
    help="Management commands for NBA Pick'em API",
    add_completion=False,
)
console = Console()


# Database commands
@app.command()
def create_superuser():
    """Create a superuser account (admin user)."""
    from app.core.database import SessionLocal
    from app.models.models import User, League
    from app.core.security import get_password_hash

    console.print("[bold blue]Create Superuser[/bold blue]")
    console.print()

    db = SessionLocal()
    try:
        # Get or create default league
        league = db.query(League).filter(League.name == "Default League").first()
        if not league:
            league = League(name="Default League")
            db.add(league)
            db.commit()
            db.refresh(league)
            console.print(f"[green]✓[/green] Created default league")

        email = typer.prompt("Email address")

        # Check if user exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            console.print(f"[red]✗[/red] User with email {email} already exists")
            sys.exit(1)

        password = getpass("Password: ")
        password_confirm = getpass("Password (again): ")

        if password != password_confirm:
            console.print("[red]✗[/red] Passwords do not match")
            sys.exit(1)

        if len(password) < 8:
            console.print("[red]✗[/red] Password must be at least 8 characters")
            sys.exit(1)

        # Create user
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            league_id=league.id,
            total_points=0
        )
        db.add(user)
        db.commit()

        console.print(f"[green]✓[/green] Superuser created successfully!")
        console.print(f"  Email: {email}")
        console.print(f"  League: {league.name}")

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


@app.command()
def seed_teams():
    """Seed the database with NBA teams."""
    from app.core.database import SessionLocal
    from app.models.models import Team

    # NBA teams with abbreviations
    nba_teams = [
        ("ATL", "Atlanta Hawks"),
        ("BOS", "Boston Celtics"),
        ("CHA", "Charlotte Hornets"),
        ("CHI", "Chicago Bulls"),
        ("CLE", "Cleveland Cavaliers"),
        ("DAL", "Dallas Mavericks"),
        ("DEN", "Denver Nuggets"),
        ("DET", "Detroit Pistons"),
        ("GSW", "Golden State Warriors"),
        ("HOU", "Houston Rockets"),
        ("IND", "Indiana Pacers"),
        ("LAC", "Los Angeles Clippers"),
        ("LAL", "Los Angeles Lakers"),
        ("MEM", "Memphis Grizzlies"),
        ("MIA", "Miami Heat"),
        ("MIL", "Milwaukee Bucks"),
        ("MIN", "Minnesota Timberwolves"),
        ("NOH", "New Orleans Pelicans"),
        ("NYK", "New York Knicks"),
        ("BKN", "Brooklyn Nets"),
        ("OKC", "Oklahoma City Thunder"),
        ("ORL", "Orlando Magic"),
        ("PHI", "Philadelphia 76ers"),
        ("PHO", "Phoenix Suns"),
        ("POR", "Portland Trail Blazers"),
        ("SAC", "Sacramento Kings"),
        ("SAS", "San Antonio Spurs"),
        ("TOR", "Toronto Raptors"),
        ("UTH", "Utah Jazz"),
        ("WAS", "Washington Wizards"),
    ]

    console.print("[bold blue]Seeding NBA Teams[/bold blue]")
    console.print()

    db = SessionLocal()
    try:
        created_count = 0
        skipped_count = 0
        updated_count = 0

        for abbreviation, team_name in nba_teams:
            existing_team = db.query(Team).filter(Team.name == team_name).first()
            if existing_team:
                # Update abbreviation if it exists but doesn't have one
                if not existing_team.abbreviation:
                    existing_team.abbreviation = abbreviation
                    console.print(f"[blue]↻[/blue] {team_name} ({abbreviation}) - updated abbreviation")
                    updated_count += 1
                else:
                    console.print(f"[yellow]⊘[/yellow] {team_name} ({abbreviation}) - already exists")
                    skipped_count += 1
            else:
                team = Team(name=team_name, abbreviation=abbreviation)
                db.add(team)
                console.print(f"[green]✓[/green] {team_name} ({abbreviation})")
                created_count += 1

        db.commit()

        console.print()
        console.print(f"[bold green]Summary:[/bold green]")
        console.print(f"  Created: {created_count}")
        console.print(f"  Updated: {updated_count}")
        console.print(f"  Skipped: {skipped_count}")
        console.print(f"  Total: {created_count + updated_count + skipped_count}")

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


@app.command()
def list_users():
    """List all users in the database."""
    from app.core.database import SessionLocal
    from app.models.models import User

    db = SessionLocal()
    try:
        users = db.query(User).all()

        if not users:
            console.print("[yellow]No users found[/yellow]")
            return

        table = Table(title="Users")
        table.add_column("Email", style="cyan")
        table.add_column("Total Points", justify="right", style="magenta")
        table.add_column("League ID", style="green")

        for user in users:
            table.add_row(
                user.email,
                str(user.total_points),
                str(user.league_id)
            )

        console.print(table)
        console.print(f"\n[bold]Total users:[/bold] {len(users)}")

    finally:
        db.close()


@app.command()
def db_shell():
    """Open an interactive database shell."""
    from app.core.database import SessionLocal, engine
    from app.models.models import Base, User, League, Team, Season, Week, TeamSelection, Game

    console.print("[bold blue]Database Shell[/bold blue]")
    console.print("Available objects: db, engine, User, League, Team, Season, Week, TeamSelection, Game")
    console.print("Example: db.query(User).all()")
    console.print()

    db = SessionLocal()

    try:
        import IPython
        IPython.embed(colors="neutral")
    except ImportError:
        import code
        code.interact(local=locals())
    finally:
        db.close()


@app.command()
def show_config():
    """Show current configuration."""
    from app.core.config import settings

    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    # Don't show sensitive values
    table.add_row("APP_NAME", settings.APP_NAME)
    table.add_row("DEBUG", str(settings.DEBUG))
    table.add_row("DATABASE_URL", settings.DATABASE_URL.split("@")[1] if "@" in settings.DATABASE_URL else "***")
    table.add_row("ALGORITHM", settings.ALGORITHM)
    table.add_row("ACCESS_TOKEN_EXPIRE_MINUTES", str(settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    console.print(table)


# NBA team name mapping from API to database
NBA_TEAM_MAPPING = {
    "76ers": "Philadelphia 76ers",
    "Bucks": "Milwaukee Bucks",
    "Bulls": "Chicago Bulls",
    "Cavaliers": "Cleveland Cavaliers",
    "Celtics": "Boston Celtics",
    "Clippers": "Los Angeles Clippers",
    "Grizzlies": "Memphis Grizzlies",
    "Hawks": "Atlanta Hawks",
    "Heat": "Miami Heat",
    "Hornets": "Charlotte Hornets",
    "Jazz": "Utah Jazz",
    "Kings": "Sacramento Kings",
    "Knicks": "New York Knicks",
    "Lakers": "Los Angeles Lakers",
    "Magic": "Orlando Magic",
    "Mavericks": "Dallas Mavericks",
    "Nets": "Brooklyn Nets",
    "Nuggets": "Denver Nuggets",
    "Pacers": "Indiana Pacers",
    "Pelicans": "New Orleans Pelicans",
    "Pistons": "Detroit Pistons",
    "Raptors": "Toronto Raptors",
    "Rockets": "Houston Rockets",
    "Spurs": "San Antonio Spurs",
    "Suns": "Phoenix Suns",
    "Thunder": "Oklahoma City Thunder",
    "Timberwolves": "Minnesota Timberwolves",
    "Trail Blazers": "Portland Trail Blazers",
    "Warriors": "Golden State Warriors",
    "Wizards": "Washington Wizards",
}


@app.command()
def ingest_games():
    """Ingest NBA games from the NBA API schedule endpoint (includes future games)."""
    url = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"
    regular_season_only = True  # Include all games (preseason, regular season, playoffs)
    dry_run = False
    from app.core.database import SessionLocal
    from app.models.models import Game, Team

    console.print(f"[bold blue]Ingesting NBA Games[/bold blue]")
    console.print(f"Source: {url}")
    console.print(f"Regular season only: {regular_season_only}")
    console.print(f"Dry run: {dry_run}")
    console.print()

    try:
        # Fetch the JSON data
        console.print("[yellow]Fetching data from NBA API...[/yellow]")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        console.print(f"[green]✓[/green] Data fetched successfully")

        # Extract season info
        season_year = data.get("leagueSchedule", {}).get("seasonYear", "Unknown")
        console.print(f"Season: {season_year}")
        console.print()

        db = SessionLocal()
        try:
            # Load all teams into memory for quick lookup
            teams = db.query(Team).all()
            team_lookup = {team.name: team for team in teams}

            created_count = 0
            updated_count = 0
            skipped_count = 0
            error_count = 0
            errors = []  # Collect error messages
            game_labels_seen = set()  # Track unique game labels for debugging

            # Process each game date
            game_dates = data.get("leagueSchedule", {}).get("gameDates", [])
            total_games = sum(len(date_obj.get("games", [])) for date_obj in game_dates)

            console.print(f"[bold]Processing {total_games} games...[/bold]")
            console.print()

            for date_obj in game_dates:
                games = date_obj.get("games", [])
                # Get the local game date from the API (not UTC date)
                local_game_date_str = date_obj.get("gameDate")  # Format: "MM/DD/YYYY"

                for game_data in games:
                    try:
                        # Skip non-regular season games if flag is set
                        game_label = game_data.get("gameLabel", "")
                        game_labels_seen.add(game_label)  # Track what labels we see

                        # Regular season includes: empty string, Emirates NBA Cup, and NBA Mexico City Game
                        regular_season_labels = {"", "Emirates NBA Cup", "NBA Mexico City Game"}
                        if regular_season_only and game_label not in regular_season_labels:
                            skipped_count += 1
                            continue

                        # Extract game info
                        nba_game_id = game_data.get("gameId")
                        home_team_name_short = game_data.get("homeTeam", {}).get("teamName", "")
                        away_team_name_short = game_data.get("awayTeam", {}).get("teamName", "")

                        # Map to full team names
                        home_team_name = NBA_TEAM_MAPPING.get(home_team_name_short)
                        away_team_name = NBA_TEAM_MAPPING.get(away_team_name_short)

                        if not home_team_name or not away_team_name:
                            errors.append(
                                f"Game {nba_game_id}: Unknown team mapping "
                                f"({home_team_name_short} vs {away_team_name_short})"
                            )
                            error_count += 1
                            continue

                        # Look up teams in database
                        home_team = team_lookup.get(home_team_name)
                        away_team = team_lookup.get(away_team_name)

                        if not home_team or not away_team:
                            missing_teams = []
                            if not home_team:
                                missing_teams.append(f"'{home_team_name}' (home)")
                            if not away_team:
                                missing_teams.append(f"'{away_team_name}' (away)")

                            errors.append(
                                f"Game {nba_game_id}: Team(s) not found in database: "
                                f"{', '.join(missing_teams)}"
                            )
                            error_count += 1
                            continue

                        # Parse datetime (use UTC time) and date (use local date from API)
                        game_datetime_str = game_data.get("gameDateTimeUTC")
                        game_datetime = None
                        game_date = None
                        if game_datetime_str:
                            game_datetime = datetime.fromisoformat(game_datetime_str.replace("Z", "+00:00"))
                        # Use local game date from API, not UTC date
                        if local_game_date_str:
                            # Parse date (format can be "MM/DD/YYYY" or "MM/DD/YYYY HH:MM:SS")
                            game_date = datetime.strptime(local_game_date_str.split()[0], "%m/%d/%Y").date()

                        # Extract scores
                        home_score = game_data.get("homeTeam", {}).get("score")
                        away_score = game_data.get("awayTeam", {}).get("score")

                        # Determine winner
                        winner_id = None
                        if home_score is not None and away_score is not None:
                            if home_score > away_score:
                                winner_id = home_team.id
                            elif away_score > home_score:
                                winner_id = away_team.id

                        # Check if game already exists
                        existing_game = db.query(Game).filter(Game.nba_game_id == nba_game_id).first()

                        if dry_run:
                            if existing_game:
                                console.print(
                                    f"[yellow]⟳[/yellow] Would update: {away_team_name} @ {home_team_name} "
                                    f"({game_date}) - {game_label}"
                                )
                                updated_count += 1
                            else:
                                console.print(
                                    f"[green]+[/green] Would create: {away_team_name} @ {home_team_name} "
                                    f"({game_date}) - {game_label}"
                                )
                                created_count += 1
                        else:
                            if existing_game:
                                # Update existing game
                                existing_game.game_datetime = game_datetime
                                existing_game.date = game_date
                                existing_game.game_label = game_label
                                existing_game.home_team_score = home_score
                                existing_game.away_team_score = away_score
                                existing_game.season_year = season_year
                                existing_game.winner_id = winner_id
                                updated_count += 1
                            else:
                                # Create new game
                                new_game = Game(
                                    home_team_id=home_team.id,
                                    away_team_id=away_team.id,
                                    nba_game_id=nba_game_id,
                                    winner_id=winner_id,
                                    date=game_date,
                                    game_datetime=game_datetime,
                                    home_team_score=home_score,
                                    away_team_score=away_score,
                                    season_year=season_year,
                                )
                                db.add(new_game)
                                created_count += 1

                    except Exception as e:
                        errors.append(f"Error processing game: {str(e)}")
                        error_count += 1
                        continue

            if not dry_run:
                db.commit()
                console.print()
                console.print("[green]✓[/green] Changes committed to database")

                # Assign games to weeks and update lock times (using EST boundaries)
                console.print()
                console.print("[yellow]Assigning games to weeks using EST boundaries...[/yellow]")
                from app.models.models import Week
                from sqlalchemy import and_
                from datetime import timedelta, timezone as dt_timezone

                # EST is UTC-5
                EST = dt_timezone(timedelta(hours=-5))

                weeks = db.query(Week).all()
                weeks_updated = 0
                games_assigned = 0

                for week in weeks:
                    # Calculate week boundaries in EST
                    # Monday 00:00:00 EST to Sunday 23:59:59 EST
                    week_start_est = datetime.combine(week.start_date, datetime.min.time()).replace(tzinfo=EST)
                    week_end_est = datetime.combine(week.end_date, datetime.max.time()).replace(tzinfo=EST)

                    # Convert to UTC for comparison
                    week_start_utc = week_start_est.astimezone(dt_timezone.utc)
                    week_end_utc = week_end_est.astimezone(dt_timezone.utc)

                    # Find games that fall within this week's EST boundaries
                    games_in_week = db.query(Game).filter(
                        and_(
                            Game.game_datetime >= week_start_utc,
                            Game.game_datetime <= week_end_utc
                        )
                    ).all()

                    if games_in_week:
                        # Assign games to week
                        for game in games_in_week:
                            if game.week_id != week.id:
                                game.week_id = week.id
                                games_assigned += 1

                        # Update lock time to first game (in EST, on or after Monday)
                        first_game = min(
                            (g for g in games_in_week if g.game_datetime),
                            key=lambda g: g.game_datetime,
                            default=None
                        )

                        if first_game and week.lock_time != first_game.game_datetime:
                            week.lock_time = first_game.game_datetime
                            weeks_updated += 1

                if games_assigned > 0 or weeks_updated > 0:
                    db.commit()
                    console.print(f"[green]✓[/green] Assigned {games_assigned} games to weeks")
                    console.print(f"[green]✓[/green] Updated {weeks_updated} week lock times")

            console.print()
            console.print(f"[bold green]Summary:[/bold green]")
            console.print(f"  Created: {created_count}")
            console.print(f"  Updated: {updated_count}")
            console.print(f"  Skipped (non-regular season): {skipped_count}")
            console.print(f"  Errors: {error_count}")
            console.print(f"  Total processed: {created_count + updated_count + skipped_count + error_count}")

            # Display game labels found (for debugging)
            if game_labels_seen:
                console.print()
                console.print(f"[bold cyan]Game Labels Found:[/bold cyan]")
                for label in sorted(game_labels_seen):
                    console.print(f"  - \"{label}\"")

            # Display errors if any
            if errors:
                console.print()
                console.print(f"[bold red]Errors ({len(errors)}):[/bold red]")
                for error in errors:
                    console.print(f"  [red]✗[/red] {error}")

        except Exception as e:
            console.print(f"[red]✗[/red] Database error: {e}")
            db.rollback()
            sys.exit(1)
        finally:
            db.close()

    except requests.RequestException as e:
        console.print(f"[red]✗[/red] Failed to fetch data: {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected error: {e}")
        sys.exit(1)


@app.command()
def update_game_score(
    game_id: str = typer.Argument(..., help="NBA Game ID"),
    home_score: int = typer.Argument(..., help="Home team score"),
    away_score: int = typer.Argument(..., help="Away team score")
):
    """Update a game's final score and recalculate user points."""
    from app.core.database import SessionLocal
    from app.services.game_service import update_game_and_recalculate_points

    console.print(f"[bold blue]Updating Game Score[/bold blue]")
    console.print(f"Game ID: {game_id}")
    console.print(f"Score: Home {home_score} - Away {away_score}")
    console.print()

    db = SessionLocal()
    try:
        result = update_game_and_recalculate_points(
            db=db,
            game_id=game_id,
            home_score=home_score,
            away_score=away_score
        )

        if "error" in result:
            console.print(f"[yellow]⚠[/yellow] Warning: {result['error']}")

        console.print(f"[green]✓[/green] Game updated successfully")
        console.print()
        console.print(f"[bold]Results:[/bold]")
        console.print(f"  Winner ID: {result.get('winner_id', 'N/A')}")
        console.print(f"  Week Number: {result.get('week_number', 'N/A')}")
        console.print(f"  Affected Users: {result['affected_users']}")
        console.print(f"  Points Awarded: {result['points_awarded']}")

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


@app.command()
def recalculate_points():
    """Recalculate all user points from completed games."""
    from app.core.database import SessionLocal
    from app.services.game_service import recalculate_all_points

    console.print("[bold blue]Recalculating All Points[/bold blue]")
    console.print()

    if not typer.confirm("This will reset all points and recalculate. Continue?"):
        console.print("[yellow]Cancelled[/yellow]")
        return

    db = SessionLocal()
    try:
        result = recalculate_all_points(db)

        console.print(f"[green]✓[/green] Points recalculated successfully")
        console.print()
        console.print(f"[bold]Results:[/bold]")
        console.print(f"  Selections Processed: {result['selections_processed']}")
        console.print(f"  Users Affected: {result['users_affected']}")
        console.print(f"  Total Points Awarded: {result['total_points_awarded']}")

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


@app.command()
def import_csv(
    csv_file: str = typer.Argument("data/nba-pickem.csv", help="Path to CSV file"),
    league_name: str = typer.Option("Default League", "--league", help="League name")
):
    """Import pick'em data from CSV file."""
    from app.core.database import SessionLocal
    from app.services.csv_import_service import import_csv_data
    import os

    console.print(f"[bold blue]Importing CSV Data[/bold blue]")
    console.print(f"File: {csv_file}")
    console.print(f"League: {league_name}")
    console.print()

    # Check if file exists
    if not os.path.exists(csv_file):
        console.print(f"[red]✗[/red] File not found: {csv_file}")
        sys.exit(1)

    db = SessionLocal()
    try:
        stats = import_csv_data(db, csv_file, league_name)

        console.print(f"[green]✓[/green] CSV imported successfully")
        console.print()
        console.print(f"[bold]Results:[/bold]")
        console.print(f"  Users Created: {stats['users_created']}")
        console.print(f"  Users Updated: {stats['users_updated']}")
        console.print(f"  Weeks Created: {stats['weeks_created']}")
        console.print(f"  Selections Created: {stats['selections_created']}")

        if stats['errors']:
            console.print()
            console.print(f"[yellow]Errors ({len(stats['errors'])}):[/yellow]")
            for error in stats['errors'][:10]:  # Show first 10 errors
                console.print(f"  - {error}")
            if len(stats['errors']) > 10:
                console.print(f"  ... and {len(stats['errors']) - 10} more")

        console.print()
        console.print("[bold cyan]Note:[/bold cyan] Default password for new users is 'pass1234'")
        console.print("Users should reset their password on first login.")

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        import traceback
        console.print(traceback.format_exc())
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


@app.command()
def fix_clippers_name():
    """Fix any 'LA Clippers' team names to 'Los Angeles Clippers'."""
    from app.core.database import SessionLocal
    from app.models.models import Team

    console.print("[bold blue]Fixing LA Clippers Team Name[/bold blue]")
    console.print()

    db = SessionLocal()
    try:
        # Check if LA Clippers exists
        la_clippers = db.query(Team).filter(Team.name == "LA Clippers").first()

        if not la_clippers:
            console.print("[green]✓[/green] No 'LA Clippers' found - database is already correct")
            return

        # Check if Los Angeles Clippers already exists
        los_angeles_clippers = db.query(Team).filter(Team.name == "Los Angeles Clippers").first()

        if los_angeles_clippers:
            console.print("[yellow]⚠[/yellow] Both 'LA Clippers' and 'Los Angeles Clippers' exist!")
            console.print("This requires manual intervention to merge the teams.")
            console.print(f"LA Clippers ID: {la_clippers.id}")
            console.print(f"Los Angeles Clippers ID: {los_angeles_clippers.id}")
            sys.exit(1)

        # Rename LA Clippers to Los Angeles Clippers
        console.print(f"[yellow]Found:[/yellow] LA Clippers (ID: {la_clippers.id})")

        if not typer.confirm("Rename 'LA Clippers' to 'Los Angeles Clippers'?"):
            console.print("[yellow]Cancelled[/yellow]")
            return

        la_clippers.name = "Los Angeles Clippers"
        db.commit()

        console.print("[green]✓[/green] Successfully renamed 'LA Clippers' to 'Los Angeles Clippers'")

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


@app.command()
def retabulate_season(season_id: Optional[str] = None):
    """
    Retabulate all team selections for a specific season.

    This command will:
    1. Get all team selections for the season
    2. Recalculate points based on actual game results
    3. Update user total points
    4. Show detailed report of any changes
    """
    from app.core.database import SessionLocal
    from app.models.models import Season
    from app.services.game_service import retabulate_season as retab_service

    console.print("[bold blue]Retabulating Season Scores[/bold blue]")
    console.print()

    db = SessionLocal()
    try:
        # If no season_id provided, get the current season
        if not season_id:
            current_season = db.query(Season).order_by(Season.year.desc()).first()
            if not current_season:
                console.print("[red]✗[/red] No seasons found in database")
                sys.exit(1)
            season_id = str(current_season.id)
            console.print(f"[cyan]Using current season: {current_season.year}[/cyan]")
            console.print()

        # Run retabulation
        result = retab_service(db, season_id)

        console.print(f"[green]✓[/green] Season retabulation complete")
        console.print()
        console.print("[bold green]Summary:[/bold green]")
        console.print(f"  Season Year: {result['season_year']}")
        console.print(f"  Selections Found: {result['selections_found']}")
        console.print(f"  Selections Updated: {result['selections_updated']}")
        console.print(f"  Users Affected: {result['users_affected']}")
        console.print(f"  Total Points Awarded: {result['total_points_awarded']}")

        # Show changes if any
        if result['changes']:
            console.print()
            console.print(f"[bold yellow]Changes Detected ({len(result['changes'])}):[/bold yellow]")

            # Group changes by user
            from collections import defaultdict
            changes_by_user = defaultdict(list)
            for change in result['changes']:
                changes_by_user[change['user_id']].append(change)

            # Display changes per user
            for user_id, user_changes in changes_by_user.items():
                total_diff = sum(c['difference'] for c in user_changes)
                console.print()
                console.print(f"  [cyan]User {user_id[:8]}...[/cyan] (Total change: {total_diff:+d} points)")

                for change in sorted(user_changes, key=lambda x: x['week_number']):
                    modifier = ""
                    if change['is_superweek']:
                        modifier = " [SW]"
                    elif change['is_shoot_the_moon']:
                        modifier = " [STM]"

                    symbol = "↑" if change['difference'] > 0 else "↓" if change['difference'] < 0 else "="
                    color = "green" if change['difference'] > 0 else "red" if change['difference'] < 0 else "yellow"

                    console.print(
                        f"    Week {change['week_number']}{modifier}: "
                        f"{change['old_points']} → {change['new_points']} "
                        f"[{color}]({change['difference']:+d})[/{color}] {symbol} "
                        f"Record: {change['record']}"
                    )
        else:
            console.print()
            console.print("[green]No changes needed - all scores are accurate![/green]")

    except ValueError as e:
        console.print(f"[red]✗[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        import traceback
        console.print(traceback.format_exc())
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


@app.command()
def backfill_scores():
    """
    Backfill game scores from NBA API and recalculate all user points.

    This command will:
    1. Fetch latest game data from NBA API
    2. Update scores and winners for completed games
    3. Recalculate all team selection points (including Shoot the Moon)
    4. Update all user total points
    """
    from app.core.database import SessionLocal
    from app.models.models import Game, Team
    from app.services.game_service import recalculate_all_points

    url = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"

    console.print("[bold blue]Backfilling Game Scores and Recalculating Points[/bold blue]")
    console.print()

    try:
        # Step 1: Fetch data from NBA API
        console.print("[bold cyan]Step 1: Fetching game data from NBA API[/bold cyan]")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        console.print("[green]✓[/green] Data fetched successfully")
        console.print()

        db = SessionLocal()
        try:
            # Load all teams for lookup
            teams = db.query(Team).all()
            team_lookup = {team.name: team for team in teams}

            # Step 2: Update game scores
            console.print("[bold cyan]Step 2: Updating game scores[/bold cyan]")
            games_updated = 0
            games_with_scores = 0

            game_dates = data.get("leagueSchedule", {}).get("gameDates", [])

            for date_obj in game_dates:
                games = date_obj.get("games", [])
                # Get the local game date from the API (not UTC date)
                local_game_date_str = date_obj.get("gameDate")  # Format: "MM/DD/YYYY"

                for game_data in games:
                    try:
                        # Skip non-regular season
                        game_label = game_data.get("gameLabel", "")
                        regular_season_labels = {"", "Emirates NBA Cup", "NBA Mexico City Game"}
                        if game_label not in regular_season_labels:
                            continue

                        nba_game_id = game_data.get("gameId")
                        home_team_name_short = game_data.get("homeTeam", {}).get("teamName", "")
                        away_team_name_short = game_data.get("awayTeam", {}).get("teamName", "")

                        # Map to full team names
                        home_team_name = NBA_TEAM_MAPPING.get(home_team_name_short)
                        away_team_name = NBA_TEAM_MAPPING.get(away_team_name_short)

                        if not home_team_name or not away_team_name:
                            continue

                        home_team = team_lookup.get(home_team_name)
                        away_team = team_lookup.get(away_team_name)

                        if not home_team or not away_team:
                            continue

                        # Extract scores
                        home_score = game_data.get("homeTeam", {}).get("score")
                        away_score = game_data.get("awayTeam", {}).get("score")

                        # Only update if both scores are present (game is final)
                        if home_score is not None and away_score is not None:
                            games_with_scores += 1

                            # Determine winner
                            if home_score > away_score:
                                winner_id = home_team.id
                            elif away_score > home_score:
                                winner_id = away_team.id
                            else:
                                winner_id = None

                            # Parse datetime (use UTC time) and date (use local date from API)
                            game_datetime_str = game_data.get("gameDateTimeUTC")
                            game_datetime = None
                            game_date = None
                            if game_datetime_str:
                                game_datetime = datetime.fromisoformat(game_datetime_str.replace("Z", "+00:00"))
                            # Use local game date from API, not UTC date
                            if local_game_date_str:
                                # Parse date (format can be "MM/DD/YYYY" or "MM/DD/YYYY HH:MM:SS")
                                game_date = datetime.strptime(local_game_date_str.split()[0], "%m/%d/%Y").date()

                            # Find or create game
                            existing_game = db.query(Game).filter(Game.nba_game_id == nba_game_id).first()

                            if existing_game:
                                # Update existing game
                                existing_game.home_team_score = home_score
                                existing_game.away_team_score = away_score
                                existing_game.winner_id = winner_id
                                existing_game.game_datetime = game_datetime
                                existing_game.date = game_date
                                games_updated += 1
                            else:
                                # Create new game
                                new_game = Game(
                                    home_team_id=home_team.id,
                                    away_team_id=away_team.id,
                                    nba_game_id=nba_game_id,
                                    winner_id=winner_id,
                                    date=game_date,
                                    game_datetime=game_datetime,
                                    home_team_score=home_score,
                                    away_team_score=away_score,
                                )
                                db.add(new_game)
                                games_updated += 1

                    except Exception as e:
                        console.print(f"[yellow]⚠[/yellow] Error processing game {nba_game_id}: {e}")
                        continue

            db.commit()
            console.print(f"[green]✓[/green] Updated {games_updated} games with scores ({games_with_scores} completed games found)")
            console.print()

            # Step 3: Recalculate all points
            console.print("[bold cyan]Step 3: Recalculating all user points[/bold cyan]")
            result = recalculate_all_points(db)

            console.print(f"[green]✓[/green] Points recalculated successfully")
            console.print()

            # Final summary
            console.print("[bold green]Summary:[/bold green]")
            console.print(f"  Games Updated: {games_updated}")
            console.print(f"  Selections Processed: {result['selections_processed']}")
            console.print(f"  Users Affected: {result['users_affected']}")
            console.print(f"  Total Points Awarded: {result['total_points_awarded']}")

        except Exception as e:
            console.print(f"[red]✗[/red] Database error: {e}")
            import traceback
            console.print(traceback.format_exc())
            db.rollback()
            sys.exit(1)
        finally:
            db.close()

    except requests.RequestException as e:
        console.print(f"[red]✗[/red] Failed to fetch data: {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected error: {e}")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


@app.command()
def admin_submit_picks(
    email: str,
    week_number: int,
    teams: str,
    superweek: Annotated[bool, typer.Option("--superweek")] = False,
    shoot_the_moon: Annotated[bool, typer.Option("--shoot-the-moon")] = False
):
    """
    Admin command to submit picks for a user (bypasses lock check).
    Use this to manually enter picks for users who were affected by bugs.

    Example:
        python manage.py admin-submit-picks user@email.com 12 "Lakers,Warriors,Celtics"
        python manage.py admin-submit-picks user@email.com 12 "Bulls" --shoot-the-moon
    """
    from app.core.database import SessionLocal
    from app.models.models import User, Week, Team, TeamSelection, Season

    console.print(f"[bold blue]Admin: Submitting Picks[/bold blue]")
    console.print(f"User: {email}")
    console.print(f"Week: {week_number}")
    if superweek:
        console.print(f"[yellow]Superweek: YES[/yellow]")
    if shoot_the_moon:
        console.print(f"[yellow]Shoot the Moon: YES[/yellow]")
    console.print()

    db = SessionLocal()
    try:
        # Find user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            console.print(f"[red]✗[/red] User not found: {email}")
            sys.exit(1)

        # Find week
        week = db.query(Week).filter(Week.number == week_number).first()
        if not week:
            console.print(f"[red]✗[/red] Week {week_number} not found")
            sys.exit(1)

        # Parse team names/abbreviations
        team_names = [t.strip() for t in teams.split(',')]
        if not team_names or len(team_names) == 0:
            console.print(f"[red]✗[/red] No teams provided")
            sys.exit(1)

        # Find teams in database
        selected_teams = []
        for team_name in team_names:
            team = db.query(Team).filter(
                (Team.name.ilike(f"%{team_name}%")) |
                (Team.abbreviation == team_name.upper())
            ).first()

            if not team:
                console.print(f"[red]✗[/red] Team not found: {team_name}")
                sys.exit(1)
            selected_teams.append(team)

        console.print(f"[cyan]Selected teams:[/cyan]")
        for team in selected_teams:
            console.print(f"  - {team.name} ({team.abbreviation})")
        console.print()

        # Check if user already has selections for this week
        existing_selections = db.query(TeamSelection).filter(
            TeamSelection.user_id == user.id,
            TeamSelection.week_id == week.id
        ).all()

        if existing_selections:
            console.print(f"[yellow]⚠[/yellow] User already has {len(existing_selections)} selections for this week")
            if not typer.confirm("Delete existing selections and replace?"):
                console.print("[yellow]Cancelled[/yellow]")
                sys.exit(0)

            # Delete existing selections
            for selection in existing_selections:
                db.delete(selection)
            console.print(f"[green]✓[/green] Deleted {len(existing_selections)} existing selections")

        # Get season ID from week
        season = db.query(Season).filter(Season.id == week.season_id).first()
        if not season:
            console.print(f"[red]✗[/red] Season not found for week {week_number}")
            sys.exit(1)

        # Create new selections (bypassing lock check)
        # Ensure booleans are actual booleans (not strings)
        is_sw = True if str(superweek).lower() == 'true' else False
        is_stm = True if str(shoot_the_moon).lower() == 'true' else False

        for team in selected_teams:
            selection = TeamSelection(
                user_id=user.id,
                team_id=team.id,
                week_id=week.id,
                season_id=season.id,
                total_points=0,  # Will be calculated later
                is_superweek=is_sw,
                is_shoot_the_moon=is_stm
            )
            db.add(selection)

        db.commit()

        console.print()
        console.print(f"[green]✓[/green] Successfully submitted {len(selected_teams)} picks for {email}")
        console.print()
        console.print("[bold cyan]Note:[/bold cyan] Points will be calculated when games complete.")
        console.print("Run 'python manage.py recalculate-points' to recalculate all points.")

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        import traceback
        console.print(traceback.format_exc())
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    app()