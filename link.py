import datetime
import json
import os
import re
import time

import requests
import xmltodict

from typing import Optional, Union, Dict
from urllib.parse import quote
from getpass import getpass

from utils import *
from model import Game, CollectionItem, WishlistMetadata


# Docs: https://boardgamegeek.com/wiki/page/BGG_XML_API2
bgg_api = "https://api.geekdo.com/xmlapi2"

def authenticated_request(method):
    def authenticated_function(*args, **kwargs):
        with requests.Session() as session, open(creds_path) as jf:
            session.post('https://boardgamegeek.com/login/api/v1', data=json.dumps({
                "credentials": json.load(jf)
            }), headers={'content-type': 'application/json'})

            return method(*args, BGG_SESSION=session, **kwargs)

    return authenticated_function

def get_user():
    try: 
        with open(creds_path) as jf: 
            return json.load(jf).get("username")
    except FileNotFoundError:
        return login().get("username")

def login():
    os.makedirs(os.path.join(os.path.dirname(__file__), "credentials"), exist_ok=True)
    username = input(f"Enter your BoardGameGeek {CYAN}username{DEFAULT}: ")
    password = getpass(f"Enter your BoardGameGeek {GREEN}password{DEFAULT}: ")
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
        model = CollectionItem(
            id=int(item["@collid"]),
            comment=item.get("comment"),
            game=Game(name=item["name"]["#text"], id=item["@objectid"])
        )

        # These are technically not mutually exclusive categories for BGG, but treating as if they are. This will
        # break things in the exceedingly rare case where a game is both owned AND wishlisted...oh well
        if item["status"]["@own"] == "1":
            model.owned = True
            owned.append(model)
        elif item["status"]["@wishlist"] == "1":
            model.owned = False
            model.wishlist = WishlistMetadata(
                priority=int(item["status"].get("@wishlistpriority", 0)),
                comment=item.get("wishlistcomment")
            )
            
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
def wishlist_game(gid: int, name: str, priority: int, comment: Optional[str] = None, BGG_SESSION: Optional[requests.Session] = None):
    request_body = {"item": {
        "collid": 0,
        "pp_currency": "USD",
        "cv_currency": "USD",
        "objecttype": "thing",
        "objectid": f"{gid}",
        "objectname": name,
        "status": { "wishlist": True },
        "wishlistpriority": priority,
        "acquisitiondate": None,
        "invdate": None
    }}

    if comment:
        request_body["item"]["textfield"] = {"wishlistcomment": {"value": comment}}

    BGG_SESSION.post(
        "https://boardgamegeek.com/api/collectionitems",
        data=json.dumps(request_body),
        headers={'content-type': 'application/json'}
    )

@authenticated_request
def update_status(
    cid: int, 
    gid: int,
    owned: bool,
    prev_owned: bool = False,
    wishlist_status: Optional[int] = None, 
    BGG_SESSION: Optional[requests.Session] = None
):
    request_body = {
        "fieldname": "status",
        "collid": cid,
        "objecttype": "thing",
        "objectid": gid,
        "own": 1 if owned else 0,
        "prev_owned": 1 if prev_owned else 0,
        "wishlist": 1 if wishlist_status is not None else 0,
        "wishlistpriority": wishlist_status if wishlist_status is not None else 1,
        "ajax": 1,
        "action": "savedata",
    }

    BGG_SESSION.post(
        "https://boardgamegeek.com/geekcollection.php",
        data=request_body,
        headers={'content-type': 'application/x-www-form-urlencoded'}
    )

@authenticated_request
def delete_item(cid: int, BGG_SESSION: Optional[requests.Session] = None):
    request_body = {
        "collid": cid,
        "ajax": 1,
        "action": "delete",
    }

    BGG_SESSION.post(
        "https://boardgamegeek.com/geekcollection.php",
        data=request_body,
        headers={'content-type': 'application/x-www-form-urlencoded'}
    )

@authenticated_request
def update_comment(
    cid: int, 
    gid: int, 
    comment: str="", 
    wishlist: bool=False, 
    BGG_SESSION: Optional[requests.Session] = None
):    
    request_body = {
        "fieldname": "comment" if not wishlist else "wishlistcomment",
        "collid": cid,
        "objecttype": "thing",
        "objectid": gid,
        "value": comment,
        "ajax": 1,
        "action": "savedata",
    }

    BGG_SESSION.post(
        "https://boardgamegeek.com/geekcollection.php",
        data=request_body,
        headers={'content-type': 'application/x-www-form-urlencoded'}
    )

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

    res_text = response.text.lower()

    if "you must login to save plays" in res_text:
        return 401
    elif not "invalid action" in res_text: 
        return 200
    else:
        return 400

if __name__ == '__main__':  
    pass
