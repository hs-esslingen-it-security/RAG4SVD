from abc import ABC, abstractmethod
from private_type import Code

class BaseContextPrompt(ABC):
    @classmethod
    def get_prompt(cls, code:Code):
        pass
