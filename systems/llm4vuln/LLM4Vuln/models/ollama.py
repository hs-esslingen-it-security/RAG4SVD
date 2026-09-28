from langchain_ollama import ChatOllama
from config import seed

qwq_model = ChatOllama(
    model="qwq:32b",
    temperature=0.1,
    num_cxt=40960,
    base_url="http://localhost:6060",
    seed=seed
)

deepseek_model = ChatOllama(
    model="deepseek-r1:70b",
    temperature=0.1,
    num_cxt=131072,
    base_url="http://localhost:6060",
)
