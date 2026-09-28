from abc import ABC, abstractmethod
from private_type import Code

class BaseSchemePrompt(ABC):
    @classmethod
    def get_prompt(cls) -> str:
        pass
