from .__base import BaseKnowledgePrompt
from typing import List

class NoKnowledgePrompt(BaseKnowledgePrompt):
    @classmethod
    def get_prompt(cls, retrieved_knowledge:str):
        prompt = "As a large language model, you have been trained with extensive knowledge of vulnerabilities. Based on this past knowledge, please evaluate whether the given code is vulnerable. Remember, only report the most confident vulnerability. In your answer, you should at least include three parts: yes or no, type of vulnerability (answer only one most likely vulnerability type if yes), and the reason for your answer."
        return prompt
    
    @classmethod
    def get_knowledge(cls, code_str:str, language:str) -> List[str]:
        return [""]
