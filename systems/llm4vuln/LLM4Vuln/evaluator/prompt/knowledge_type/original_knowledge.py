from .__base import BaseKnowledgePrompt
from typing import List

class OriginalKnowledgePrompt(BaseKnowledgePrompt):
    @classmethod
    def get_prompt(cls, retrieved_knowledge:str):
        
        if len(retrieved_knowledge) > 5000:
            retrieved_knowledge = retrieved_knowledge[:5000]

        prompt = f"Now I provide you with a vulnerability report as follows:\n{retrieved_knowledge}\n\n Based on this given vulnerability report, please evaluate whether the given code is vulnerable. Remember, only report the most confident vulnerability. In your answer, you should at least include three parts: yes or no, type of vulnerability (answer only one most likely vulnerability type if yes), and the reason for your answer."
        return prompt

    @classmethod
    def get_knowledge(cls, code_str:str, language:str) -> List[str]:
        return super().get_knowledge_internal(language, "code", code_str)