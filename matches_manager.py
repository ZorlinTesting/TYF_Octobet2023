from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from classes import Team


lol_esports_url = 'https://lolesports.com/schedule?leagues=msi'
tbd_url = 'https://am-a.akamaihd.net/image?resize=140:&f=http%3A%2F%2Fassets.lolesports.com%2Fwatch%2Fteam-tbd.png'
floor = 20
overround = 0.05
# number_of_days = 19
remaining_no_days = 13
number_of_matches = 25


class MatchesManager:
    def __init__(self):
        self.initial_list = []
        self.match_list = []
        self.rating_list = []

    def generate_ranking(self):
        """input: match_objects list, output: unique team list in json with power ranking"""
        options = webdriver.ChromeOptions()
        options.add_experimental_option('detach', True)
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(lol_esports_url)

        website = driver.page_source
        soup = BeautifulSoup(website, 'html.parser')

        # team 1 processing
        all_team1 = soup.select(selector=".EventMatch .future .teams .team1 .team-info span")
        team1_list = [team1.getText() for team1 in all_team1]
        all_team1_img = soup.select(selector=".EventMatch .future .teams .team1 img")
        team1_img = [team1.get('src') for team1 in all_team1_img]
        team1_names = [name for name in team1_list if team1_list.index(name) % 2 == 0 and 'TBD' not in name]
        team1_tri = [tri for tri in team1_list if team1_list.index(tri) % 2 == 1 and 'TBD' not in tri]
        team1_img = [img for img in team1_img if 'team-tbd.png' not in img]

        # team 2 processing
        all_team2 = soup.select(selector=".EventMatch .future .teams .team2 .team-info span")
        team2_list = [team2.getText() for team2 in all_team2]
        all_team2_img = soup.select(selector=".EventMatch .future .teams .team2 img")
        team2_img = [team2.get('src') for team2 in all_team2_img]
        team2_names = [name for name in team2_list if team2_list.index(name) % 2 == 0 and 'TBD' not in name]
        # team2_tri = [tri for tri in team2_list if team2_list.index(tri) % 2 == 1 and 'TBD' not in tri]
        team2_img = [img for img in team2_img if 'team-tbd.png' not in img]

        team2_tri = []
        for tri in team2_list:
            if 'TBD' not in tri:
                if team2_list.index(tri) % 2 == 1:
                    team2_tri.append(tri)
                elif tri == 'T1' and team2_list.index(tri) % 2 == 0:  # exception: since T1 name == T1 tri
                    team2_tri.append(tri)

        # cross-checking and fusing
        team_names = team1_names + team2_names
        team_names = list(dict.fromkeys(team_names))

        team_tri = team1_tri + team2_tri
        team_tri = list(dict.fromkeys(team_tri))

        team_img = team1_img + team2_img
        team_img = list(dict.fromkeys(team_img))

        # generating Team objects
        for i in range(0, len(team_names)):
            new_team = Team(name=team_names[i], tricode=team_tri[i], img_url=team_img[i], power_rank=None)
            self.rating_list.append(new_team)
        new_team = Team(name='TBD', tricode='TBD', img_url=tbd_url, power_rank=None)
        self.rating_list.append(new_team)
        return self.rating_list

    def start_crawl(self):
        """access lolesports page, generate list of match dictionaries"""
        options = webdriver.ChromeOptions()
        options.add_experimental_option('detach', True)
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(lol_esports_url)

        website = driver.page_source
        soup = BeautifulSoup(website, 'html.parser')

        all_time = soup.select(selector=".EventMatch .future .EventTime .time span")
        time_list = [time.getText() for time in all_time if time.getText() != 'APPROX']

        all_team1 = soup.select(selector=".EventMatch .future .teams .team1 .team-info span")
        team1_list = [team1.getText() for team1 in all_team1]

        all_team2 = soup.select(selector=".EventMatch .future .teams .team2 .team-info span")
        team2_list = [team2.getText() for team2 in all_team2]

        all_best_of = soup.select(selector=".EventMatch .future .league div")
        best_of_list = [bo.getText() for bo in all_best_of]
        best_of_list = [item[-1] for item in best_of_list]

        all_days = soup.select(selector=".EventDate .date span")
        all_days = [day.getText() for day in all_days[2::3]]
        day_list = []
        for i in range(0, int(remaining_no_days)):
            a = all_days.pop(-1)
            day_list.append(a)
            day_list.append(a)
            if 14 <= i <= 19 or i == 7:  # manually configured to match day order
                day_list.append(a)
                day_list.append(a)
        day_list.reverse()

        for item in range(0, len(team1_list), 2):
            new_match = (f'{day_list[item]} - {time_list[item]} {time_list[item + 1]}', best_of_list[item + 1],
                         team1_list[item], team2_list[item])
            self.match_list.append(new_match)
        return self.match_list

    def generate_odds(self, pr1, pr2):
        """generate processed match data to sql database"""
        # base chance
        pr1 = 1 - (float(pr1) / int(floor))
        pr2 = 1 - (float(pr2) / int(floor))

        # predicted wager share, add overround, inverse for odds
        odds1 = round(1 / ((pr1 / (pr1 + pr2)) + int(overround)), 2)
        odds2 = round(1 / ((pr2 / (pr1 + pr2)) + int(overround)), 2)

        return odds1, odds2
