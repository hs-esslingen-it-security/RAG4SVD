from abc import ABC, abstractmethod
from typing import List

class BaseKnowledgePrompt(ABC):
    @classmethod
    def get_prompt(cls, retrieved_knowledge:str):
        pass

    @classmethod
    def get_knowledge(cls, code_str:str, language:str) -> List[str]:
        pass
    
    @classmethod
    def get_knowledge_internal(cls, language:str, search_type:str, code_str:str) -> List[str]:
        import registry
        knowledge_loader = registry.get_knowledgeloader(language, search_type)
        return knowledge_loader().search(code_str)

