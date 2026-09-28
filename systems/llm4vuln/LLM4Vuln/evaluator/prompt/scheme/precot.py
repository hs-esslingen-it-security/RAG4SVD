from .__base import BaseSchemePrompt

class PreCoTSchemePrompt(BaseSchemePrompt):
    @classmethod
    def get_prompt(cls) -> str:
        prompt = "Note that during your reasoning, you should review the given code step by step and finally determine whether it is vulnerable. For example, you can first summarize the functionality of the given code, then analyze whether there is any error that causes the vulnerability. Lastly, provide me with the result."
        return prompt