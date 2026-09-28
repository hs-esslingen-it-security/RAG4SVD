from ..__base import BaseKnowledgeLoader
from typing import List
#from langchain_openai import ChatOpenAI
#from langchain_core.pydantic_v1 import BaseModel, Field
from pydantic.v1 import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
import re
from langchain_core.runnables import RunnableLambda
from config import KNOWLEDGE_K
# from models import gpt_41_nano_model
import models.utils_model as MODELS_UTILS
import json

def clean_llm_response(text: str) -> str:
    if not text:
        return ""

    # remove <think>...</think> blocks (DeepSeek style)
    # re.DOTALL makes . match newlines
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

    # remove Markdown code blocks (e.g., ```json ... ```)
    code_blocks = re.findall(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if code_blocks:
        text = code_blocks[-1].strip()
    
    ## too aggressive parsing for open-weights
    # # locate the first '{' and the last '}' to extract raw JSON
    # start = text.find('{')
    # end = text.rfind('}')
    
    # if start != -1 and end != -1:
    #     text = text[start : end + 1]

    return text.strip()


class JavaKnowledgeLoader(BaseKnowledgeLoader):
    language = "java"
    search_type = "code"

class JavaFunctionKnowledgeLoader(BaseKnowledgeLoader):
    language = "java"
    search_type = "function"

    def search(self, query: str) -> List[str]:
        function_query = self.__generate_functionality(query)

        # If summarization failed completely, fallback to the raw query (code)
        # This prevents the 'None.replace' crash in the vector store
        if not function_query:
            print("Warning: Summarization failed. Falling back to raw code query.")
            function_query = query 

        docs = self.db.similarity_search(function_query, k=KNOWLEDGE_K)
        return [doc.metadata["description"] for doc in docs]


    def __generate_functionality(self, query: str) -> str:
        model = MODELS_UTILS.get_SUMMARY_MODEL() # gpt_41_nano_model # SUMMARY MODEL
        parser = JsonOutputParser(pydantic_object=self.__FunctionSummarization)
        prompt_template = PromptTemplate(
            template="You are a Java program auditing expert. I have a database of vulnerability knowledge. However, you cannot read all the database since it is too large. You are asked to summarize the given code into less than three sentence, and I will help you search in the vector database. The summarization should be short and clear. The code is as follows:\n\n {code} \n\nSummarize the code into a sentence: {format_instructions}",
            input_variables=["code"],
            partial_variables={
                "format_instructions": parser.get_format_instructions()}
        )

        chain = prompt_template | model # | parser
        
        # transform while true to max_retries
        MAX_RETRIES = 3
        for attempt in range(MAX_RETRIES):
            try:
                raw_response = chain.invoke({"code": query})
                cleaned_response = clean_llm_response(raw_response if isinstance(raw_response, str) else raw_response.content)
                
                try:
                    _res = json.loads(cleaned_response)
                    
                    # Look for 'functionality', but accept 'summary' or 'description'
                    functionality = _res.get('functionality') or \
                                    _res.get('summary') or \
                                    _res.get('description') or \
                                    _res.get('output')
                                    
                    # If it returned a dict but none of those keys, convert the whole dict to string
                    if not functionality:
                        functionality = str(_res)

                #res = self.__FunctionSummarization(**_res)
                #functionality = res.functionality

                except json.JSONDecodeError:
                    # If it wasn't JSON, just use the raw text
                    functionality = cleaned_response
                

                # Normalize all outputs to string
                if isinstance(functionality, list):
                    functionality = " ".join(str(x) for x in functionality)
                elif isinstance(functionality, dict):
                    functionality = json.dumps(functionality)
                elif functionality is None:
                    functionality = ""
                else:
                    functionality = str(functionality)

                functionality = functionality.strip()
                if not functionality: 
                    return "Code snippet"
                
                tokens = functionality.split()
                if len(tokens) > 2000:
                    functionality = " ".join(tokens[:2000])

                return functionality

            except Exception as e:
                print(f"Functionality summarization failed (Attempt {attempt+1}/{MAX_RETRIES}): {e}")

        print("Warning: Summarization failed. Falling back to raw code query.")
        return query


    class __FunctionSummarization(BaseModel):
        functionality: str = Field(
            description="The summarized functionality of the function")
