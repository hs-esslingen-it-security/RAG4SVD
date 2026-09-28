from typing import Dict

class Result:
    def __init__(self):
        self.TP = 0
        self.FP = 0
        self.FN = 0
        self.TN = 0
        self.FP_type = 0
        self.pairs_total = 0
        self.pairs_correct = 0
    
    @property
    def precision(self):
        try:
            return self.TP / (self.TP + self.FP + self.FP_type)
            # return self.TP / (self.TP + self.FP)
        except ZeroDivisionError:
            return -1
    
    @property
    def recall(self):
        try:
            # return self.TP / (self.TP + self.FN)
            return self.TP / (self.TP + self.FN + self.FP_type)
        except ZeroDivisionError:
            return -1
    
    @property
    def f1(self):
        if self.precision == -1 or self.recall == -1:
            return -1
        try:
            return 2 * self.precision * self.recall / (self.precision + self.recall)
        except ZeroDivisionError:
            return -1
        
    @property
    def accuracy(self):
        return (self.TP + self.TN) / (self.TP + self.TN + self.FP + self.FN + self.FP_type)
    
    @property
    def precision_binary(self):
        try:
            return (self.TP + self.FP_type) / (self.TP + self.FP + self.FP_type)
        except ZeroDivisionError:
            return -1
        
    @property
    def recall_binary(self):
        try:
            return (self.TP + self.FP_type) / (self.TP + self.FN + self.FP_type)
        except ZeroDivisionError:
            return -1
    
    @property
    def f1_binary(self):
        if self.precision_binary == -1 or self.recall_binary == -1:
            return -1
        try:
            return 2 * self.precision_binary * self.recall_binary / (self.precision_binary + self.recall_binary)
        except ZeroDivisionError:
            return -1

    @property
    def pairwise_accuracy(self):
        try:
            return self.pairs_correct / self.pairs_total
        except ZeroDivisionError:
            return -1
    
    def to_json(self):
        return {
            "TP": self.TP,
            "FP": self.FP,
            "FN": self.FN,
            "TN": self.TN,
            "FP_type": self.FP_type,
            "pairs_total": self.pairs_total,
            "pairs_correct": self.pairs_correct,
            "pairwise_accuracy": self.pairwise_accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "precision_binary": self.precision_binary,
            "recall_binary": self.recall_binary,
            "f1_binary": self.f1_binary,
        }
    
    def merge(self, in_result):
        self.TP += in_result.TP
        self.FP += in_result.FP
        self.FN += in_result.FN
        self.TN += in_result.TN
        self.FP_type += in_result.FP_type


class ModelResult:
    def __init__(self) -> None:
        self.results:Dict[str, Dict[str, Dict[str, Result]]] = {}

    def get_result(self, scheme:str, knowledge:str, context:str) -> Result:
        if scheme not in self.results:
            self.results[scheme] = {}
        if knowledge not in self.results[scheme]:
            self.results[scheme][knowledge] = {}
        if context not in self.results[scheme][knowledge]:
            self.results[scheme][knowledge][context] = Result()
        return self.results[scheme][knowledge][context]
    
    def to_json(self):
        return {k: {k2: {k3: v3.to_json() for k3, v3 in v2.items()} for k2, v2 in v.items()} for k, v in self.results.items()}
    
class LanguageResult:
    def __init__(self, language:str) -> None:
        self.results:Dict[str, ModelResult] = {}
        self.language = language

    def get_result(self, model:str) -> ModelResult:
        if model not in self.results:
            self.results[model] = ModelResult()
        return self.results[model]
    
    def to_json(self) -> dict:
        return {k: v.to_json() for k, v in self.results.items()}
    

    def to_latex_table(self) -> str:
        table_model_order = ["gpt-35-turbo", "gpt-4-turbo", "phi3", "codellama-13b", "codellama-70b", "llama3"]
        # scheme_order = ["RawSchemePrompt", "PreCoTSchemePrompt", "PostCoTSchemePrompt"]
        scheme_order = ["RawSchemePrompt", "PreCoTSchemePrompt"]
        knowledge_order = ["NoKnowledgePrompt", "OriginalKnowledgePrompt", "SummarizedKnowledgePrompt"]
        context_order = ["WithContextPrompt", "WithoutContextPrompt"]

        knowledge_text_map = {
            "NoKnowledgePrompt": "W/O Extra Knowledge",
            "OriginalKnowledgePrompt": "W/ Original Vuln Report",
            "SummarizedKnowledgePrompt": "W/ Summarized Vuln Report"
        }

        model_text_map = {
            "gpt-35-turbo": "GPT-3.5",
            "gpt-4-turbo": "GPT-4",
            "phi3": "Phi-3",
            "codellama-13b": "CodeLLama 13B",
            "codellama-70b": "CodeLLama 70B",
            "llama3": "Llama 3"
        }

        def arrow_true_case(value:int, value_raw:int) -> str:
            if value > value_raw:
                return "\\dataUpC"
            elif value < value_raw:
                return "\\dataDownC"
            else:
                return ""
        
        def arrow_false_case(value:int, value_raw:int) -> str:
            if value > value_raw:
                return "\\dataDownC"
            elif value < value_raw:
                return "\\dataUpC"
            else:
                return ""

        # first is the table header
        table_with_number = """
\\begin{table*}[!t]
    \\caption{Raw results of TP, FP, and FN under different combinations of knowledge, context, prompt schemes, and LLMs for """ + self.language.capitalize() + """.}
    % \\vspace{-2ex}
    \label{tab:evaluation_all_detail}
    \\resizebox{\\textwidth}{!}{
        \\begin{tabular}{|ll|crrrrrr|crrrrrr|crrrrrr|}
            \\hline
            \\multicolumn{2}{|l|}{\multirow{2}{*}{}}                                      & \\multicolumn{8}{c|}{Raw} & \\multicolumn{8}{c|}{Pre-CoT}                                                                                                                                                                                                                                                                               \\\\ \\cline{3-18}
            \\multicolumn{2}{|l|}{}                                                       & \\multicolumn{1}{c|}{TP}  & \\multicolumn{1}{c|}{FP}      & \\multicolumn{1}{c|}{TN}     & \\multicolumn{1}{c|}{FN}  & \\multicolumn{1}{c|}{FP-type} & \\multicolumn{1}{c|}{Precision} & \\multicolumn{1}{c|}{Recall} & \\multicolumn{1}{c|}{Accuracy} & \\multicolumn{1}{c|}{TP} & \\multicolumn{1}{c|}{FP} & \\multicolumn{1}{c|}{TN} & \\multicolumn{1}{c|}{FN} & \\multicolumn{1}{c|}{FP-type} & \\multicolumn{1}{c|}{Precision} & \\multicolumn{1}{c|}{Recall} & \\multicolumn{1}{c|}{Accuracy}                           \\\\
            \\hline
    """
        
        for model in table_model_order:
            if model in self.results:
                for knowledge_type in knowledge_order:
                    for context_type in context_order:
                        if context_type == "WithContextPrompt":
                            table_with_number += "\\multicolumn{1}{|c|}{\\multirow{2}{*}{" + model_text_map[model] + " " + knowledge_text_map[knowledge_type] + "}} & C "
                        elif context_type == "WithoutContextPrompt":
                            table_with_number += "\\multicolumn{1}{|c|}{}                                          & N "
                        for scheme_type in scheme_order:
                            result = self.results[model].get_result(scheme_type, knowledge_type, context_type)

                            if scheme_type == "RawSchemePrompt":
                                table_with_number += " & \\multicolumn{1}{r|}{" + str(result.TP) + "} & \\multicolumn{1}{r|}{" + str(result.FP) + "} & \\multicolumn{1}{r|}{" + str(result.TN) + "} & \\multicolumn{1}{r|}{" + str(result.FN) + "} & \\multicolumn{1}{r|}{" + str(result.FP_type) + "} " + " & \\multicolumn{1}{r|}{" + ('%.02f' % (result.precision*100)) + "} & \\multicolumn{1}{r|}{" + ('%.02f' % (result.recall*100)) + "} & \\multicolumn{1}{r|}{" + ('%.02f' % (result.accuracy*100)) + "} "
                            else:
                                raw_result = self.results[model].get_result("RawSchemePrompt", knowledge_type, context_type)
                                # add up and down arrows
                                table_with_number += " & \\multicolumn{1}{r|}{" + str(result.TP) + arrow_true_case(result.TP, raw_result.TP) + "} & \\multicolumn{1}{r|}{" + str(result.FP) + arrow_false_case(result.FP, raw_result.FP) + "} & \\multicolumn{1}{r|}{" + str(result.TN) + arrow_true_case(result.TN, raw_result.TN) + "} & \\multicolumn{1}{r|}{" + str(result.FN) + arrow_false_case(result.FN, raw_result.FN) + "} & \\multicolumn{1}{r|}{" + str(result.FP_type) + arrow_false_case(result.FP_type, raw_result.FP_type) + "} " + " & \\multicolumn{1}{r|}{" + ('%.02f' % (result.precision*100)) + arrow_true_case(result.precision, raw_result.precision) + "} & \\multicolumn{1}{r|}{" + ('%.02f' % (result.recall*100)) + arrow_true_case(result.recall, raw_result.recall) + "} & \\multicolumn{1}{r|}{" + ('%.02f' % (result.accuracy*100)) + arrow_true_case(result.accuracy, raw_result.accuracy) + "} "
                        table_with_number += "\\\\\n"
                        if context_type == "WithoutContextPrompt":
                            table_with_number += "\\hline\n"

        # end of table
        table_with_number += """\\end{tabular}
    }
    \\begin{flushleft}
        1. ``C'' and ``N'' represent the results with context and without context, respectively. \\\\
        2. \\dataUpC~and \\dataDownC~indicate better or worse values compared to the Raw column.
    \\end{flushleft}
\\end{table*}"""

        return table_with_number
    
    def to_latex_table_f1(self) -> str:
        table_model_order = ["gpt-4.1", "phi3", "llama3", "o4-mini", "qwq", "deepseek", "AVERAGE"]
        # scheme_order = ["RawSchemePrompt", "PreCoTSchemePrompt", "PostCoTSchemePrompt"]
        scheme_order = ["RawSchemePrompt", "PreCoTSchemePrompt"]
        knowledge_order = ["NoKnowledgePrompt", "OriginalKnowledgePrompt", "SummarizedKnowledgePrompt"]
        context_order = ["WithContextPrompt", "WithoutContextPrompt"]

        knowledge_text_map = {
            "NoKnowledgePrompt": "None (*3)",
            "OriginalKnowledgePrompt": "Original",
            "SummarizedKnowledgePrompt": "Summarized"
        }

        model_text_map = {
            "gpt-35-turbo": "GPT-3.5",
            "gpt-4-turbo": "GPT-4",
            "phi3": "Phi-3",
            "codellama-13b": "CodeLLama 13B",
            "codellama-70b": "CodeLLama 70B",
            "llama3": "Llama 3",
            "qwq": "QwQ-32B",
            "deepseek": "DeepSeek-R1",
            "o4-mini": "o4-mini",
            "gpt-4.1": "GPT-4.1",
            "AVERAGE": "Average"
        }

        context_text_map = {
            "WithContextPrompt": "C",
            "WithoutContextPrompt": "N"
        }

        def arrow_true_case(value:int, value_raw:int) -> str:
            if value > value_raw:
                return "\\dataUpC"
            elif value < value_raw:
                return "\\dataDownC"
            else:
                return ""
        
        def arrow_false_case(value:int, value_raw:int) -> str:
            if value > value_raw:
                return "\\dataDownC"
            elif value < value_raw:
                return "\\dataUpC"
            else:
                return ""

        # first is the table header
        table_with_number = """
\\begin{table*}[!t]
    \\caption{Raw results of TP, FP, and FN under different combinations of knowledge, context, prompt schemes, and LLMs for """ + self.language.capitalize() + """.}
    % \\vspace{-2ex}
    \label{tab:evaluation_all_detail}
    \\resizebox{\\textwidth}{!}{
        \\begin{tabular}{lll|rrrrrrrr|rrrrrrrr|}
            \\hline
            \\multicolumn{3}{|l|}{\multirow{2}{*}{}}                                      & \\multicolumn{8}{c|}{Raw} & \\multicolumn{8}{c|}{CoT}                                                                                                                                                                                                                                                                               \\\\ \\cline{4-19}
            \\multicolumn{3}{|l|}{} & \\multicolumn{1}{c|}{TP} & \\multicolumn{1}{c|}{FP} & \\multicolumn{1}{c|}{TN} & \\multicolumn{1}{c|}{FN} & \\multicolumn{1}{c|}{FP\\textsubscript{t}} & \\multicolumn{1}{c|}{P\\textsubscript{m}} & \\multicolumn{1}{c|}{R\\textsubscript{m}} & \\multicolumn{1}{c|}{F1\\textsubscript{m}} & \\multicolumn{1}{c|}{TP} & \\multicolumn{1}{c|}{FP} & \\multicolumn{1}{c|}{TN} & \\multicolumn{1}{c|}{FN} & \\multicolumn{1}{c|}{FP\\textsubscript{t}} & \\multicolumn{1}{c|}{P\\textsubscript{m}} & \\multicolumn{1}{c|}{R\\textsubscript{m}} & \\multicolumn{1}{c|}{F1\\textsubscript{m}} \\\\
            \\hline
    """
        prev_temp = None
        for model in table_model_order:
            if model in self.results or model == "AVERAGE":
                table_with_number += "\\multicolumn{1}{|l|}{\\multirow{6}{*}{\\rotatebox{90}{"+model_text_map[model]+"}}} & "
                knowledge_counter = 0
                for knowledge_type in knowledge_order:
                    if knowledge_counter != 0:
                        table_with_number += "\multicolumn{1}{|l|}{}                                         & "

                    table_with_number += "\multicolumn{1}{|c|}{\multirow{2}{*}{" + knowledge_text_map[knowledge_type] + "}}       & "
                    knowledge_counter += 1
                    context_counter = 0
                    for context_type in context_order:
                        if context_counter != 0:
                            table_with_number += "\multicolumn{1}{|l|}{}                                         & "
                            table_with_number += "\multicolumn{1}{|c|}{}                                           & "
                        table_with_number += context_text_map[context_type] + " & "
                        context_counter += 1

                        scheme_counter = 0
                        for scheme_type in scheme_order:
                            if model != "AVERAGE":
                                res = self.get_result(model).get_result(scheme_type, knowledge_type, context_type)
                                if knowledge_type == "NoKnowledgePrompt":
                                    res.TP *= 3
                                    res.FP *= 3
                                    res.FN *= 3
                                    res.TN *= 3
                                    res.FP_type *= 3
                                    # print("Set three times for NoKnowledgePrompt")
                                if scheme_counter == 0:
                                    table_with_number += " \\multicolumn{1}{r|}{" + str(res.TP) + "} & \\multicolumn{1}{r|}{" + str(res.FP) + "} & \\multicolumn{1}{r|}{" + str(res.TN) + "} & \\multicolumn{1}{r|}{" + str(res.FN) + "} & \\multicolumn{1}{r|}{" + str(res.FP_type) + "} & \\multicolumn{1}{r|}{" + ('%.2f' % (res.precision*100)) + "} & \\multicolumn{1}{r|}{" + ('%.2f' % (res.recall*100)) + "} & \\multicolumn{1}{r|}{" + ('%.2f' % (res.f1*100)) + "}"
                                else:
                                    raw_res = self.get_result(model).get_result("RawSchemePrompt", knowledge_type, context_type)
                                    table_with_number += " \\multicolumn{1}{r|}{" + str(res.TP) + arrow_true_case(res.TP, raw_res.TP) + "} & \\multicolumn{1}{r|}{" + str(res.FP) + arrow_false_case(res.FP, raw_res.FP) + "} & \\multicolumn{1}{r|}{" + str(res.TN) + arrow_true_case(res.TN, raw_res.TN) + "} & \\multicolumn{1}{r|}{" + str(res.FN) + arrow_false_case(res.FN, raw_res.FN) + "} & \\multicolumn{1}{r|}{" + str(res.FP_type) + arrow_false_case(res.FP_type, raw_res.FP_type) + "} & \\multicolumn{1}{r|}{" + ('%.2f' % (res.precision*100)) + arrow_true_case(res.precision, raw_res.precision) + "} & \\multicolumn{1}{r|}{" + ('%.2f' % (res.recall*100)) + arrow_true_case(res.recall, raw_res.recall) + "} & \\multicolumn{1}{r|}{" + ('%.2f' % (res.f1*100)) + arrow_true_case(res.f1, raw_res.f1) + "}"
                                if scheme_counter == 0:
                                    table_with_number += " &"
                                else:
                                    table_with_number += "\\\\\n"
                                scheme_counter += 1
                            else:
                                temp_res = Result()
                                temp_res_counter = 0
                                for model in table_model_order:
                                    if model in self.results:
                                        res = self.get_result(model).get_result(scheme_type, knowledge_type, context_type)
                                        temp_res.TP += res.TP
                                        temp_res.FP += res.FP
                                        temp_res.FN += res.FN
                                        temp_res.TN += res.TN
                                        temp_res.FP_type += res.FP_type
                                        temp_res_counter += 1
                                
                                # calculate the average
                                temp_res.TP /= temp_res_counter
                                temp_res.FP /= temp_res_counter
                                temp_res.FN /= temp_res_counter
                                temp_res.TN /= temp_res_counter
                                temp_res.FP_type /= temp_res_counter
                                if scheme_counter == 0:
                                    table_with_number += " \\multicolumn{1}{r|}{" + "%.02f" % temp_res.TP + "} & \\multicolumn{1}{r|}{" + "%.02f" % temp_res.FP + "} & \\multicolumn{1}{r|}{" + "%.02f" % temp_res.TN + "} & \\multicolumn{1}{r|}{" + "%.02f" % temp_res.FN + "} & \\multicolumn{1}{r|}{" + "%.02f" % temp_res.FP_type + "} & \\multicolumn{1}{r|}{" + ('%.02f' % (temp_res.precision*100)) + "} & \\multicolumn{1}{r|}{" + ('%.02f' % (temp_res.recall*100)) + "} & \\multicolumn{1}{r|}{" + ('%.02f' % (temp_res.f1*100)) + "}"
                                else:
                                    raw_res = prev_temp
                                    table_with_number += " \\multicolumn{1}{r|}{" + "%.02f" % temp_res.TP + arrow_true_case(temp_res.TP, raw_res.TP) + "} & \\multicolumn{1}{r|}{" + "%.02f" % temp_res.FP + arrow_false_case(temp_res.FP, raw_res.FP) + "} & \\multicolumn{1}{r|}{" + "%.02f" % temp_res.TN + arrow_true_case(temp_res.TN, raw_res.TN) + "} & \\multicolumn{1}{r|}{" + "%.02f" % temp_res.FN + arrow_false_case(temp_res.FN, raw_res.FN) + "} & \\multicolumn{1}{r|}{" + "%.02f" % temp_res.FP_type + arrow_false_case(temp_res.FP_type, raw_res.FP_type) + "} & \\multicolumn{1}{r|}{" + ('%.02f' % (temp_res.precision*100)) + arrow_true_case(temp_res.precision, raw_res.precision) + "} & \\multicolumn{1}{r|}{" + ('%.02f' % (temp_res.recall*100)) + arrow_true_case(temp_res.recall, raw_res.recall) + "} & \\multicolumn{1}{r|}{" + ('%.02f' % (temp_res.f1*100)) + arrow_true_case(temp_res.f1, raw_res.f1) + "}"
                                if scheme_counter == 0:
                                    table_with_number += " &"
                                else:
                                    table_with_number += "\\\\\n"
                                scheme_counter += 1
                                prev_temp = temp_res

                        if context_counter == 2 and knowledge_counter == 3:
                            table_with_number += "\\hline\n"
                        elif context_counter == 2:
                            table_with_number += "\\cline{2-19}\n"

        # end of table
        table_with_number += """\\end{tabular}
    }
    \\begin{flushleft}
        1. ``C'' and ``N'' represent the results with context and without context, respectively. \\\\
        2. \\dataUpC~and \\dataDownC~indicate better or worse values compared to the Raw column.
    \\end{flushleft}
\\end{table*}"""

        return table_with_number
