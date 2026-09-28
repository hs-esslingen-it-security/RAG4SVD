import pandas as pd
import numpy as np
import html
import re
from FlagEmbedding import BGEM3FlagModel
from sklearn.metrics.pairwise import cosine_similarity
import xml.etree.ElementTree as ET
from typing import Dict, Optional, List

model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True, devices=['cuda:0'])
ns = {
    "cwe": "http://cwe.mitre.org/cwe-7",
    "xhtml": "http://www.w3.org/1999/xhtml"
}

df = pd.read_csv("1435.csv/1435_filtered_columns.csv")  # CWE-ID,Name,Description

corpus_ids = df['CWE-ID'].fillna("").tolist()
corpus_texts = df['Name'].fillna("") + " " + df['Description'].fillna("")
valid_indices = [i for i, text in enumerate(corpus_texts) if text.strip() != ""]
corpus_texts = [corpus_texts[i] for i in valid_indices]
corpus_ids = [corpus_ids[i] for i in valid_indices]

corpus_embeddings = model.encode(
    corpus_texts,
    return_dense=True,
    return_sparse=True,
    batch_size=8
)


def normalize_embeddings(embeddings):
    norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norm[norm == 0] = 1e-8
    return embeddings / norm


corpus_embeddings['dense_vecs'] = normalize_embeddings(corpus_embeddings['dense_vecs'])


def search_by_query(query: str, top_k: int = 1) -> list:
    query_embedding = model.encode(
        [query],
        return_dense=True,
        return_sparse=True
    )
    query_embedding['dense_vecs'] = normalize_embeddings(query_embedding['dense_vecs'])
    dense_similarity = cosine_similarity(
        query_embedding['dense_vecs'],
        corpus_embeddings['dense_vecs']
    ).flatten()

    sparse_similarity = []
    query_sparse_dict = query_embedding['lexical_weights'][0]
    for doc_sparse in corpus_embeddings['lexical_weights']:
        score = sum(query_sparse_dict.get(k, 0) * doc_sparse.get(k, 0) for k in query_sparse_dict)
        sparse_similarity.append(score)
    sparse_similarity = np.array(sparse_similarity)

    combined_score = 0.7 * dense_similarity + 0.3 * sparse_similarity

    top_indices = np.argsort(combined_score)[::-1][:top_k]
    return [(corpus_ids[i], round(combined_score[i].item(), 4)) for i in top_indices]


def parse_cwe_xml(xml_file_path: str) -> Dict[str, ET.Element]:
    ns = {"cwe": "http://cwe.mitre.org/cwe-7"}

    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        weakness_map = {}
        weaknesses = root.findall(".//cwe:Weaknesses/cwe:Weakness", namespaces=ns)

        for weakness in weaknesses:
            weak_id = weakness.get("ID")
            if weak_id:
                weakness_map[weak_id] = weakness
        return weakness_map
    
    except FileNotFoundError:
        print(f"Error: File {xml_file_path} not found")
        return {}
    except ET.ParseError:
        print(f"Error: {xml_file_path} is not a valid XML file")
        return {}
    except Exception as e:
        print(f"An unknown error occurred while parsing the XML file: {str(e)}")
        return {}

def get_child_text(parent_elem: ET.Element, child_tag: str, namespaces: Dict[str, str]) -> Optional[str]:
    child = parent_elem.find(child_tag, namespaces=namespaces)
    if child is not None and child.text:
        return child.text.strip()
    return None


def extract_bad_example_code(weakness_elem: ET.Element) -> List[str]:
    bad_code_list = []
    demo_examples = weakness_elem.findall(
        ".//cwe:Demonstrative_Examples//cwe:Demonstrative_Example",
        namespaces=ns
    )

    for demo_example in demo_examples:
        all_code_nodes = demo_example.findall(
            ".//cwe:Example_Code",
            namespaces=ns
        )
        bad_code_nodes = []
        for code_node in all_code_nodes:
            nature = code_node.get("Nature", "").strip().lower()
            if nature == "bad":
                bad_code_nodes.append(code_node)

        for code_node in bad_code_nodes:
            div_node = code_node.find("xhtml:div", namespaces=ns)

            if div_node:
                def _extract_all_text(node):
                    text = []
                    if node.text:
                        text.append(node.text)
                    for child in node:
                        text.append(_extract_all_text(child))
                        if child.tail:
                            text.append(child.tail)
                    return "".join(text)

                raw_text = _extract_all_text(div_node)
            else:
                raw_text = code_node.text or ""

            if raw_text:
                clean_code = html.unescape(raw_text)

                clean_code = clean_code.replace("\\\\n", "\n")
                clean_code = clean_code.replace("\\\\t", "\t")
                clean_code = clean_code.replace("\\\\", "\\")

                clean_code = clean_code.replace("<xhtml:br/>", "\n")
                clean_code = clean_code.replace("<xhtml:br>", "\n")
                clean_code = clean_code.replace("<br/>", "\n")
                clean_code = clean_code.replace("<br>", "\n")

                clean_code = re.sub(r'\n+', '\n', clean_code)
                clean_code = re.sub(r' +', ' ', clean_code)
                clean_code = clean_code.strip()

                if clean_code:
                    bad_code_list.append(clean_code)

    return bad_code_list

def get_weakness_by_id(weakness_map: Dict[str, ET.Element], target_id: str) -> Optional[Dict]:
    ns = {"cwe": "http://cwe.mitre.org/cwe-7"}
    target_id_str = str(target_id)

    weakness_elem = weakness_map.get(target_id_str)
    if not weakness_elem:
        print(f"Weakness entry with ID {target_id_str} not found")
        return None

    weakness_info = {
        "Name": weakness_elem.get("Name"),
        "Description": get_child_text(weakness_elem, "cwe:Description", ns),
        "Bad_Example_Code": extract_bad_example_code(weakness_elem)
    }

    return weakness_info

if __name__ == "__main__":
    query1 = "Improper Input Validation"
    result1 = search_by_query(query1, top_k=2)
    print(f"Query: {query1}")
    knowledge = "Possible weakness types:"
    for order, (idx, score) in enumerate(result1, 1):
        XML_FILE = "cwec_latest.xml/cwec_v4.19.1.xml"
        weakness_dict = parse_cwe_xml(XML_FILE)
        target_id = idx
        result = get_weakness_by_id(weakness_dict, target_id)

        if result:
            code = ""
            for segment in result['Bad_Example_Code']:
                code += segment

            knowledge = knowledge + "\n" + str(order) + "、" + result['Name'] + "：" + result['Description'] \
                        + " Examples of Vulnerable Code：" + code

    print(knowledge)