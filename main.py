from flask import Flask, render_template, redirect, request, flash, url_for
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from matches_manager import MatchesManager
from math import floor
from datetime import datetime

from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField, SelectField, IntegerField
from wtforms.validators import DataRequired, NumberRange

from sqlalchemy import create_engine, Column, Integer, String, Table, ForeignKey, Float
from sqlalchemy.orm import declarative_base, relationship, Session


db = SQLAlchemy()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///octobet-2023.db"
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap(app)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)

matches_manager = MatchesManager()
now = datetime.now()

# Make the engine
engine = create_engine("sqlite:///octobet-2023.db", future=True, echo=False, connect_args={"check_same_thread": False})

# Make the DeclarativeMeta
Base = declarative_base()


# TODO: matches and view-matches route html formatting

# Declare classes for FlaskForm

class LoginForm(FlaskForm):
    number = IntegerField('Number', validators=[DataRequired()])
    password = StringField('Password', validators=[DataRequired()])
    submit = SubmitField('Submit')


class RegistrationForm(FlaskForm):
    number = IntegerField('Number', validators=[DataRequired()])
    password = StringField('Password', validators=[DataRequired()])
    name = StringField('Facebook Name', validators=[DataRequired()])
    submit = SubmitField('Submit')


class BetForm(FlaskForm):
    user_team = SelectField('Your Team', validators=[DataRequired()])
    token_amt = IntegerField('Your Wager (number of tokens)', validators=[DataRequired()])
    submit = SubmitField("Let's go!")


# Declare Classes / Tables
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
    user_team = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)

    matches_b = relationship("Match", secondary="match_bets", back_populates='bets_m')
    users_b = relationship("User", secondary="user_bets", back_populates='bets_u')


class User(Base, UserMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    number = Column(Integer, unique=True, nullable=False)
    password = Column(String(100))
    facebook_name = Column(String(1000))
    token_balance = Column(Float)

    bets_u = relationship("Bet", secondary="user_bets", back_populates='users_b')


# Create the tables in the database
Base.metadata.create_all(engine)

with Session(bind=engine) as session:
    pass


@app.route('/')
def home():
    return render_template('index.html', logged_in=current_user.is_authenticated)


@login_manager.user_loader
def load_user(user_id):
    return session.get(User, user_id)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if request.method == 'POST' and form.validate_on_submit():
        # create new user
        new_user = User()

        # if user.number is already in database
        if session.query(User).filter_by(number=form.number.data).first():
            flash('Number already in use, sign in instead', 'error')
            return redirect(url_for('login'))

        # salt and hash pw
        hashed_pw = generate_password_hash(form.password.data,
                                           method='pbkdf2:sha256',
                                           salt_length=8)
        new_user.number = form.number.data
        new_user.facebook_name = form.name.data
        new_user.password = hashed_pw
        new_user.token_balance = 0

        session.add(new_user)
        session.commit()

        login_user(new_user)
        return redirect(url_for('home'))

    else:
        return render_template("register.html", form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST' and form.validate_on_submit():

        number = form.number.data
        password = form.password.data

        user = session.query(User).filter_by(number=number).first()

        if not user:
            flash('Invalid credentials', 'error')
            return render_template("login.html", form=form)

        # noinspection PyTypeChecker
        if check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))

        else:
            flash('Incorrect password', 'error')
            return render_template("login.html", form=form)
    else:
        return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/matches')
def display_matches():
    show_list = []
    match_list = session.query(Match).order_by(Match.id).all()

    # check match_list in Match.db for future matches
    for match in match_list:
        # noinspection PyTypeChecker
        date_time_obj = datetime.strptime(match.datetime, '%B %d - %I %p')
        date_time_obj = date_time_obj.replace(year=2023)
        if date_time_obj > now:
            show_list.append(match)
    return render_template('matches.html', match_list=show_list, logged_in=current_user.is_authenticated)


@app.route('/view-match/<int:match_id>', methods=['GET', 'POST'])
def single_match(match_id):
    form = BetForm()
    match = session.query(Match).filter_by(id=match_id).first()
    active_bet = None

    if current_user.is_authenticated:

        # check if user has existing bet on this match
        for bet in match.bets_m:
            for user in bet.users_b:
                if current_user.number == user.number:
                    active_bet = bet

        if not active_bet:  # make new bet
            team_names = [team.name for team in match.teams]
            max_token = int(floor(current_user.token_balance))
            form.user_team.choices = team_names
            form.token_amt.validators = [DataRequired(message=f'Whole tokens only! (1 to {max_token} token/s)'),
                                         NumberRange(min=1, max=max_token,
                                                     message=f'Whole tokens only! (1 to {max_token} token/s)')]

            if form.validate_on_submit():
                print('Bet accepted')
                date_time = now.strftime("%m/%d/%Y, %H:%M:%S")

                # affect user_balance
                current_user.token_balance -= form.token_amt.data

                # create new bet record in bets.db
                new_bet = Bet(datetime=date_time, amount=form.token_amt.data, user_team=form.user_team.data)
                new_bet.users_b = [current_user]
                new_bet.matches_b = [match]

                session.add(new_bet)
                session.commit()

                return redirect('/matches')
                # TODO: redirect to user profile instead

            else:
                return render_template('view-match.html', match=match, logged_in=current_user.is_authenticated,
                                       form=form, active_bet=active_bet)

        elif active_bet:  # show details of existing bet
            return render_template('view-match.html', match=match, logged_in=current_user.is_authenticated,
                                   form=form, active_bet=active_bet)

    else:
        return render_template('view-match.html', match=match, logged_in=current_user.is_authenticated,
                               form=form, active_bet=active_bet)


@app.route('/rank')
@login_required
def first_update():
    """run this function to find teams, or update the power rank of teams, and update team database"""
    team_list = session.query(Team).order_by(Team.id).all()
    team_name_list = [team.name for team in team_list]
    command = input('crawl/rank: ').lower()
    if command == 'crawl':
        # crawl lolesports for list of teams
        print('No rating list found')
        rating_list = matches_manager.generate_ranking()
        for item in rating_list:
            print(item.name, item.tricode)
            if item.name not in team_name_list:
                print('new team added')
                session.add(item)
        session.commit()
        return redirect('/')
    elif command == 'rank':
        # ask input for power ranking of found teams
        print('Team list found, no rating')
        for team in team_list:
            if team.power_rank is None:
                team.power_rank = input(f'What is the power rank of {team.name}? ')
                session.commit()
        return redirect('/')


@app.route('/crawl')
@login_required
def second_update():
    """run this function to find list of displayed future matches, and update match database"""
    match_list = session.query(Match).order_by(Match.id).all()

    # crawl lolesports for list of future matches
    try:
        short_list = matches_manager.start_crawl()
    except IndexError:
        # handle error for when lolesports responds poorly
        short_list = matches_manager.start_crawl()

    finally:
        # create new match records
        for (dt, bo, team1, team2) in short_list:
            t1 = session.query(Team).filter_by(name=team1).first()
            t2 = session.query(Team).filter_by(name=team2).first()
            if t1.name != t2.name:
                new_match = Match(datetime=dt, result=None, best_of=bo, team1_odds=0, team2_odds=0)
                new_match.teams = [t1, t2]
                session.add(new_match)
        session.commit()
        return redirect('/')


@app.route('/combine')
@login_required
def third_update():
    """run this function to generate odds and update match database"""
    match_list = session.query(Match).order_by(Match.id).all()
    for match in match_list:
        if match.team1_odds == 0:
            t1, t2 = match.teams
            if t1.name == 'TBD' or t2.name == 'TBD':
                match.team1_odds = None
                match.team2_odds = None
            else:
                match.team1_odds, match.team2_odds = matches_manager.generate_odds(t1.power_rank, t2.power_rank)
            print(f'{match.datetime} - {t1.name, match.team1_odds} vs {t2.name, match.team2_odds}')
            session.commit()
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
