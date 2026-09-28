from .__base import BaseKnowledgePrompt
from typing import List

class SummarizedKnowledgePrompt(BaseKnowledgePrompt):
    @classmethod
    def get_prompt(cls, retrieved_knowledge:str):

        prompt = f"Now I provide you with a vulnerability knowledge that \"{retrieved_knowledge}\"\n\n Based on this given vulnerability knowledge, please evaluate whether the given is vulnerable. Remember, only report the most confident vulnerability. In your answer, you should at least include three parts: yes or no, type of vulnerability (answer only one most likely vulnerability type if yes), and the reason for your answer."
        return prompt

    @classmethod
    def get_knowledge(cls, code_str:str, language:str) -> List[str]:
        return super().get_knowledge_internal(language, "function", code_str)
