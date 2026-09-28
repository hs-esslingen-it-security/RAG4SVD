from langchain_community.llms.replicate import Replicate
from config import seed

phi3_mini_model = Replicate(
    model = "microsoft/phi-3-mini-128k-instruct:45ba1bd0a3cf3d5254becd00d937c4ba0c01b13fa1830818f483a76aa844205e",
    model_kwargs={"temperature": 0.1, "seed": seed}
)

llama_3_model = Replicate(
    model = "meta/meta-llama-3-8b-instruct",
    model_kwargs={"temperature": 0, "seed": seed}
)

codellama_13b_model = Replicate(
    model = "meta/codellama-13b-instruct:a5e2d67630195a09b96932f5fa541fe64069c97d40cd0b69cdd91919987d0e7f"
)

codellama_70b_model = Replicate(
    model = "meta/codellama-70b-instruct:a279116fe47a0f65701a8817188601e2fe8f4b9e04a518789655ea7b995851bf"
)

qwq_model = Replicate(
    model = "lucataco/qwq-32b:5a9425923f3ef1101dc663609a80cbd597dea6554a6b0c06483b949cb72603ed",
    model_kwargs={"temperature": 0.1, "seed": seed}
)

deepseek_model = Replicate(
    model = "deepseek-ai/deepseek-r1",
    model_kwargs={"temperature": 0.1, "seed": seed}
)

