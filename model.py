from typing import Optional, List

class Game:
    name: str
    id: int
    player_minimum: Optional[int]
    player_maximum: Optional[int]
    player_best: Optional[int]
    player_recommended: Optional[List[int]]
    complexity: Optional[float]

    def __init__(self, **kwargs):
        for field in [
            "name", 
            "id", 
            "player_minimum", 
            "player_maximum", 
            "player_best", 
            "player_recommended",
            "complexity"
        ]:
            self.__dict__[field] = kwargs.get(field)

    def __str__(self):
        return f"{self.name} @ {self.id}"

    def __repr__(self): 
        return self.__str__()

class CollectionItem:
    game: Game
    id: int
    comment: Optional[str]

    def __init__(self, **kwargs):
        for field in [
            "id",
            "game",
            "comment"
        ]:
            self.__dict__[field] = kwargs.get(field)
    
    def __str__(self):
        return str(self.game)

    def __repr__(self):
        return repr(self.game)
        
