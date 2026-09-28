from models.openai import gpt_4_turbo_model, gpt_41_nano_model
from langchain_core.output_parsers import StrOutputParser
import json
import os
from rich import get_console
from rich.progress import track
import re

console = get_console()

def process_code(input_code:str)->str:
    prompt = f"""{input_code}\n\nI need to do data augments for the above code for vulnerability detection. Please help me to do the following things on the given code:

1. Change the variable names to new names that have similar semantics.
2. Change the comments, but also keep the semantics.
3. Do not include words that hint the given code is vulnerable or not, such as "bug". """
    parser = StrOutputParser()

    chain = gpt_41_nano_model | parser
    response = chain.invoke(prompt)
    # process response, the code should be in markdown format
    pattern = "```(cpp|c++|c)\\s+([\\s\\S]+)\\s+```"
    # breakpoint()
    code = re.search(pattern, response).group(1)
    return code

def run():
    for file in track(os.listdir("dataset/java"), description="Processing Java dataset."):
        if file.endswith(".json"):
            with open(f"dataset/cpp/{file}", "r") as f:
                data = json.load(f)
            # process all the code segs

            data["code_before_patch"]["code"] = process_code(data["code_before_patch"]["code"])
            data["code_after_patch"]["code"] = process_code(data["code_after_patch"]["code"])

            # dump the data back
            with open(f"dataset/cpp/{file}", "w") as f:
                json.dump(data, f, indent=4)
    

