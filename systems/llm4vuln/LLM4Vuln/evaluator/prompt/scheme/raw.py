from .__base import BaseSchemePrompt

class RawSchemePrompt(BaseSchemePrompt):
    @classmethod
    def get_prompt(cls) -> str:
        prompt = ""
        return prompt