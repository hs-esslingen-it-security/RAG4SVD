from .__base import BaseContextPrompt
from private_type import Code

class WithoutContextPrompt(BaseContextPrompt):
    @classmethod
    def get_prompt(cls, code:Code):
        return code.get_str()