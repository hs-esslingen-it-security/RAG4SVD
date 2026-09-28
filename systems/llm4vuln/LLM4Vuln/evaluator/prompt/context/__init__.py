from .with_context import WithContextPrompt
from .without_context import WithoutContextPrompt
from .__base import BaseContextPrompt
from typing import List, Type

supported:List[Type[BaseContextPrompt]] = [
    #WithContextPrompt,
    WithoutContextPrompt
]