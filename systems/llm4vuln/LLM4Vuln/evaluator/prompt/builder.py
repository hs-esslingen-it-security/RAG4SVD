from . import context
from . import knowledge_type
from . import scheme
from private_type import Code
from typing import List, Tuple
from .knowledge_type.no_knowledge import NoKnowledgePrompt


class PromptCombination:
    def __init__(self, scheme_prompt:str, knowledge_prompt:str, context_prompt:str) -> None:
        self.scheme_prompt = scheme_prompt
        self.knowledge_prompt = knowledge_prompt
        self.context_prompt = context_prompt

    def to_tuple(self) -> Tuple[str,str,str]:
        return (self.scheme_prompt, self.knowledge_prompt, self.context_prompt)
    
    def to_list(self) -> List[str]:
        return [self.scheme_prompt, self.knowledge_prompt, self.context_prompt]
    
    def __eq__(self, value: object) -> bool:
        return self.scheme_prompt == value.scheme_prompt and self.knowledge_prompt == value.knowledge_prompt and self.context_prompt == value.context_prompt

    def __hash__(self) -> int:
        return hash((self.scheme_prompt, self.knowledge_prompt, self.context_prompt))

class PromptBuilder:
    @classmethod
    def build_all(cls, language:str, code:Code) -> List[Tuple[str,PromptCombination]]:
        result = []

        for scheme_prompt_class in scheme.supported:
            for knowledge_type_prompt_class in knowledge_type.supported:
                for context_prompt_class in context.supported:
                    # first, get all the code
                    code_str = context_prompt_class.get_prompt(code)
                    # then, search the code with the knowledge loader
                    for retrieved_knowledge in knowledge_type_prompt_class.get_knowledge(code_str, language):
                        # concat the prompt
                        final_prompt = knowledge_type_prompt_class.get_prompt(retrieved_knowledge) + " " + scheme_prompt_class.get_prompt() + "\n\n" + code_str
                        result.append((final_prompt, PromptCombination(scheme_prompt_class.__name__, knowledge_type_prompt_class.__name__, context_prompt_class.__name__)))
                        # if knowledge_type_prompt_class == NoKnowledgePrompt:
                        #     # Add two more same prompts
                        #     result.append((final_prompt, PromptCombination(scheme_prompt_class.__name__, knowledge_type_prompt_class.__name__, context_prompt_class.__name__)))
                        #     result.append((final_prompt, PromptCombination(scheme_prompt_class.__name__, knowledge_type_prompt_class.__name__, context_prompt_class.__name__)))

        return result
