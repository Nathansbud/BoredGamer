import requests
import json
import os
import datetime
import xmltodict
import re
import time

from typing import Optional, Union

from model import Game

# Docs: https://boardgamegeek.com/wiki/page/BGG_XML_API2
bgg_api = "https://api.geekdo.com/xmlapi2"
creds_path = os.path.join(os.path.dirname(__file__), "credentials", "bgg.json")

def authenticated_request(method):
    def authenticated_function(*args, **kwargs):
        with requests.Session() as session, open(creds_path) as jf:
            session.post('https://boardgamegeek.com/login/api/v1', data=json.dumps({
                "credentials": json.load(jf)
            }), headers={'content-type': 'application/json'})

            return method(*args, BGG_SESSION=session, **kwargs)

    return authenticated_function

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
    while (response := requests.get(f"{bgg_api}/plays?username=Nathansbud&played=1&page={(i := i+1)}{f'&mindate={date_offset}' if days > 0 else ''}")):
        data = xmltodict.parse(response.content)
        plays = data["plays"]["play"] if 'play' in data['plays'] else []
        
        all_plays += [{'date':p.get('@date'), 'plays':int(p.get("@quantity")), "name":p.get('item', {}).get('@name')} for p in plays if not isinstance(p, str)]

    return all_plays

def get_collection(username: str):
    response = requests.get(f"{bgg_api}/collection?username={username}")
    timeout = 1
    while response.status_code != 200:
        response = requests.get(f"{bgg_api}/collection?username={username}")
        time.sleep(timeout)
        timeout *= 2
    
    collection = xmltodict.parse(response.content)
    owned, wishlist = [], []
    for item in collection["items"]["item"]:
        model = Game(name=item["name"]["#text"], id=item["@objectid"])

        if item["status"]["@own"] == "1":
            owned.append(model)
        elif item["status"]["@wishlist"] == 1:
            wishlist.append(model)
    
    return owned, wishlist

def get_game(id: Union[int, str]):
    retries = 0
    while retries < 5:
        response = requests.get(f"{bgg_api}/thing?id={id}&thingtype=boardgame&stats=1")
        if not response.content: 
            return None
        
        returned = xmltodict.parse(response.content)
        
        # BGG sometimes spuriously returns an error response without particular cause (doesn't appear to be rate limit),
        # so simply sleep and retry
        if "error" in returned:
            print(f"Received error attempting to get ID {id}: {returned['error']}; retrying...")
            retries += 1
            time.sleep(1)
        else:
            content = returned["items"]["item"]
            break
    else:
        return None

    best_with, recommended_counts = None, []
    for result in content["poll-summary"]["result"]:
        if result.get("@name") in ["bestwith", "recommmendedwith"]:
            bounds = "".join(result["@value"].split(" ")[2:-1]).rstrip("+")
            if "," not in bounds:
                bounds = bounds.split("–")
                output = list(range(
                    int(bounds[0]), 
                    int(bounds[1] if len(bounds) > 1 else bounds[0]) + 1
                ))
            else:
                output = [int(v) for v in bounds.split(",")]

            if result.get("@name") == "bestwith":
                best_with = output
            elif result.get("@name") == "recommmendedwith":
                recommended_counts = output
    
    return Game(**{
        # Assume the English title is first index
        "name": content["name"][0]["@value"] if isinstance(content["name"], list) else content["name"]["@value"],
        "id": content["@id"],
        "player_minimum": content['minplayers']["@value"],
        "player_maximum": content['maxplayers']["@value"],
        "player_best": best_with,
        "player_recommended": recommended_counts,
        "complexity": round(float(content["statistics"]["ratings"]["averageweight"]["@value"]), 2)
    })

@authenticated_request
def log_play(gid, plays=1, comment="", BGG_SESSION: Optional[requests.Session] = None):
    if BGG_SESSION is None:
        print("This request must be authenticated!")
        return False
    
    playload = {
        "playdate": datetime.datetime.now().strftime("%Y-%m-%d"),
        "objectid": f"{gid}",
        "objecttype":"thing",
        "action":"save",
        "quantity": f"{plays}",
        "comments": comment
    }

    response = BGG_SESSION.post(
        "https://boardgamegeek.com/geekplay.php", 
        data=json.dumps(playload), 
        headers={'content-type': 'application/json'}
    )

    #Still returns 200 on failure; check if "invalid action" appears in the returned html
    return not "invalid action" in response.text.lower()

if __name__ == '__main__':  
    pass
