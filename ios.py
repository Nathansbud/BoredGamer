from sys import platform
import link

try:
    import dialogs
except ImportError:
    pass

def choose_title():
    if platform != 'ios': 
        raise RuntimeError("Cannot run choose_title on a non-iOS device!")
    
    sections = [
        {"title":"Game: ", "type": "text", "key":"game"},
        {"title":"Plays: ", "type":"number", "key":"plays", "value": "1"}
    ]
    
    choices = dialogs.form_dialog("Game Played", fields=sections) or {}
    
    try:
        plays = int(choices.get('plays', 0))
        game = choices.get('game')
        if game and plays > 0:
            game_options = link.get_games(game)
            if game_options:
                selected = dialogs.list_dialog("Choose Title", [f'{g["name"]} ({g["year"]}) - {g["idx"]}' for g in game_options])		
                if selected: 
                    idx = selected.split('-')[-1]
                    link.log_play(idx, plays)			
                    dialogs.alert("Add Success", f"Added {str(plays) + ' plays' if plays != 1 else str(plays) + ' play'} to {game}", "Close", hide_cancel_button=True)
            else:
                dialogs.alert(f"No entries found for {game} on BoardGameGeek!")
    except ValueError:
        dialogs.alert("Play count must be a number!")

if __name__ == "__main__":
    choose_title()
