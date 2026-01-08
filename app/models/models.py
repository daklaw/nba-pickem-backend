from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Date, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
import uuid

Base = declarative_base()


class League(Base):
    __tablename__ = "leagues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False)

    # Relationships
    users = relationship("User", back_populates="league")
    seasons = relationship("Season", back_populates="league")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    total_points = Column(Integer, default=0)
    league_id = Column(UUID(as_uuid=True), ForeignKey("leagues.id"), nullable=False)

    # Relationships
    league = relationship("League", back_populates="users")
    team_selections = relationship("TeamSelection", back_populates="user")


class Season(Base):
    __tablename__ = "seasons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    year = Column(Integer, nullable=False)
    league_id = Column(UUID(as_uuid=True), ForeignKey("leagues.id"), nullable=False)

    # Relationships
    league = relationship("League", back_populates="seasons")
    team_selections = relationship("TeamSelection", back_populates="season")


class Team(Base):
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, unique=True, nullable=False)
    abbreviation = Column(String, unique=True, nullable=False)

    # Relationships
    team_selections = relationship("TeamSelection", back_populates="team")
    home_games = relationship("Game", foreign_keys="Game.home_team_id", back_populates="home_team")
    away_games = relationship("Game", foreign_keys="Game.away_team_id", back_populates="away_team")


class Week(Base):
    __tablename__ = "weeks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    number = Column(Integer, nullable=False)  # Week number in the season (1, 2, 3, etc.)
    start_date = Column(Date, nullable=False)  # Monday of the week
    end_date = Column(Date, nullable=False)  # Sunday of the week
    lock_time = Column(DateTime, nullable=False)  # When picks lock (start of first game)
    season_id = Column(UUID(as_uuid=True), ForeignKey("seasons.id"), nullable=False)

    # Relationships
    season = relationship("Season")


class TeamSelection(Base):
    __tablename__ = "team_selections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    season_id = Column(UUID(as_uuid=True), ForeignKey("seasons.id"), nullable=False)
    week_id = Column(UUID(as_uuid=True), ForeignKey("weeks.id"), nullable=False)
    total_points = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    is_superweek = Column(Boolean, default=False)
    is_shoot_the_moon = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="team_selections")
    team = relationship("Team", back_populates="team_selections")
    season = relationship("Season", back_populates="team_selections")
    week = relationship("Week")

    # Computed properties
    @hybrid_property
    def week_number(self):
        """Get the week number from the related Week object."""
        if self.week:
            return self.week.number
        return None

    @hybrid_property
    def team_name(self):
        """Get the team name from the related Team object."""
        if self.team:
            return self.team.name
        return None

    # Uniqueness constraints:
    # 1. User can only make one selection per week
    # 2. User can only pick a team once per season
    __table_args__ = (
        UniqueConstraint('user_id', 'week_id', name='_user_week_uc'),
        UniqueConstraint('user_id', 'team_id', 'season_id', name='_user_team_season_uc'),
    )


class Game(Base):
    __tablename__ = "games"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    home_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    winner_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)  # Nullable until game is complete
    week_id = Column(UUID(as_uuid=True), ForeignKey("weeks.id"), nullable=True)  # Week this game belongs to
    date = Column(Date, nullable=False)

    # NBA API fields
    nba_game_id = Column(String, unique=True, nullable=True, index=True)  # NBA's game ID
    game_datetime = Column(DateTime, nullable=True)  # Full datetime from NBA API
    home_team_score = Column(Integer, nullable=True)
    away_team_score = Column(Integer, nullable=True)
    season_year = Column(String, nullable=True)  # e.g., "2024-25"

    # Relationships
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_games")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_games")
    week = relationship("Week")