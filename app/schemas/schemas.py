from pydantic import BaseModel, EmailStr, field_serializer
from typing import Optional, List
from datetime import date, datetime, timezone
from uuid import UUID


# User Schemas
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str
    league_id: UUID


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: UUID
    total_points: int
    league_id: UUID

    class Config:
        from_attributes = True


# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: UUID
    current_season_id: Optional[UUID] = None


class TokenData(BaseModel):
    email: Optional[str] = None


# Team Schemas
class TeamBase(BaseModel):
    name: str
    abbreviation: str


class TeamCreate(TeamBase):
    pass


class TeamResponse(TeamBase):
    id: UUID

    class Config:
        from_attributes = True


# League Schemas
class LeagueBase(BaseModel):
    name: str


class LeagueCreate(LeagueBase):
    pass


class LeagueResponse(LeagueBase):
    id: UUID

    class Config:
        from_attributes = True


# Season Schemas
class SeasonBase(BaseModel):
    year: int
    league_id: UUID


class SeasonCreate(SeasonBase):
    pass


class SeasonResponse(SeasonBase):
    id: UUID

    class Config:
        from_attributes = True


# Week Schemas
class WeekBase(BaseModel):
    number: int
    start_date: date  # Monday
    end_date: date  # Sunday
    lock_time: datetime  # When picks lock (start of first game)
    season_id: UUID

    @field_serializer('lock_time')
    def serialize_lock_time(self, dt: datetime, _info):
        """Serialize lock_time with UTC timezone (Z suffix)"""
        if dt is None:
            return None
        # Add UTC timezone if naive
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # Convert to UTC
        utc_dt = dt.astimezone(timezone.utc)
        # Return with Z suffix
        iso_string = utc_dt.isoformat()
        if iso_string.endswith('+00:00'):
            return iso_string[:-6] + 'Z'
        return iso_string


class WeekCreate(WeekBase):
    pass


class WeekResponse(WeekBase):
    id: UUID

    class Config:
        from_attributes = True


class NextWeekSelectionResponse(BaseModel):
    team_id: Optional[UUID] = None
    team_name: Optional[str] = None
    is_superweek: bool = False
    is_shoot_the_moon: bool = False


class NextWeekResponse(WeekBase):
    id: UUID
    can_use_superweek: bool
    selection: NextWeekSelectionResponse

    class Config:
        from_attributes = True


class CurrentWeekSelectionResponse(BaseModel):
    team_id: Optional[UUID] = None
    team_name: Optional[str] = None
    is_superweek: bool = False
    is_shoot_the_moon: bool = False


class CurrentWeekResponse(WeekBase):
    id: UUID
    is_locked: bool
    selection: CurrentWeekSelectionResponse

    class Config:
        from_attributes = True


# TeamSelection Schemas
class TeamSelectionCreate(BaseModel):
    team_id: UUID
    week_id: UUID
    is_superweek: bool = False
    is_shoot_the_moon: bool = False


class TeamSelectionResponse(BaseModel):
    id: UUID
    user_id: UUID
    team_id: UUID
    team_name: str
    season_id: UUID
    week_id: UUID
    week_number: int
    total_points: int
    is_superweek: bool
    is_shoot_the_moon: bool

    class Config:
        from_attributes = True


# Game Schemas
class GameBase(BaseModel):
    home_team_id: UUID
    away_team_id: UUID
    date: date


class GameCreate(GameBase):
    pass


class GameUpdate(BaseModel):
    winner_id: Optional[UUID] = None


class GameResponse(GameBase):
    id: UUID
    winner_id: Optional[UUID] = None

    class Config:
        from_attributes = True


# League Standings Schemas
class UserStandingResponse(BaseModel):
    rank: int
    user_id: UUID
    email: str
    name: str
    season_points: int
    current_week_team_name: Optional[str] = None
    current_week_is_superweek: bool = False
    current_week_is_shoot_the_moon: bool = False
    current_week_points: int = 0


class LeagueStandingsResponse(BaseModel):
    league_id: UUID
    league_name: str
    season_id: UUID
    season_year: int
    standings: List[UserStandingResponse]


# Weekly Selections Schemas
class UserWeeklySelectionResponse(BaseModel):
    user_id: UUID
    name: str
    has_selected: bool
    team_id: Optional[UUID] = None
    team_name: Optional[str] = None
    team_logo: Optional[str] = None
    is_superweek: bool
    is_shoot_the_moon: bool
    total_points: int


class WeeklySelectionsResponse(BaseModel):
    league_id: UUID
    league_name: str
    season_id: UUID
    season_year: int
    week_id: UUID
    week_number: int
    selections: List[UserWeeklySelectionResponse]


# Team Games Schema
class TeamGamesResponse(BaseModel):
    id: UUID
    week_id: Optional[UUID] = None
    date: date
    game_datetime: Optional[datetime] = None
    home_team_id: UUID
    home_team_name: Optional[str] = None
    home_team_score: Optional[int] = None
    away_team_id: UUID
    away_team_name: Optional[str] = None
    away_team_score: Optional[int] = None
    winner_id: Optional[UUID] = None
    winner_name: Optional[str] = None
    nba_game_id: Optional[str] = None

    @field_serializer('game_datetime')
    def serialize_game_datetime(self, dt: Optional[datetime], _info):
        """Serialize game_datetime with UTC timezone (Z suffix)"""
        if dt is None:
            return None
        # Add UTC timezone if naive
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # Convert to UTC
        utc_dt = dt.astimezone(timezone.utc)
        # Return with Z suffix
        iso_string = utc_dt.isoformat()
        if iso_string.endswith('+00:00'):
            return iso_string[:-6] + 'Z'
        return iso_string


# Next Week Schedule Schema
class NextWeekGameSchedule(BaseModel):
    opponent_name: str
    opponent_abbreviation: str
    date: date
    is_away: bool