from langchain_openai import ChatOpenAI
from config import seed, OPEN_ROUTER_API_KEY

gpt_4_turbo_model = ChatOpenAI(
    model = "gpt-4-turbo",
    temperature=0,
    seed=seed
)

gpt_35_turbo_model = ChatOpenAI(
    model = "gpt-3.5-turbo",
    temperature=0,
    seed=seed
)

gpt_41_nano_model = ChatOpenAI(
    model = "gpt-4.1-nano",
    temperature=0,
    seed=seed,
)

gpt_41_nano_model_random = ChatOpenAI(
    model = "gpt-4.1-nano"
)

qwq_model = ChatOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPEN_ROUTER_API_KEY,
    model="qwen/qwq-32b",
    temperature=0.1,
    seed=seed,
)

deepseek_model = ChatOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPEN_ROUTER_API_KEY,
    model="deepseek/deepseek-r1",
    temperature=0.1,
    seed=seed,
)

gpt_o4_mini = ChatOpenAI(
    model = "o4-mini",
    # temperature=0,
    seed=seed,
)

gpt_41 = ChatOpenAI(
    model = "gpt-4.1",
    temperature=0,
    seed=seed,
)