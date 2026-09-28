from __future__ import annotations
from typing import Type
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from dataloader.__base import BaseLoader
    from knowledge.__base import BaseKnowledgeLoader

def _init():
    global _global_dict
    _global_dict = {
        "dataloader": {},
        "knowledgeloader": {}
    }

def get_dataloader(name: str) -> Type[BaseLoader]:
    return _global_dict["dataloader"][name]

def register_dataloader(loader: Type[BaseLoader]) -> None:
    _global_dict["dataloader"][loader.language] = loader

def get_knowledgeloader(name: str, search_type:str) -> Type[BaseKnowledgeLoader]:
    return _global_dict["knowledgeloader"][name][search_type]

def register_knowledgeloader(loader: Type[BaseKnowledgeLoader]) -> None:
    if loader.language not in _global_dict["knowledgeloader"]:
        _global_dict["knowledgeloader"][loader.language] = {}
    _global_dict["knowledgeloader"][loader.language][loader.search_type] = loader

