import json
import csv
from rich.progress import track
import subprocess
import os
import git
from typing import Tuple, List, Dict, Set
import requests
import bs4
import traceback
from rich import get_console

console = get_console()

BASE_PROJECT_PATH = "/home1/XXXX-1/XXXX-4"

def checks():
    check_submodule()
    check_compile()

def check_submodule():
    if os.path.exists(os.path.join("ext", "cg_llm4vuln")):
        return
    else:
        raise Exception("Submodule cg_llm4vuln not found")

def check_compile(again=False):
    if os.path.exists(os.path.join("ext", "cg_llm4vuln", "build", "libs", "cg_llm4vuln-1.0-SNAPSHOT.jar")):
        return
    else:
        if again:
            raise Exception("Failed to compile java-callgraph. Please check the error message.")
        else:
            compile_java_cg()
            check_compile(again=True)

def compile_java_cg():
    subprocess.run(["./gradlew", "build", "--stacktrace"], cwd="./ext/cg_llm4vuln")

def url_to_path(repo_url: str) -> str:
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    owner_name = repo_url.split("/")[-2]
    return os.path.join(BASE_PROJECT_PATH, owner_name + "_" + repo_name)

def clone_repo(repo_url: str) -> Tuple[git.Repo, str]:
    local_path = url_to_path(repo_url)
    if os.path.exists(local_path):
        return git.Repo(local_path), local_path
    return git.Repo.clone_from(repo_url, local_path), local_path 

def call_tool(project_path: str, class_name:str, method_name:str) -> Dict[str, str|List[str]]:
    project_path = os.path.abspath(project_path)
    subprocess.run(["java", "-jar", "./cg_llm4vuln-1.0-SNAPSHOT.jar", project_path, class_name, method_name], cwd="ext/cg_llm4vuln/build/libs/", check=True, capture_output=True)
    output = json.load(open("ext/cg_llm4vuln/build/libs/output.json"))
    return output

def get_cve_info(cve_id: str) -> str:
    url = "https://cve.mitre.org/cgi-bin/cvename.cgi?name=" + cve_id
    response = requests.get(url)
    soup = bs4.BeautifulSoup(response.text, "html.parser")
    cve_info = soup.select_one("div#GeneratedTable>table>tr:nth-child(4)>td").get_text()
    return cve_info

def run():
    checks()
    processed_repos:Set[str] = set()

    counter = {
        "total": 0,
        "failed": 0,
        "repeat": 0,
        "success": 0
    }
    with open("dataset/java/JavaCVE.csv") as f:
        reader = csv.DictReader(f)
        for row in track(reader, description="Processing CVEs"):
            try:
                counter["total"] += 1
                cve_id = row["cve"]
                repo_url = row["patch link"].split("/commit")[0]
                repo, local_path = clone_repo(repo_url)
                # if one repo has mutiple cves, we only process it once
                # if local_path in processed_repos:
                #     console.log("Processed")
                #     counter["repeat"] += 1
                #     continue
                processed_repos.add(local_path)

                # find and checkout the commit. Convert url to commit hash
                patch_commit:str = row["patch link"].split("/")[-1]
                # the parent of the patch commit is the vulnerable commit, we randomly choose one if there are multiple parents
                vulnerable_commit:str = repo.commit(patch_commit).parents[0]
                
                # checkout the vulnerable commit
                repo.git.checkout(vulnerable_commit)

                # find original and callee code, before and after the patch
                class_name = row["class and methods"].split(":")[0]
                method_name = row["class and methods"].split(":")[1]

                # call the tool
                code_before_patch = call_tool(local_path, class_name, method_name)
                code_before_patch["related"] = list(set(code_before_patch["related"]))
                
                # checkout the patch commit
                repo.git.checkout(patch_commit)

                # call the tool
                code_after_patch = call_tool(local_path, class_name, method_name)
                code_after_patch["related"] = list(set(code_after_patch["related"]))

                if code_before_patch["code"] == "" or code_after_patch["code"] == "":
                    console.log(f"Failed to get code for {cve_id}")
                    counter["failed"] += 1
                    continue

                if code_before_patch["code"] == code_after_patch["code"]:
                    console.log(f"Code before and after patch are the same for {cve_id}")
                    counter["failed"] += 1
                    continue

                # get cve info
                cve_info = get_cve_info(cve_id)

                # save the data
                data = {
                    "cve": cve_id,
                    "repo_remote": repo_url,
                    "repo_local": local_path,
                    "cve_info": cve_info,
                    "code_before_patch": code_before_patch,
                    "code_after_patch": code_after_patch
                }
                json.dump(data, open(f"dataset/java/{cve_id}.json", "w"))
                counter["success"] += 1
            except:
                console.log(f"Failed to process {cve_id}")
                console.print_exception()
                counter["failed"] += 1
    console.print_json(data=counter)