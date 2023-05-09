from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy import Column, Integer, String, Table, ForeignKey, Float

db = SQLAlchemy()
Base = declarative_base()

match_teams = Table('match_teams', Base.metadata,
                    Column('match_id', ForeignKey('matches.id'), primary_key=True),
                    Column('team_id', ForeignKey('teams.id'), primary_key=True)
                    )

match_bets = Table('match_bets', Base.metadata,
                   Column('match_id', ForeignKey('matches.id'), primary_key=True),
                   Column('bet_id', ForeignKey('bets.id'), primary_key=True)
                   )

user_bets = Table('user_bets', Base.metadata,
                  Column('user_id', ForeignKey('users.id'), primary_key=True),
                  Column('bet_id', ForeignKey('bets.id'), primary_key=True)
                  )


class Match(Base):
    __tablename__ = 'matches'
    id = Column(Integer, primary_key=True)
    datetime = Column(String, unique=True, nullable=False)
    result = Column(String)
    best_of = Column(Integer, nullable=False)

    team1_odds = Column(Float)
    team2_odds = Column(Float)

    teams = relationship("Team", secondary="match_teams", back_populates='matches_t')
    bets_m = relationship("Bet", secondary="match_bets", back_populates='matches_b')


class Team(Base):
    __tablename__ = 'teams'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    tricode = Column(String, nullable=False)
    img_url = Column(String(1000), nullable=False)
    power_rank = Column(Float)

    matches_t = relationship("Match", secondary="match_teams", back_populates='teams')


class Bet(Base):
    __tablename__ = 'bets'
    id = Column(Integer, primary_key=True)
    datetime = Column(String, unique=True, nullable=False)
    amount = Column(Integer, nullable=False)

    matches_b = relationship("Match", secondary="match_bets", back_populates='bets_m')
    users_b = relationship("User", secondary="user_bets", back_populates='bets_u')


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    number = Column(Integer, unique=True, nullable=False)
    password = Column(String(100))
    facebook_name = Column(String(1000))
    token_balance = Column(Float)

    bets_u = relationship("Bet", secondary="user_bets", back_populates='users_b')
