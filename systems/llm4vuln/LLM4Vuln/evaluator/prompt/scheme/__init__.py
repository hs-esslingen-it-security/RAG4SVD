from .raw import RawSchemePrompt
from .precot import PreCoTSchemePrompt
# from .postcot import PostCoTSchemePrompt
from .__base import BaseSchemePrompt
from typing import List, Type

supported:List[Type[BaseSchemePrompt]] = [
    #RawSchemePrompt,
    PreCoTSchemePrompt
    # PostCoTSchemePrompt
]