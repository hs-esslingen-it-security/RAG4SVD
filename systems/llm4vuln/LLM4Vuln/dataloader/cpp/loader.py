from ..__base import BaseLoader
import json
import os
from typing import Generator, Tuple
from private_type.code import CppCode

class CppLoader(BaseLoader):
    language = "cpp"
    def __init__(self, dataset_base: str | None = None):
        super().__init__(dataset_base=dataset_base)

    def load(self) -> Generator[Tuple[CppCode, bool, str, str], None, None]:
        for file in os.listdir(self.dataset_base):
            if file.endswith(".json"):
                with open(os.path.join(self.dataset_base, file), "r") as f:
                    data = json.load(f)
                    pair_id = data.get("cve") or os.path.splitext(file)[0]
                    code = CppCode(data["code_before_patch"]["code"], [], [CppCode(c,[],[]) for c in data["code_before_patch"]["related"]])
                    yield code, True, data.get("cve_info", ""), pair_id

                    code = CppCode(data["code_after_patch"]["code"], [], [CppCode(c,[],[]) for c in data["code_after_patch"]["related"]])
                    yield code, False, "", pair_id

