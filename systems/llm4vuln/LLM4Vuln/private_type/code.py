from typing import List

class Code:
    def __init__(self, code_str:str) -> None:
        self.code_str:str = code_str

    def get_str(self) -> str:
        if len(self.code_str) > 4000:
            return self.code_str[:4000]
        return self.code_str
    
    def get_all_str(self) -> str:
        return self.code_str


class CodeWithRelated(Code):
    def __init__(self, code_str:str, related_code:List[Code]) -> None:
        super().__init__(code_str)
        self.related_code:List[Code] = related_code
    
    def get_all_str(self) -> str:
        return self.code_str + '\n' + '\n'.join([code.get_all_str() for code in self.related_code])


class CodeWithRelatedAndCallee(CodeWithRelated):
    def __init__(self, code_str:str, related_code:List[Code], callee_code:List[Code]) -> None:
        super().__init__(code_str, related_code)
        self.callee_code:List[Code] = callee_code

    def get_all_str(self) -> str:
        # limited to 5,000 characters, which should be less than 5,000 tokens
        all_str = super().get_all_str() + '\n' + '\n'.join([code.get_all_str() for code in self.callee_code])
        if len(all_str) > 4000:
            return all_str[:4000]
        return all_str


class SolidityCode(CodeWithRelatedAndCallee):
    pass

class JavaCode(CodeWithRelatedAndCallee):
    pass

class CppCode(CodeWithRelatedAndCallee):
    pass
