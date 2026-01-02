# NBA Pick'em Fantasy Game - Backend API

A FastAPI-based backend for an NBA pick'em fantasy game where users select teams each week throughout the season.

## Features

- User authentication with JWT tokens
- League and season management
- Team selection with constraints (one team per season per user)
- RESTful API endpoints
- PostgreSQL database with psycopg3 driver

## Project Structure

```
nba_pickem/
├── app/
│   ├── core/
│   │   ├── config.py          # Application settings
│   │   ├── database.py        # Database configuration
│   │   └── security.py        # Password hashing & JWT
│   ├── dependencies/
│   │   └── auth.py            # Authentication dependencies
│   ├── models/
│   │   └── models.py          # SQLAlchemy database models
│   ├── routers/
│   │   ├── auth.py            # Authentication endpoints
│   │   └── team_selections.py # Team selection endpoints
│   └── schemas/
│       └── schemas.py         # Pydantic validation schemas
├── main.py                    # FastAPI application entry point
├── requirements.txt           # Python dependencies
└── .env                       # Environment variables (create from .env.example)
```

## Setup

### 1. PostgreSQL Setup

First, ensure PostgreSQL is installed and running on your system.

**Create the database:**
```bash
# Using psql
createdb nba_pickem

# Or connect to PostgreSQL and run:
# CREATE DATABASE nba_pickem;
```

### 2. Install Dependencies

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Settings

Create a `.env` file in the root directory (copy from `.env.example`):

```bash
cp .env.example .env
```

Update the `.env` file with your settings:

```env
# Database Configuration (note the postgresql+psycopg:// prefix for psycopg3)
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/nba_pickem

# JWT Configuration
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Settings
APP_NAME=NBA Pick'em API
DEBUG=True
```

**Important:**
- Use `postgresql+psycopg://` prefix (not `postgresql://`) to use psycopg3
- Change the credentials to match your PostgreSQL setup

### 4. Run the Server

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

The database tables will be automatically created on first startup.

### 5. Access API Documentation

FastAPI automatically generates interactive API documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Database Models

### League
- `id`: Primary key
- `name`: League name

### User
- `id`: Primary key
- `email`: User email (unique)
- `hashed_password`: Hashed password
- `total_points`: Total points accumulated
- `league_id`: Foreign key to League

### Season
- `id`: Primary key
- `year`: Season year
- `league_id`: Foreign key to League

### Team
- `id`: Primary key
- `name`: Team name (e.g., "New York Knicks")
- `logo`: URL or path to logo image

### Week
- `id`: Primary key
- `number`: Week number

### TeamSelection
- `id`: Primary key
- `user_id`: Foreign key to User
- `team_id`: Foreign key to Team
- `season_id`: Foreign key to Season
- `week_id`: Foreign key to Week
- `total_points`: Points for this selection
- `is_superweek`: Boolean flag
- `is_shoot_the_moon`: Boolean flag
- **Unique constraint**: (user_id, team_id, season_id)

### Game
- `id`: Primary key
- `home_team_id`: Foreign key to Team
- `away_team_id`: Foreign key to Team
- `winner_id`: Foreign key to Team (nullable)
- `date`: Game date

## API Endpoints

### Authentication

#### Register User
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword",
  "league_id": 1
}
```

#### Login
```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=securepassword
```

Returns:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Logout
```http
POST /auth/logout
Authorization: Bearer <token>
```

### Team Selections

#### Get Available Teams
Get all teams that the user hasn't selected this season:

```http
GET /team-selections/available-teams?season_id=1
Authorization: Bearer <token>
```

#### Make a Team Selection
```http
POST /team-selections/?season_id=1
Authorization: Bearer <token>
Content-Type: application/json

{
  "team_id": 5,
  "week_id": 3,
  "is_superweek": false,
  "is_shoot_the_moon": false
}
```

#### Get My Selections
```http
GET /team-selections/my-selections?season_id=1
Authorization: Bearer <token>
```

## Usage Example

### 1. Register a User
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "player@example.com",
    "password": "mypassword",
    "league_id": 1
  }'
```

### 2. Login
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=player@example.com&password=mypassword"
```

### 3. Get Available Teams
```bash
curl -X GET "http://localhost:8000/team-selections/available-teams?season_id=1" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 4. Make a Team Selection
```bash
curl -X POST "http://localhost:8000/team-selections/?season_id=1" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": 5,
    "week_id": 1,
    "is_superweek": false,
    "is_shoot_the_moon": false
  }'
```

## Business Rules

1. **One Team Per Season**: Users can only select each team once per season
2. **Authentication Required**: All team selection endpoints require authentication
3. **League Membership**: Users can only make selections for seasons in their league

## CORS Configuration

The API is configured to accept requests from:
- `http://localhost:3000` (Create React App)
- `http://localhost:5173` (Vite)

Update `main.py` to add additional origins as needed.

## Next Steps

To fully implement the game, you'll need to:

1. **Seed Initial Data**: Create leagues, seasons, teams, and weeks
2. **Add Game Management**: Endpoints to create and update games
3. **Points Calculation**: Logic to calculate points based on game results
4. **Leaderboard**: Endpoint to show user rankings
5. **Admin Panel**: Endpoints for managing leagues and seasons
6. **Frontend Integration**: Connect with your React application

## Database Migrations

For production environments, consider using [Alembic](https://alembic.sqlalchemy.org/) for database migrations instead of the automatic table creation:

```bash
# Install Alembic
pip install alembic

# Initialize Alembic
alembic init migrations

# Create a migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

This provides better control over schema changes and allows for rollbacks.

## Production Deployment

### Database Configuration

For production, use a managed PostgreSQL service or properly configured PostgreSQL instance:

```env
# Production example (use postgresql+psycopg:// for psycopg3)
DATABASE_URL=postgresql+psycopg://user:password@db.example.com:5432/nba_pickem_prod
```

### Connection Pooling

The application already uses SQLAlchemy's connection pooling. For production, you may want to adjust pool settings in `app/core/database.py`:

```python
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,          # Adjust based on your needs
    max_overflow=10,       # Extra connections when pool is full
    echo=settings.DEBUG
)
```

## Security Notes

- **Change `SECRET_KEY`**: Generate a strong random key for production (use environment variables)
- **Use HTTPS**: Always use HTTPS in production
- **Implement rate limiting**: Add rate limiting middleware to prevent abuse
- **Input validation**: All inputs are validated with Pydantic schemas
- **Refresh tokens**: Consider implementing refresh tokens for better security
- **Password requirements**: Enforce strong password policies
- **Database credentials**: Never commit `.env` file to version control
- **CORS**: Update allowed origins in `main.py` for production domains