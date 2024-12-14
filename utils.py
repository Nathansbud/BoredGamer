import os

CYAN = "\033[36;1m"
YELLOW = "\33[33;1m"
GREEN = "\033[32;1m"
RED = "\033[31;1m"
DEFAULT = "\033[0m"

cache_path = os.path.join(os.path.dirname(__file__), "cache.json")
creds_path = os.path.join(os.path.dirname(__file__), "credentials", "bgg.json")
