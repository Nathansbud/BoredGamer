import requests
import json
import os
import datetime
import xmltodict

bgg_api = "https://api.geekdo.com/xmlapi2"

def get_games(name):
    response = requests.get(f'{bgg_api}/search?query={name.replace(" ", "%20")}&exact=1&type=boardgame')
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
    while response := requests.get(f"{bgg_api}/plays?username=Nathansbud&played=1&page={(i := i+1)}{f'&mindate={date_offset}' if days > 0 else ''}"):
        data = xmltodict.parse(response.content)
        plays = data["plays"]["play"] if 'play' in data['plays'] else []
        all_plays += [{'date':p.get('@date'), 'plays':int(p.get("@quantity")), "name":p.get('item', {}).get('@name')} for p in plays]
    return all_plays

def log_play(gid, plays=1):
    with requests.Session() as session, open(os.path.join(os.path.dirname(__file__), "credentials", "bgg.json")) as jf:
        login = {"credentials": json.load(jf)}
        headers = {'content-type': 'application/json'}
        cookies = session.post('https://boardgamegeek.com/login/api/v1', data=json.dumps(login), headers=headers)
        playload = {
            "playdate": datetime.datetime.now().strftime("%Y-%m-%d"),
            "objectid": f"{gid}",
            "objecttype":"thing",
            "action":"save",
            "quantity": f"{plays}",
        }

        response = session.post("https://boardgamegeek.com/geekplay.php", data=json.dumps(playload), headers=headers)
        #Still returns 200 on failure; check if "invalid action" appears in the returned html
        return not "invalid action" in response.text.lower()

if __name__ == '__main__':
    get_plays()
