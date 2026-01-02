# Game Service

Service layer for handling NBA game updates and user point calculations.

## Features

### 1. Update Game Scores and Recalculate Points
When a game becomes final, this service:
- Updates the game with final scores
- Identifies the winner
- Determines which week the game belongs to
- Finds all users who picked the winning team for that week
- Awards points based on their selection modifiers
- Updates both team selection points and user total points

### 2. Point Calculation System

**Base Scoring:**
- Regular pick: **1 point** per win
- Superweek: **2 points** per win (2x multiplier)
- Shoot the Moon: **2 points** per loss (2x multiplier) - only if team loses ALL games, otherwise 0 points

### 3. Week Determination

The system automatically determines which week a game belongs to:
- Week 1 starts with the first regular season game
- Each week is 7 days long
- Weeks are automatically created as needed

## Usage

### From Code (Service Function)

```python
from app.core.database import SessionLocal
from app.services.game_service import update_game_and_recalculate_points

db = SessionLocal()
try:
    result = update_game_and_recalculate_points(
        db=db,
        game_id="0022500123",  # NBA Game ID
        home_score=110,
        away_score=105,
        game_status=3,  # 3 = Final
        game_status_text="Final"
    )

    print(f"Winner ID: {result['winner_id']}")
    print(f"Affected Users: {result['affected_users']}")
    print(f"Points Awarded: {result['points_awarded']}")
finally:
    db.close()
```

### From Command Line

**Update a single game:**
```bash
python manage.py update-game-score 0022500123 110 105
```

**Recalculate all points from scratch:**
```bash
python manage.py recalculate-points
```

## Functions

### `update_game_and_recalculate_points()`
Updates a game's final score and recalculates points for affected users.

**Parameters:**
- `db` (Session): Database session
- `game_id` (str): NBA game ID
- `home_score` (int): Final home team score
- `away_score` (int): Final away team score
- `game_status` (int, optional): Game status code (default: 3)
- `game_status_text` (str, optional): Game status text (default: "Final")

**Returns:**
```python
{
    "game_id": "0022500123",
    "winner_id": "uuid-of-winner",
    "winner_score": 110,
    "loser_score": 105,
    "week_number": 5,
    "affected_users": 12,
    "points_awarded": 15  # Could be higher if users had superweek/shoot the moon
}
```

### `recalculate_all_points()`
Recalculates all user points from completed games. Useful for:
- Fixing data inconsistencies
- Initial migration of existing games
- Testing/debugging

**Parameters:**
- `db` (Session): Database session

**Returns:**
```python
{
    "games_processed": 250,
    "users_affected": 45,
    "total_points_awarded": 1234
}
```

### `get_week_for_date()`
Determines which week a game belongs to based on its date.

**Parameters:**
- `db` (Session): Database session
- `game_date` (date): Date of the game

**Returns:**
- Week object or None

### `calculate_points_for_win()`
Calculates points awarded for a win based on selection modifiers.

**Parameters:**
- `team_selection` (TeamSelection): The team selection to calculate points for

**Returns:**
- int: Number of points to award

## Integration with NBA API

The `ingest-games` command automatically imports game scores from the NBA API.
To set up automatic score updates:

1. Run `ingest-games` periodically (e.g., every 15 minutes during game days)
2. The command will update scores for all games
3. Call `update_game_and_recalculate_points()` for newly completed games

Or use a webhook from NBA API if available.

## Database Schema Requirements

This service requires the following models:
- **Game**: Stores game information including scores and winner
- **Team**: NBA teams
- **Week**: Week numbers for the season
- **TeamSelection**: User's team picks with modifiers
- **User**: Users with total points

## Example Workflow

1. User picks Lakers for Week 5 with Superweek modifier
2. Lakers play and win a game during Week 5
3. Service is called: `update_game_and_recalculate_points()`
4. Service determines Lakers won
5. Service finds Week 5
6. Service finds all TeamSelections for Lakers in Week 5
7. Service awards 2 points (1 base × 2 superweek) to the user
8. User's total_points and TeamSelection.total_points are updated

## Testing

Test the service with a completed game:
```bash
# Get a completed game ID
psql $DATABASE_URL -c "SELECT nba_game_id FROM games WHERE game_status = 3 LIMIT 1;"

# Test the update (use actual scores)
python manage.py update-game-score <game_id> <home_score> <away_score>
```