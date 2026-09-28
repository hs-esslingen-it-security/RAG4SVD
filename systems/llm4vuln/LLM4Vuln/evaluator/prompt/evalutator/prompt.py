from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables.base import RunnableSerializable
from langchain_core.runnables import RunnableLambda
from langchain_core.language_models.llms import LLM
from pydantic.v1 import BaseModel, Field
import re
#from langchain.pydantic_v1 import BaseModel, Field
from typing import Dict, Any

def build_prompt_ask_whether_has_vuln_str(prompt:str, model:LLM) -> RunnableSerializable[Dict, Any]:
    prompt = prompt.replace("{", "{{").replace("}", "}}")
    prompt_template = PromptTemplate(
        template=prompt
    )

    parser = StrOutputParser()

    return prompt_template | model | parser


def transfer_whether_has_vuln_str_to_structure(answer:str, model:LLM) -> RunnableSerializable[Dict, Any]:
    class AskWhetherHasVuln(BaseModel):
        has_vuln: bool = Field(description="Whether the code has vulnerability")
        vuln_type: str = Field(description="A sentence to describe the type of vulnerability")
    prompt = "The given text is a description of the scanner result of a code segment. Please generate structured result from the following string: \n" + answer
    prompt = prompt.replace("{", "{{").replace("}", "}}")
    parser = JsonOutputParser(pydantic_object=AskWhetherHasVuln)
    prompt_template = PromptTemplate(
        template=prompt + " {format_instructions}",
        partial_variables={
            "format_instructions": parser.get_format_instructions()}
    )

    return prompt_template | model | parser




def build_prompt_check_gt(given_type:str, gt:str, model:LLM) -> RunnableSerializable[Dict, Any]:
    class CheckGT(BaseModel):
        is_gt: bool = Field(description="Whether the given vulnerability type is consistant with the ground truth")

    prompt = f"Given the vulnerability type \"{given_type}\", is it consistent with the ground truth:\n {gt}?"

    prompt = prompt.replace("{", "{{").replace("}", "}}")

    parser = JsonOutputParser(pydantic_object=CheckGT)
    prompt_template = PromptTemplate(
        template=prompt + " {format_instructions}",
        partial_variables={
            "format_instructions": parser.get_format_instructions()}
    )

    return prompt_template | model | parser
