import argparse
import json
import webbrowser

from sys import platform
from enum import Enum

from simple_term_menu import TerminalMenu

import link, tags
from utils import *

selected = None

class Reversor:
    def __init__(self, value): self.value =value
    def __eq__(self, oth): return oth.value == self.value
    def __lt__(self, oth): return oth.value < self.value

class CollectionUpdate(Enum):
    MARK_LOANED = "Mark Loaned"
    MARK_RETURNED = "Mark Returned"
    MARK_AUDIT = "Mark Audit"
    MARK_GIVEAWAY = "Mark Giveaway"
    MARK_KEEP = "Mark Keep"
    CLEAR_TAGS = "Clear Tags"

L_CollectionUpdate = list(CollectionUpdate)
V_CollectionUpdate = [v.value for v in L_CollectionUpdate]

if __name__ == '__main__':
    try:
        try: 
            with open(cache_path, 'r') as cf: 
                cache = json.load(cf)
        except FileNotFoundError:
            cache = {}

        parser = argparse.ArgumentParser(
            prog='bgg', 
            description="Various utilities for BoardGameGeek logging",
            allow_abbrev=True, 
        )

        mutex = parser.add_mutually_exclusive_group()
        mutex.add_argument('-a', '--add', nargs='+', metavar=('title', '?plays'), help="add plays by title")
        mutex.add_argument('-s', '--summary', nargs='*', metavar=('?days', '?filter'), const=None, help='get game summary for last # of days (or full history if omitted)')
        mutex.add_argument('-l', '--login', action='store_true', help="login to a BoardGameGeek account")
        mutex.add_argument('-o', '--open', action='store_true', help='open logged in BoardGameGeek account')
        mutex.add_argument('-r', '--reset-cache', action='store_true', help="reset stored search cache information")

        mutex.add_argument('--collection', action="store_true", help="interface with user collection")
        mutex.add_argument('--lookup', nargs=1, help="lookup user collection")

        parser.add_argument('-n', '--nocache', action='store_true', help='ignore cache')
        parser.add_argument('-m', '--sortmode', default='plays', const='plays', nargs='?', choices=['title', 'plays'], help='mode to sort summary by')
        parser.add_argument('-c', '--comment', nargs='?', help='play comment')
        parser.add_argument('-w', '--wishlist', action='store_true', help='add to wishlist')
        parser.add_argument('--filters', nargs=1, help="filters for collection")

        args = vars(parser.parse_args())
        
        add, summary, lookup, s_wishlist = (
            args.get(v) for v in ['add', 'summary', 'lookup', 'wishlist']
        )

        filters = [v for v in (args.get("filters") or [''])[0].split(",") if v]
        
        no_args = True
        if args.get('reset_cache'): 
            no_args = False
            try: 
                print("Clearing stored play cache!")
                os.remove(cache_path)
            except OSError as e:
                pass

        if args.get('login'):
            link.login()
        elif add is not None:
            default = True
            plays = 1
            if len(add) == 2:
                try:
                    plays = int(add[1])
                    if plays < 1: raise ValueError
                except ValueError:
                    parser.error("Add argument must be a positive number (preferably an integer)!")
                finally: 
                    default = False
            
            use_cache = not args.get('nocache')
            title = add[0].lower()
            game_options = link.get_games(title)
            if use_cache and title in cache and cache[title]['count'] >= 3:
                selected = cache[title]
            else:
                if not game_options:
                    print("No items found!")
                else:
                    game_items = [f'{game["name"]} ({game["year"]}) - ID: {game["idx"]}' for game in game_options]
                    sidx = TerminalMenu(game_items, menu_highlight_style=("bg_cyan", "fg_black")).show()
                    selected = game_options[sidx] if isinstance(sidx, int) else None

            if s_wishlist:
                plays = 4 if default else min(plays, max(plays, 1), 5)
                link.wishlist_game(selected['idx'], selected['name'], priority=plays)
            elif selected is not None:
                print(f"Adding {CYAN}{plays} {'plays' if plays > 1 else 'play'}{DEFAULT} to {YELLOW}{selected['name']} ({selected['year']}){DEFAULT}...")
                try:
                    res = link.log_play(selected['idx'], plays=plays, comment=args.get('comment'))
                    if res == 200:
                        print(f"{GREEN}{'Plays added!' if plays > 1 else 'Play added!'}{DEFAULT}")
                    else:
                        if res == 401:
                            print(f"{RED}Incorrect credentials for currently logged in account{DEFAULT}. Try logging in with {YELLOW}bgg -l{DEFAULT}!")
                        else:
                            print(f"{RED}Play adding failed for unknown reasons!{DEFAULT}")
                        
                        exit(1)

                    if not title in cache or cache[title]['idx'] != selected['idx']:
                        cache[title] = {'count': 1, 'idx': selected['idx'], 'name': selected['name'], 'year': selected['year']}
                    else:
                        cache[title]['count'] += 1

                    with open(cache_path, 'w+') as cf:
                        json.dump(cache, cf)
                except Exception as e:
                    print(e)
                    print(f"{RED}Play adding failed!{DEFAULT}")
        
        elif summary is not None:
            days = 0
            filter_on = "".join(summary[1:]) if len(summary) > 1 else ""
            if len(summary) > 0 and summary[0] != '.':
                try:
                    days = int(summary[0])
                except ValueError:
                    print("Summary must have a number or . as its first argument!")
                    exit(1) 

            play_data = link.get_plays(None if days < 1 else days)
            if play_data:
                game_data = {}
                for play in play_data:
                    if play['name'] in game_data: game_data[play['name']] += play['plays']
                    else: game_data[play['name']] = play['plays']

                game_sorter = lambda gd: gd
                if args.get('sortmode') == 'plays':
                    game_sorter = lambda gd: (Reversor(gd[1]), gd[0] if not gd[0].lower().startswith("the ") else gd[0][4:])
                elif args.get('sortmode') == 'title': 
                    game_sorter = lambda gd: (gd[0] if not gd[0].lower().startswith("the ") else gd[0][4:])

                summary_set = [gd for gd in sorted(game_data.items(), key=game_sorter) if filter_on.lower() in gd[0].lower()]
            
                if not summary_set: 
                    print(f"{RED}No games found matching filter condition '{filter_on}'!{DEFAULT}")
                else: 
                    for game, plays in summary_set:
                        print(f"- {YELLOW}{game}{DEFAULT}: {CYAN}{plays}{DEFAULT}")
            else:
                print(f"{RED}No plays logged{' in that timespan' if summary < 1 else ''}!{DEFAULT}")
        elif args.get("collection"):
            user = link.get_user()
            _owned, _wishlist = link.get_collection(user)
            owned = [
                o for o in _owned if len(filters) == 0 or
                (o.comment and all(f in o.comment for f in filters))
            ]
            
            if not owned: 
                print(f"No items in the collection satisfies all applied filters: {filters}")
            else:
                selected = True
                while selected is not None:
                    sidx = TerminalMenu(
                        (o.game.name for o in owned), 
                        menu_highlight_style=("bg_cyan", "fg_black"),
                        title=f"{user} – Collection"
                    ).show()

                    selected = owned[sidx] if isinstance(sidx, int) else None
                    if selected is not None:
                        ssidx = TerminalMenu(
                            V_CollectionUpdate, 
                            menu_highlight_style=("bg_cyan", "fg_black"),
                            title=f"{selected.game.name} {selected.comment or ''}"
                        ).show()
                        
                        subselected = L_CollectionUpdate[ssidx] if isinstance(ssidx, int) else None
                        if subselected is CollectionUpdate.MARK_LOANED:
                            response = input("Loaned to: ").strip()
                            if not response: continue

                            output = tags.modify_tags(
                                selected,
                                {tags.TagType.LOANED: response}
                            )

                            selected.comment = output
                            link.update_comment(selected.id, selected.game.id, output)
                        elif subselected is CollectionUpdate.MARK_RETURNED:
                            output = tags.modify_tags(
                                selected,
                                {tags.TagType.LOANED: False} 
                            )

                            selected.comment = output
                            link.update_comment(selected.id, selected.game.id, output)
                        elif subselected in [
                            CollectionUpdate.MARK_AUDIT,
                            CollectionUpdate.MARK_GIVEAWAY,
                            CollectionUpdate.MARK_KEEP
                        ]:
                            audit_value = "Giveaway" if subselected == CollectionUpdate.MARK_GIVEAWAY else (
                                subselected == CollectionUpdate.MARK_AUDIT
                            )

                            output = tags.modify_tags(
                                selected, 
                                {tags.TagType.AUDIT: audit_value}
                            )
                            
                            selected.comment = output
                            link.update_comment(selected.id, selected.game.id, output)
                        elif subselected is CollectionUpdate.MARK_GIVEAWAY:
                            output = tags.modify_tags(
                                selected, 
                                {tags.TagType.AUDIT: "Giveaway"}
                            )
                            
                            selected.comment = output
                            link.update_comment(selected.id, selected.game.id, output)
                        elif subselected is CollectionUpdate.CLEAR_TAGS:
                            selected.comment = ""
                            link.update_comment(
                                selected.id, selected.game.id,
                                {k: False for k in tags.parse_tags(selected.comment)}
                            )
                        elif subselected is not None:
                            print(f"No action has been implemented for: {subselected}")
        elif lookup is not None:
            _owned, _wishlist = link.get_collection(lookup[0])
            owned = [
                o for o in _owned if len(filters) == 0 or
                (o.comment and all(f in o.comment for f in filters))
            ]

            for o in owned:
                print(f"- {o.game.name}")

        elif args.get('open'):
            user = link.get_user()
            webbrowser.open(f'https://boardgamegeek.com/collection/user/{user}')               
        elif no_args:
            parser.print_help()
    except KeyboardInterrupt:
        pass
