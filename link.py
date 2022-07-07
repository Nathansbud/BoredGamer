import datetime
import json
import os
import re

import requests
import xmltodict

from utils import *

bgg_api = "https://api.geekdo.com/xmlapi2"

def get_user(): 
    try: 
        with open(creds_path) as jf: 
            return json.load(jf)
    except FileNotFoundError:
        return login()  

def login():
    os.makedirs(os.path.join(os.path.dirname(__file__), "credentials"), exist_ok=True)
    username = input(f"Enter your BoardGameGeek {CYAN}username{DEFAULT}: ")
    password = input(f"Enter your BoardGameGeek {GREEN}password{DEFAULT}: ")
    with open(creds_path, 'w') as cf:
        creds = {"username": username, "password": password}
        json.dump(creds, cf)
        print(f"Saved login information for user {CYAN}{username}{DEFAULT}; if this is {RED}incorrect{DEFAULT}, run {YELLOW}bgg -l{DEFAULT} to login again!")
        return creds     
        
def get_games(name):
    pattern = '[^a-zA-Z0-9\s]'
    response = requests.get(f'{bgg_api}/search?query={re.sub(pattern, "", name).replace(" ", "%20")}&exact=0&type=boardgame')

    if response:
        response = xmltodict.parse(response.content)
        total = int(response.get('items', {}).get('@total'))
        
        if total == 0: return []
        else:
            return [{'name': item.get('name', {}).get('@value'), 'year': item.get('yearpublished', {}).get('@value'), 'idx':item.get('@id')} for item in ([response['items']['item']] if total == 1 else response['items']['item'])]
            
def get_plays(days=30):
    if not days: days = 0
    date_offset = (datetime.datetime.now() - datetime.timedelta(days=days if days else 0)).strftime("%y-%m-%d")

    i = 0
    all_plays = []
    user = get_user()
    while (response := requests.get(f"{bgg_api}/plays?username={user.get('username')}&played=1&page={(i := i+1)}{f'&mindate={date_offset}' if days > 0 else ''}")):
        if "invalid object or user" in response.text.lower():
            print(f"{RED}Could not find any plays for user {user.get('username')}{DEFAULT}. Try logging in with {YELLOW}bgg -l{DEFAULT}!")
            exit(1)

        data = xmltodict.parse(response.content)
        plays = data["plays"]["play"] if 'play' in data['plays'] else []
        
        all_plays += [{'date':p.get('@date'), 'plays':int(p.get("@quantity")), "name":p.get('item', {}).get('@name')} for p in plays if not isinstance(p, str)]

    return all_plays

def log_play(gid, plays=1, comment=""):
    with requests.Session() as session:
        login = {"credentials": get_user()}
        headers = {'content-type': 'application/json'}
        cookies = session.post('https://boardgamegeek.com/login/api/v1', data=json.dumps(login), headers=headers)
        playload = {
            "playdate": datetime.datetime.now().strftime("%Y-%m-%d"),
            "objectid": f"{gid}",
            "objecttype":"thing",
            "action":"save",
            "quantity": f"{plays}",
            "comments": comment
        }

        response = session.post("https://boardgamegeek.com/geekplay.php", data=json.dumps(playload), headers=headers)
        res_text = response.text.lower()

        if "you must login to save plays" in res_text:
            return 401
        elif not "invalid action" in res_text: 
            return 200
        else:
            return 400

if __name__ == '__main__':
    get_plays()
