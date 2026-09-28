import requests
from rich.progress import track
import rich
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_core.documents import Document
import bs4
from typing import List
import os
from models import gpt_41_nano_model_random
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from threading import Lock
import faiss

console = rich.get_console()
lock = Lock()


def generate_db(title, detail, documents_for_code, documents_for_function):
    title = title.text
    description = detail.select_one("div#Description>div+div").text
    description += " "
    try:
        description += detail.select_one("div#Extended_Description>div+div").text
    except:
        pass
    try:
        examples = detail.select_one("div#Demonstrative_Examples>div+div").text
    except:
        examples = "There is no example code"
    try:
        mitigation = detail.select_one("div#Potential_Mitigations>div+div").text
    except:
        mitigation = "There is no mitigation"
    
    to_save_obj_code = {
        "title": title,
        "description": description,
        "examples": examples,
        "mitigation": mitigation,
        "vul": "Title: " + title + "\n" + "Description: " + description + "\n" + "Potential Mitigation: " + mitigation + "\n" + "Examples: " + examples,
        "summarized": title + description + mitigation
    }

    to_save_obj_function = {
        "title": title,
        "description": description,
        "examples": examples,
        "mitigation": mitigation,
        "vul": "Title: " + title + "\n" + "Description: " + description + "\n" + "Potential Mitigation: " + mitigation + "\n",
        "full": title + description + mitigation + examples
    }

    # documents_for_code.append(Document(page_content = to_save_obj_code["vul"], metadata = to_save_obj_code))
    # documents_for_function.append(Document(page_content = to_save_obj_function["vul"], metadata = to_save_obj_function))

    prompt = f"""CWE: {title}
Description: {description}
Mitigation: {mitigation}


Base on the given CWE information, please help me generate 10 different vulnerable code snippets in Java language. Each code snippet should be different from each other, and trying to cover as many as business logic as possible. You do not need to generate the description of the vulnerabilities, only the code is needed. For each code snippet, please include it in a code block, which starts with "```" and ends with "```". """
    
    retry_counter = 0
    while True:
        try:
            response = gpt_41_nano_model_random.invoke(prompt)
            content = response.content
            split_content = content.split("```")
            temp_code_list = []
            temp_func_list = []
            for i in range(1, 20, 2):
                temp_content = split_content[i]
                if temp_content.startswith("java"):
                    temp_content = temp_content[5:].strip()
                else:
                    temp_content = temp_content.strip()

            
                prompt_report = f"""```java
{temp_content}
```
                
The above code has {title} vulnerability. 

Please help me generate a vulnerability report for it. The report should include the following sections: 1) Vulnerability Description, 2) Vulnerable Code, 3) Root Cause, 4) Impact, 5) Mitigation. Each section should be clearly labeled and contain relevant information. The report should be concise and easy to understand."""
                
                content_report = gpt_41_nano_model_random.invoke(prompt_report).content
                
                to_save_obj_code_append_code = to_save_obj_code.copy()
                to_save_obj_code_append_code["code"] = temp_content
                to_save_obj_code_append_code["report"] = content_report

                temp_code_list.append(Document(page_content = temp_content + "\n\n" + content_report, metadata = to_save_obj_code))

                # Summarize the functionality
                prompt_functionality = temp_content + "\n\n" + content_report + """

Given the following vulnerability description, following the task:
1. Describe the functionality implemented in the given code. This should be answered under the section "Functionality:" and written in the imperative mood, e.g., "Calculate the price of a token." Your response should be concise and limited to one paragraph and within 40-50 words.
2. Remember, do not contain any variable or function or experssion name in the Functionality Result, focus on the functionality or business logic itself."""
                
                content_functionality = gpt_41_nano_model_random.invoke(prompt_functionality).content

                prompt_root_cause = temp_content + "\n\n" + content_report + """
Please provide a comprehensive and clear abstract that identifies the fundamental mechanics behind a specific vulnerability, ensuring that this knowledge can be applied universally to detect similar vulnerabilities across different scenarios. Your abstract should:
    1. Avoid mentioning any moderation tools or systems.
    2. Exclude specific code references, such as function or variable names, while providing a general yet precise technical description.
    3. Use the format: KeyConcept:xxxx, placing the foundational explanation of the vulnerability inside the brackets.
    4. Guarantee that one can understand and identify the vulnerability using only the information from the VulnerableCode and this KeyConcept.
    5. Strive for clarity and precision in your description, rather than brevity.
    6. Break down the vulnerability to its core elements, ensuring all terms are explained and there are no ambiguities.
    By following these guidelines, ensure that your abstract remains general and applicable to various contexts, without relying on specific code samples or detailed case-specific information.
"""
                content_root_cause = gpt_41_nano_model_random.invoke(prompt_root_cause).content

                to_save_obj_function_append_code = to_save_obj_function.copy()
                to_save_obj_function_append_code["code"] = temp_content
                to_save_obj_function_append_code["report"] = content_report
                to_save_obj_function_append_code["functionality"] = content_functionality
                to_save_obj_function_append_code["root_cause"] = content_root_cause

                temp_func_list.append(Document(page_content = content_functionality + "\n\n" + content_root_cause, metadata = to_save_obj_function_append_code))
            
            with lock:
                documents_for_code.extend(temp_code_list)
                documents_for_function.extend(temp_func_list)
            break
        except Exception as e:
            traceback.print_exc()
            retry_counter += 1
            console.log("Error: ", e)
            if retry_counter > 5:
                breakpoint()
            continue


def run():
    db_base_path = "knowledge_db/java"
    CWE_URL = "https://cwe.mitre.org/data/slices/660.html"
    response = requests.get(CWE_URL)
    soup = bs4.BeautifulSoup(response.text, "html.parser")
    cwe_titles = soup.find_all("div", {"style":"overflow:auto;"})[1:]
    cwe_details = soup.find_all("div", {"xmlns:xhtml":"http://www.w3.org/1999/xhtml", "id": "CWEDefinition", "class": "Weakness"})

    # key is the title + description + examples
    documents_for_code:List[Document] = []
    # key is the description
    documents_for_function:List[Document] = []
    
    with ThreadPoolExecutor(max_workers=32) as executor:
        futures:List[Future] = []
        for title, detail in track(zip(cwe_titles, cwe_details), total=len(cwe_titles), console=console, description="Generating tasks..."):
            future = executor.submit(generate_db, title, detail, documents_for_code, documents_for_function)
            futures.append(future)
        
        for future in track(as_completed(futures), total=len(futures), console=console, description="Processing..."):
            try:
                future.result()
            except Exception as e:
                traceback.print_exc()
                console.log("Error: ", e)
                continue

    
    console.log("Total documents for code: ", len(documents_for_code))
    embeddings = OpenAIEmbeddings()

    db_for_code = FAISS(
        embedding_function=embeddings,
        index=faiss.IndexFlatL2(len(embeddings.embed_query(documents_for_code[0].page_content))),
        docstore=InMemoryDocstore(),
        index_to_docstore_id={},
    )
    # embed every 100 documents to the db
    for i in range(0, len(documents_for_code), 100):
        db_for_code.add_documents(documents_for_code[i:i+100])
        console.log("Added documents: ", i, " to ", i+100)
    db_for_code.save_local(os.path.join(db_base_path, "code"))

    # Same for db_for_function
    db_for_function = FAISS(
        embedding_function=embeddings,
        index=faiss.IndexFlatL2(len(embeddings.embed_query(documents_for_function[0].page_content))),
        docstore=InMemoryDocstore(),
        index_to_docstore_id={},
    ) 
    for i in range(0, len(documents_for_function), 100):
        db_for_function.add_documents(documents_for_function[i:i+100])
        console.log("Added documents: ", i, " to ", i+100)
    db_for_function.save_local(os.path.join(db_base_path, "function"))

