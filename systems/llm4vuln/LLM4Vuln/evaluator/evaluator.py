from .prompt import PromptBuilder, PromptCombination
from private_type import LanguageResult
from langchain_core.language_models.llms import LLM
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain_community.llms import HuggingFacePipeline
from typing import Tuple, List, Dict
import models as LLM4VulnModels
import models.utils_model as MODELS_UTILS
#from models import gpt_4_turbo_model, gpt_35_turbo_model, gpt_41_nano_model, gpt_41_nano_model_random
from .prompt.evalutator import build_prompt_ask_whether_has_vuln_str, build_prompt_check_gt, transfer_whether_has_vuln_str_to_structure
from rich import get_console
from langchain_core.exceptions import OutputParserException
import traceback
import os
import json
from private_type.result import Result
from rich.progress import track, Progress
from config import PARALLEL_K
import json
import re

console = get_console()


### original LLM4Vuln parsers are not designed to handle "chatty" open-source models
def remove_think(text:str) -> str:
    if "</think>" in text:
        text = text.split("</think>")[-1]
    return text

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

def robust_json_extract(text):
    """
    Attempts:
    1. direct json
    2. extract {...}
    3. extract [...]
    -> heuristic vuln detection
    """
    if not text:
        raise ValueError("Empty response")

    text = str(text).strip()
    # direct parse
    try:
        return json.loads(text)
    except:
        pass

    # extract object
    obj_match = re.search(r'\{.*\}', text, re.DOTALL)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except:
            pass

    # extract array
    arr_match = re.search(r'\[.*\]', text, re.DOTALL)
    if arr_match:
        try:
            return json.loads(arr_match.group(0))
        except:
            pass

    raise ValueError("No valid JSON found")


def heuristic_parse_vulnerability(text: str) -> dict:
    """
    Multi-strategy heuristic parser for chatty / low-instruction-following models.
    Strategy order:
      1. Explicit JSON key presence (already in code, kept)
      2. Post-marker extraction (### Solution:, **Answer:**, etc.)
      3. Sentence-level Yes/No scan (not just first 50 chars)
      (4. Keyword density across full text)
      Raise if nothing found
    """
    if not text or not text.strip() or text.strip() == "{}":
        raise ValueError("Empty or null response — cannot determine vulnerability status.")
    text_clean = text.strip()
    text_lower = text_clean.lower()
    
    # --- Strategy 1: Explicit JSON keys ---
    if '"has_vuln": true' in text_lower[:200] or "'has_vuln': true" in text_lower[:200] or '"vulnerability": true' in text_lower[:200] or "'vulnerability': true" in text_lower[:200]:
        console.log("Heuristic parse: explicit key present")
        return {"has_vuln": True, "vuln_type": text}
    if '"has_vuln": false' in text_lower[:200] or "'has_vuln': false" in text_lower[:200] or '"vulnerability": false' in text_lower[:200] or "'vulnerability': false" in text_lower[:200]:
        console.log("Heuristic parse: explicit key present")
        return {"has_vuln": False, "vuln_type": "None"}

    # --- Strategy 2: Extract text AFTER common answer-section markers ---
    answer_markers = [
    r"###\s*(?:solution|respone|answer|result|conclusion|output|verdict)[:\s]*",
    r"\*\*(?:solution|respone|answer|result|conclusion|verdict)\*\*[:\s]*",
    r"#+\s*(?:final\s+)?(?:solution|answer|response|result|conclusion|output|verdict)\s*[:\-]*\s*"
    ]
    for marker in answer_markers:
        m = re.search(marker, text_lower)
        if m:
            after = text_lower[m.end():]
            if after.startswith("yes") or "is vulnerable" in after[:80] or "contains a vuln" in after[:80] or "has a vuln" in after[:80]:
                console.log("Heuristic parse: marker present")
                return {"has_vuln": True, "vuln_type": text_clean}
            if after.startswith("no") or "not vulnerable" in after[:80] or "no vuln" in after[:80] or "does not contain" in after[:80]:
                console.log("Heuristic parse: marker present")
                return {"has_vuln": False, "vuln_type": "None"}

    # --- Strategy 3: Yes/No scan ---
    if text_lower[:10].startswith("yes") or "code is not vulnerable" in text_lower[:80]:
        console.log("Heuristic parse: starts with yes/no/vulnerable")
        return {"has_vuln": True, "vuln_type": text_clean}
    if text_lower[:10].startswith("no") or "code is vulnerable" in text_lower[:80]:
        console.log("Heuristic parse: starts with yes/no/vulnerable")
        return {"has_vuln": False, "vuln_type": "None"}
    
    # remove due to skewed results w.r.t. models echoing answer
    # # --- Strategy 4: Keyword density ---
    # vuln_positive = ["is vulnerable", "contains a vulnerability", "has a vulnerability",
    #                  "vulnerability exists", "is susceptible", "vulnerable to", "has vuln"]
    # vuln_negative = ["not vulnerable", "no vulnerability", "does not contain a vuln",
    #                  "is not susceptible", "no vuln", "is secure", "cannot find a vuln",
    #                  "found no vuln"]

    # pos_hits = sum(1 for p in vuln_positive if p in text_lower)
    # neg_hits = sum(1 for n in vuln_negative if n in text_lower)

    # if pos_hits > neg_hits and pos_hits > 0:
    #     console.log("Heuristic parse: keyword density")
    #     return {"has_vuln": True, "vuln_type": text_clean}
    # if neg_hits > pos_hits and neg_hits > 0:
    #     console.log("Heuristic parse: keyword density")
    #     return {"has_vuln": False, "vuln_type": "None"}

    # fail
    raise ValueError(f"Heuristic parse failed. Could not determine vulnerability status. Start of text: {text[:100]}...")


def heuristic_parse_gt(text: str) -> dict:
    """Fallback parser for GT check responses."""
    text_lower = text.lower()
    
    # Explicit JSON key
    if '"is_gt": true' in text_lower or "'is_gt': true" in text_lower:
        console.log("Heuristic parse gt: explicit key present")
        return {"is_gt": True}
    if '"is_gt": false' in text_lower or "'is_gt': false" in text_lower:
        console.log("Heuristic parse gt: explicit key present")
        return {"is_gt": False}
    
    # # Check for confirmation phrases
    # confirm = ["correct", "matches", "same type", "same vulnerability", "is the gt", "is correct", "yes"]
    # deny    = ["incorrect", "does not match", "different type", "wrong type", "is not the gt", "no"]
       
    # pos = sum(1 for p in confirm if p in text_lower)
    # neg = sum(1 for p in deny if p in text_lower)
    # if pos > neg and pos > 0:
    #     console.log("Heuristic parse gt: keyword density")
    #     return {"is_gt": True}
    # if neg > pos and neg > 0:
    #     console.log("Heuristic parse gt: keyword density")
    #     return {"is_gt": False}
    
    raise ValueError(f"GT heuristic parse failed. Start: {text[:80]}...")


class MapKey:
    def __init__(self, combination:PromptCombination, model:str, gt_description:str):
        self.combination = combination
        self.model = model
        self.gt_description = gt_description
    
    def __eq__(self, other):
        return self.combination == other.combination and self.model == other.model and self.gt_description == other.gt_description
    
    def __hash__(self):
        return hash((self.combination, self.model, self.gt_description))

# run_config = {
#         "summary_model": args.summary,
#         "gt_model": args.gt,
#         "embedding_model": args.embedding
#     }
# llm4vuln-${MODEL}__sum-${SM}__emb-${EMB}__gt-${GT}

class Evaluator:
    def __init__(self, language:str, run_config:dict = None, dataset_base: str | None = None) -> None:
        self.language = language
        self.run_config = run_config or {}
        self.gt_model_name = self.run_config.get("gt_model")
        self.summary_model_name = self.run_config.get("summary_model")
        self.emb_model_name = self.run_config.get("embedding_model")

        import registry
        loader_cls = registry.get_dataloader(language)
        self.data_loader = loader_cls(dataset_base=dataset_base)
        self.middle_result = []
        self.result = LanguageResult(language)
        self.loaded_middle_result = []
        self.loaded_middle_result_map = {}

        self.checkpoint_file = None
        self.stats_file = None
        self.run_id = None
    
    # # Example to filter type
    # {
    #     "models": [
    #         "gpt-4-turbo",
    #         "gpt-35-turbo"
    #     ],
    #     "prompt_scheme": [
    #         "RawSchemePrompt",
    #         "SummarizedKnowledgePrompt",
    #         "WithContextPrompt"
    #     ]
    # }

    def make_middle_result(self, combination: PromptCombination, gt:bool, gt_description:str, raw_result:str, has_vuln:bool, vuln_type:str, is_gt:bool, model:str, prompt:str, pair_id: str | None = None):
        return {
            "combination": combination.to_list(),
            "gt": gt,
            "gt_description": gt_description,
            "raw_result": raw_result,
            "has_vuln": has_vuln,
            "vuln_type": vuln_type,
            "is_gt": is_gt,
            "model": model,
            "prompt": prompt,
            "pair_id": pair_id
        }

    def get_all_models(self, filter_type:dict = None) -> List[Tuple[str, LLM]]:
        results = []
        # for model in LLM4VulnModels.supported["commercial"]:
        #     if filter_type is not None and "models" in filter_type and model not in filter_type["models"]:
        #         continue
        #     results.append((model, LLM4VulnModels.supported["commercial"][model]))
        for model in LLM4VulnModels.supported["open-source"]:
            if filter_type is not None and "models" in filter_type and model not in filter_type["models"]:
                continue

            # check if model is already loaded (summary, embedding, gt); else: intantiate
            results.append((model, MODELS_UTILS.get_llm_client(model)))
        return results

    def check_combination(self, combination: PromptCombination, filter_type:dict):
        if filter_type is not None and "prompt_scheme" in filter_type:
            if combination.context_prompt not in filter_type["prompt_scheme"]:
                return False
            if combination.knowledge_prompt not in filter_type["prompt_scheme"]:
                return False
            if combination.scheme_prompt not in filter_type["prompt_scheme"]:
                return False
        return True



    ### adapt evaluate function:
    ##########################################
    ### - change while True loops to for attempt in range
    ### - local performance, remove rate limiting
    def evaluate(self, filter_type:dict = None):

        models = self.get_all_models(filter_type) ## get models
        self.run_id = f"llm4vuln-{self.language}_{models[0][0]}_sum-{self.summary_model_name}_emb-{self.emb_model_name}_gt-{self.gt_model_name}"
        self.checkpoint_file = f"middle_result.{self.run_id}.not_finish.json"
        self.stats_file = f"stats_result.{self.run_id}.json"
        
        console.log(f"[Evaluator] Checkpoint file: {self.checkpoint_file}")
        console.log(f"[Evaluator] Stats file: {self.stats_file}")

        if os.path.exists(self.checkpoint_file):
            # if exists, continue from the current point
            with open(self.checkpoint_file, "r") as f:
                self.loaded_middle_result = json.load(f)

        # --- add statistics ---
        # Structure: stats[prompt_scheme][knowledge][context][model][error_type] = count
        self.stats = {} 
        def update_stat(comb, model_name, error_type):
            # Helper to safely increment nested dict
            s = comb.scheme_prompt
            k = comb.knowledge_prompt
            c = comb.context_prompt
            if s not in self.stats: self.stats[s] = {}
            if k not in self.stats[s]: self.stats[s][k] = {}
            if c not in self.stats[s][k]: self.stats[s][k][c] = {}
            if model_name not in self.stats[s][k][c]: self.stats[s][k][c][model_name] = {}
            
            self.stats[s][k][c][model_name][error_type] = self.stats[s][k][c][model_name].get(error_type, 0) + 1


        counter = 0
        MAX_RETRIES = 3

        for loaded in track(self.data_loader.load(), f"Evaluating in dataset for language: {self.language}", console=console):
            if len(loaded) == 4:
                code, ground_truth_label, ground_truth_description, pair_id = loaded
            else:
                code, ground_truth_label, ground_truth_description = loaded
                pair_id = None
            todo_list = PromptBuilder.build_all(self.language, code) 
            
            for prompt, combination in todo_list:
                counter += 1
                console.log(f"Working on {counter}th item.")

                # skip if filtered out
                if filter_type is not None and "prompt_scheme" in filter_type and not self.check_combination(combination, filter_type):
                    continue

                for model_name, model in models:
                    # check whether in the middle result
                    in_middle_flag = False
                    current_result = None
                    to_pop_index = None
                    is_gt = None
                    for middle_index, item in enumerate(self.loaded_middle_result):
                        if PromptCombination(*(item["combination"])) == combination and item["model"] == model_name and item["gt_description"] == ground_truth_description:
                            in_middle_flag = True
                            current_result = item
                            to_pop_index = middle_index
                            break

                    if in_middle_flag:
                        # read from the middle result
                        raw_result = current_result["raw_result"]
                        has_vuln = current_result["has_vuln"]
                        vuln_type = current_result["vuln_type"]
                        is_gt = current_result["is_gt"]
                        console.log("Recover from middle result. Skip ...")
                    else:                        
                        ### (1) generate raw result
                        raw_result = None
                        for attempt in range(MAX_RETRIES):
                            try:
                                raw_response = build_prompt_ask_whether_has_vuln_str(prompt, model).invoke({})
                                raw_result = clean_llm_response(raw_response)
                                break # success
                            except Exception as e:
                                console.log(f"Generation error (Attempt {attempt+1}/{MAX_RETRIES}): {e}")
                                
                        # If generation failed completely, skip this item
                        if raw_result is None or raw_result == "":
                            console.log("Failed to generate raw result (or empty). Skipping item.")
                            update_stat(combination, model_name, "generation_error")
                            continue

                        ### (2) parse result
                        parse_success = False
                        for attempt in range(MAX_RETRIES):
                            try:
                                # # Attempt 1: Strict JSON
                                # result = json.loads(raw_result)
                                result = robust_json_extract(raw_result)
                                # Validate structure
                                if "has_vuln" not in result:
                                    raise KeyError("Missing 'has_vuln'")
                                
                                has_vuln = result["has_vuln"]
                                vuln_type = result["vuln_type"]
                                parse_success = True
                                break 
                            except Exception as e:
                                # Attempt 2: structure by GT model
                                try:
                                    result = transfer_whether_has_vuln_str_to_structure(raw_result, MODELS_UTILS.get_GT_MODEL()).invoke({})
                                    if isinstance(result, dict):
                                        has_vuln = result["has_vuln"]
                                        vuln_type = result["vuln_type"]
                                        parse_success = True
                                        break # success
                                except Exception as e:
                                    # Attempt 3: Heuristic Fallback
                                    try:
                                        result = heuristic_parse_vulnerability(raw_result)
                                        has_vuln = result["has_vuln"]
                                        vuln_type = result["vuln_type"]
                                        parse_success = True
                                        console.log(f"Heuristic parse used for: {raw_result[:30]}...")
                                        break # success
                                    except Exception as e:
                                        console.log(f"Result parsing error (Attempt {attempt+1}/{MAX_RETRIES}): {e}")
                        
                        if not parse_success:
                            update_stat(combination, model_name, "parsing_error")
                            continue

                    # Get the result saver object
                    result_saver_object = self.result.get_result(model_name).get_result(*(combination.to_tuple()))

                    # If it is not vulnerable in the label, but the model thinks it is vulnerable, then it is a false positive
                    if not ground_truth_label and has_vuln:
                        result_saver_object.FP += 1
                        is_gt = None
                    # If it is not vulnerable in the label, and the model thinks it is not vulnerable, then it is a true negative
                    if not ground_truth_label and not has_vuln:
                        result_saver_object.TN += 1
                        is_gt = None
                    # If it is vulnerable in the label, but the model thinks it is not vulnerable, then it is a false negative
                    if ground_truth_label and not has_vuln:
                        result_saver_object.FN += 1
                        is_gt = None
                    # If it is vulnerable in the label, and the model thinks it is vulnerable, we need to check whether the type is correct
                    if ground_truth_label and has_vuln:
                        if not in_middle_flag:
                            gt_check_success = False 
                            for attempt in range(MAX_RETRIES):
                                try:
                                    gt_response = build_prompt_check_gt(raw_result, ground_truth_description, MODELS_UTILS.get_GT_MODEL()).invoke({})

                                    if not isinstance(gt_response, str):
                                        gt_response = str(gt_response)

                                    cleaned_gt = clean_llm_response(gt_response)
                                    # Attempt 1: robust JSON extraction
                                    try:
                                        # gt_json = json.loads(cleaned_gt)
                                        gt_json = robust_json_extract(cleaned_gt)
                                        if isinstance(gt_json, dict) and "is_gt" in gt_json:
                                            is_gt = gt_json["is_gt"]
                                            gt_check_success = True
                                            break
                                    except Exception:
                                        pass

                                    # Attempt 2: heuristic parser
                                    try:
                                        heuristic = heuristic_parse_gt(cleaned_gt)

                                        if heuristic is not None:
                                            is_gt = heuristic["is_gt"]
                                            gt_check_success = True
                                            console.log(f"Heuristic GT parse used: {cleaned_gt[:80]}...")
                                            break
                                    except Exception:
                                        pass

                                except (KeyError, OutputParserException, TypeError, ValueError) as e:
                                    console.log(f"GT Type Check error (Attempt {attempt+1}/{MAX_RETRIES}): {e}")
                            if not gt_check_success:
                                update_stat(combination, model_name, "gt_check_error")
                        else:
                            is_gt = current_result["is_gt"]

                        if is_gt is not None:
                            if is_gt:
                                result_saver_object.TP += 1
                            else:
                                result_saver_object.FP_type += 1

                    # save middle result  
                    with open(self.stats_file, "w") as f:
                        json.dump(self.stats, f, indent=4)

                    self.middle_result.append(self.make_middle_result(combination, ground_truth_label, ground_truth_description, raw_result, has_vuln, vuln_type, is_gt, model_name, prompt, pair_id))
                    with open(self.checkpoint_file, "w") as f:
                        json.dump(self.middle_result, f)
                        
                    if in_middle_flag:
                        self.loaded_middle_result.pop(to_pop_index)

        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)

        # Compute pairwise accuracy for paired datasets like PrimeVul
        self.compute_pairwise_accuracy()

        

    
    def compute_pairwise_accuracy(self):
        """
        Compute pairwise accuracy from middle_result.
        For each CVE, match the vulnerable (gt=True) and non-vulnerable (gt=False) code pair.
        A pair is correct if both are correctly classified.
        """
        if not self.middle_result:
            return
        
        from collections import defaultdict
        import re
        
        # Group by (model, prompt_combination)
        grouped = defaultdict(lambda: defaultdict(list))
        
        for item in self.middle_result:
            model = item["model"]
            combination = tuple(item["combination"])
            pair_id = item.get("pair_id")
            if pair_id is None:
                # extract CVE from gt_description as a fallback
                if item.get("gt_description"):
                    match = re.search(r'(CVE-\d{4}-\d{4,5})', item["gt_description"])
                    if match:
                        pair_id = match.group(1)

            if pair_id is None:
                continue

            key = (model, combination, pair_id)
            grouped[key][item["gt"]].append(item)
        
        # For each CVE pair, check if both are correctly classified
        for (model, combination, cve_id), by_label in grouped.items():
            if cve_id is None:
                continue

            # Three seperate runs - three predictions
            # For vulnerable code: Correct if ANY of the top-3 are detected and the judge confirms it's the GT
            vuln_correct = any(item["has_vuln"] == True and item["is_gt"] == True for item in by_label.get(True, []))
            # For non-vulnerable code: Correct if ALL of the top-3 are marked as "No" (has_vuln=False)
            non_vuln_correct = all(item["has_vuln"] == False for item in by_label.get(False, []))
            
            pairs_total = 1
            pairs_correct = 1 if (vuln_correct and non_vuln_correct) else 0
            
            # Update result object
            result_obj = self.result.get_result(model).get_result(*combination)
            result_obj.pairs_correct += pairs_correct
            result_obj.pairs_total += pairs_total
