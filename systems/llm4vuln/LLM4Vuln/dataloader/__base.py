from abc import ABC, abstractmethod
from private_type import Code
from typing import Generator, Tuple
from registry import register_dataloader
import os

class BaseLoader(ABC):
    language = "base"

    # def __init__(self) -> None:
    #     self.dataset_base = os.path.join("dataset", self.language)
    # add dataset_base to use other datasets (e.g., primevul_paired)
    def __init__(self, dataset_base: str | None = None) -> None:
        if dataset_base is None:
            dataset_base = os.path.join("dataset", self.language)
        self.dataset_base = dataset_base

    @abstractmethod
    def load(self) -> Generator[tuple, None, None]:
        # return code, label, optional gt_description, and optional pair_id
        pass

    def __init_subclass__(cls) -> None:
        register_dataloader(cls)
        return super().__init_subclass__()
