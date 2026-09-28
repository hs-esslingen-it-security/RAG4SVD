from .__base import BaseContextPrompt
from private_type import Code

class WithContextPrompt(BaseContextPrompt):
    @classmethod
    def get_prompt(cls, code:Code):
        return code.get_all_str()