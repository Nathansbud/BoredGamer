# The motivation behind tags is using a structured approach to the BGG comment field to track additional,
# to do things like manage loaned games, track games that should be audited, and more.

# Tags can act either as flags or as values, and a single collection item can have multiple active tags, though
# each tag is unique (i.e. it wouldn't make sense for a game to be loaned to multiple people)

# The structure of a tag is one of: [Tag] | [Tag: Value]

import re
from typing import Dict, Optional, Union
from enum import Enum

from model import CollectionItem

class TagType(Enum):
    LOANED = "Loaned"
    AUDIT = "Audit"

def modify_tags(coll_item: CollectionItem, tags: Dict[Union[TagType, str], str]):
    existing_tags = parse_tags(coll_item.comment)
    for t, v in tags.items():
        existing_tags[t] = v

    out_str = ""
    for tag, value in existing_tags.items():
        out_tag = tag.value if isinstance(tag, TagType) else tag
        if isinstance(value, str):
            out_str += f"[{out_tag}: {value}]"
        elif value:
            out_str += f"[{out_tag}]"

    return out_str

def try_map(tag_str: str) -> Union[TagType, str]:
    entries = {entry.value: entry for entry in list(TagType)}
    return entries.get(tag_str, tag_str)

def parse_tags(s: Optional[str]):
    if not s: return {}
    
    raw_tags = [tag.split(":") for tag in re.findall("\[(.*?)\]", s)]
    
    output_tags = {}
    for t in raw_tags:
        tag_name = try_map(t[0])
        if len(t) == 1: 
            output_tags[tag_name] = True
        else:
            output_tags[tag_name] = t[1].strip()
    
    return output_tags
