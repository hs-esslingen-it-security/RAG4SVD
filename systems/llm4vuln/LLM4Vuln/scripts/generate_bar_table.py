import json
import os

def run():
    table_latex_header = """
\\begin{table}[htbp]
\\centering
\\caption{Comparison of general purpose and reasoning models on [[language]].}
\\label{tab:bar_table_[[language]]}
\\resizebox{\\linewidth}{!}{
\\begin{tabular}{cllcll}
\\toprule
\\textbf{Model} & \\textbf{Setup} & \\textbf{Metrics} & \\textbf{Model} & \\textbf{Setup} & \\textbf{Metrics} \\\\
\\midrule

"""
    table_latex_footer = """
\\bottomrule
\\end{tabular}
}
\\end{table}
"""

    result_files = [
        "outputs/solidity.new.processed.json",
        "outputs/cpp.all.json",
        "outputs/java.all.json",
        "outputs/solidity.all.json",
    ]

    general_models = [
        "gpt-4.1",
        "llama3",
        "phi3"
    ]

    reasoning_models = [
        "o4-mini",
        "deepseek",
        "qwq"
    ]

    model_display_name_map = {
        "gpt-4.1": "GPT-4.1",
        "llama3": "Llama 3 8B",
        "phi3": "Phi-3",
        "o4-mini": "o4 mini",
        "deepseek": "DeepSeek-R1",
        "qwq": "QwQ-32B"
    }

    knowledge_order = [
        "NoKnowledgePrompt",
        "OriginalKnowledgePrompt",
        "SummarizedKnowledgePrompt"
    ]

    context_order = [
        "WithContextPrompt",
        "WithoutContextPrompt"
    ]

    knowledge_short_names = {
        "NoKnowledgePrompt": "Nk",
        "OriginalKnowledgePrompt": "Ok",
        "SummarizedKnowledgePrompt": "Sk"
    }

    context_short_names = {
        "WithContextPrompt": "C",
        "WithoutContextPrompt": "N"
    }

    total_table = "" 

    for result_file in result_files:
        total_table += table_latex_header.replace("[[language]]", os.path.basename(result_file).split('.')[0].capitalize()).replace("Cpp", "C/C++")
        with open(result_file, 'r') as f:
            results = json.load(f)
            # The table is two columns, general models on the left, reasoning models on the right
            for general_model, reasoning_model in zip(general_models, reasoning_models):
                lines = ""
                # add a cell for 6 rows 1 columns, with model name

                general_metrics = results[general_model]["RawSchemePrompt"]
                reasoning_metrics = results[reasoning_model]["RawSchemePrompt"]

                # Get TP, TN, FP, FN, FP_type
                for knowledge in knowledge_order:
                    for context in context_order:
                        # Bar is like: \FiveBar{50}{80}{30}{20}{40}
                        if lines == "":
                            # This line is Model name, bar, model name, bar
                            lines += f"\\multirow{{6}}{{*}}{{\\rotatebox{{90}}{{{model_display_name_map[general_model]}}}}} & {knowledge_short_names[knowledge]}{context_short_names[context]} & \\FiveBar{{{general_metrics[knowledge][context]['TP']}}}{{{general_metrics[knowledge][context]['TN']}}}{{{general_metrics[knowledge][context]['FP']}}}{{{general_metrics[knowledge][context]['FN']}}}{{{general_metrics[knowledge][context]['FP_type']}}} & \\multirow{{6}}{{*}}{{\\rotatebox{{90}}{{{model_display_name_map[reasoning_model]}}}}} & {knowledge_short_names[knowledge]}{context_short_names[context]} & \\FiveBar{{{reasoning_metrics[knowledge][context]['TP']}}}{{{reasoning_metrics[knowledge][context]['TN']}}}{{{reasoning_metrics[knowledge][context]['FP']}}}{{{reasoning_metrics[knowledge][context]['FN']}}}{{{reasoning_metrics[knowledge][context]['FP_type']}}} \\\\\n"
                        else:
                            lines += f" & {knowledge_short_names[knowledge]}{context_short_names[context]} & \\FiveBar{{{general_metrics[knowledge][context]['TP']}}}{{{general_metrics[knowledge][context]['TN']}}}{{{general_metrics[knowledge][context]['FP']}}}{{{general_metrics[knowledge][context]['FN']}}}{{{general_metrics[knowledge][context]['FP_type']}}} & & {knowledge_short_names[knowledge]}{context_short_names[context]} & \\FiveBar{{{reasoning_metrics[knowledge][context]['TP']}}}{{{reasoning_metrics[knowledge][context]['TN']}}}{{{reasoning_metrics[knowledge][context]['FP']}}}{{{reasoning_metrics[knowledge][context]['FN']}}}{{{reasoning_metrics[knowledge][context]['FP_type']}}} \\\\\n"

                total_table += lines

            total_table += table_latex_footer
    with open("outputs/bar_table.tex", 'w') as f:
        f.write(total_table)

