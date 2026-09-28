from abc import ABC, abstractmethod
from typing import List
import os
from registry import register_knowledgeloader
#from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
#from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from config import KNOWLEDGE_K
import models.utils_model as MODELS_UTILS


class BaseKnowledgeLoader(ABC):
    language = "Unknown"
    search_type = "Unknown"

    def __init__(self) -> None:
        emb =  MODELS_UTILS.get_EMBEDDING_MODEL()
        # database path dependent on embedding model
        self.knowledge_db_path = os.path.join("knowledge_db", self.language, self.search_type, "faiss_"+emb.model_name.split("/")[-1])

        assert os.path.exists(self.knowledge_db_path), f"Knowledge database not found at {self.knowledge_db_path}"
        self.db = FAISS.load_local(self.knowledge_db_path, emb, allow_dangerous_deserialization=True)

    def search(self, query:str) -> List[str]:
        docs = self.db.similarity_search(query, k=KNOWLEDGE_K)
        return [doc.metadata["vul"] if len(doc.metadata["vul"].split(" ")) < 1500 else " ".join(doc.metadata["vul"].split(" ")[:1500]) for doc in docs]

    def __init_subclass__(cls) -> None:
        register_knowledgeloader(cls)
        return super().__init_subclass__()

    
