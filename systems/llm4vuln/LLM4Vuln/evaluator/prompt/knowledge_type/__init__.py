from .no_knowledge import NoKnowledgePrompt
from .original_knowledge import OriginalKnowledgePrompt
from .summarized_knowledge import SummarizedKnowledgePrompt
from .__base import BaseKnowledgePrompt
from typing import List, Type

supported:List[Type[BaseKnowledgePrompt]] = [
    # NoKnowledgePrompt,
    # OriginalKnowledgePrompt,
    SummarizedKnowledgePrompt
    # FinetuneKnowledgePrompt
]