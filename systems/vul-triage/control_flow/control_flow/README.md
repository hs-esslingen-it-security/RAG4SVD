# vuln_flow_analyzer.py — Code Graph Compression and Natural Language Description Tool

Builds AST/CFG/DFG graph representations from C/C++ source code, filters them at different levels of detail, and converts the resulting graphs into natural-language descriptions for vulnerability analysis.

## Installation

```bash
pip install pycparser
```

Additionally, a system installation of `gcc` is required (used for C preprocessing). On macOS, the Xcode Command Line Tools are sufficient.

The project already includes the following auxiliary files, so no additional installation is required:

- `generate_graphs.py` — Backend graph construction module (AST/CFG/DFG/PDG)
- `fake_libc_include/` — Minimal standard library headers required by `pycparser`

---

## Workflow

### Overall Pipeline

```
Source Code (.c/.cpp)
    │
    ▼
┌──────────────────────────────┐
│ 1. Language Detection        │  Determine the language from the file extension
│                              │  or source code characteristics
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ 2. Graph Construction        │  Prefer `precise_c` mode
│                              │  (accurate parsing with pycparser)
│                              │  If parsing fails, automatically fall back
│                              │  to `heuristic_c` mode (regex-based heuristics)
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ 3. Graph Filtering           │  Filter AST/CFG/DFG nodes and edges
│    (Detail Levels A/B/C)     │  according to the selected detail level
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ 4. Natural Language Gen      │  Convert the filtered graph into a
│                              │  structured natural-language description
└──────────────┬───────────────┘
               ▼

Output Files (JSON + TXT)
```

### Graph Construction Modes

| Mode | Trigger | Method | Accuracy |
|------|---------|--------|----------|
| `precise_c` | C/C++ source successfully parsed by `pycparser` | Uses `gcc -E` preprocessing, builds a complete AST with `pycparser`, then generates CFG/DFG using `generate_graphs.py` | High: precise function-level call relationships, control flow, and data flow |
| `heuristic_c` | Automatic fallback when `pycparser` fails | Performs line-by-line regex-based analysis to heuristically identify functions, calls, control structures, and data flow | Medium: function boundaries or some call relationships may be incomplete |

### Detail Levels

| Level | Alias | AST Retention Strategy | CFG Path Limit | DFG Chain Limit |
|------|------|------------------------|---------------|----------------|
| **A** | low | Keep only function definitions, declarations, function calls, branches, and return statements | 3 paths | 4 chains |
| **B** | medium | Includes everything from Level A plus assignments, constants, operators, etc. | 6 paths | 8 chains |
| **C** | high | Retains all semantic nodes (removing only type-expansion noise) | 12 paths | 16 chains |

---

## Usage

```bash
python vuln_flow_analyzer.py <source_file> [--output-dir <dir>] [--detail-level A|B|C|all]
```

### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `source_file` | Yes | — | Path to the input source file |
| `--output-dir` | No | `<source_dir>/output` | Output directory |
| `--detail-level` | No | `C` | Detail level: `A`, `B`, `C`, or `all` (also accepts `low`, `medium`, `high`) |

### Examples

```bash
# Analyze a single file using the default (Level C)
python vuln_flow_analyzer.py test_snippets/vuln_01_stack_bof.c

# Specify the output directory and generate all detail levels
python vuln_flow_analyzer.py test_snippets/vuln_01_stack_bof.c \
    --output-dir output/vuln_01 \
    --detail-level all

# Generate only Level B
python vuln_flow_analyzer.py test_snippets/safe_01_string_utils.c \
    --output-dir output/safe_01 \
    --detail-level B
```

---

## Input

A single C/C++ source file (`.c`, `.h`, `.cpp`, `.cc`, etc.).

Python, JavaScript, and Java source files are also supported and will be analyzed using the `heuristic_c` mode.

---

## Output

When `--detail-level all` is specified, the output directory contains the following nine files:

```
output/
├── vuln_prompt_a.txt          # Natural-language description (Level A)
├── vuln_prompt_b.txt          # Natural-language description (Level B)
├── vuln_prompt_c.txt          # Natural-language description (Level C)
├── analysis_graph_a.json      # Filtered graph data (Level A)
├── analysis_graph_b.json      # Filtered graph data (Level B)
├── analysis_graph_c.json      # Filtered graph data (Level C)
├── retained_elements_a.json   # Retained element summary (Level A)
├── retained_elements_b.json   # Retained element summary (Level B)
└── retained_elements_c.json   # Retained element summary (Level C)
```

### Output Files

| File | Format | Description |
|------|--------|-------------|
| `vuln_prompt_*.txt` | Plain text | Structured natural-language description containing **AST**, **CFG**, and **DFG** sections, including function signatures, call chains, control-flow paths, and data-flow chains |
| `analysis_graph_*.json` | JSON | Filtered graph representation, including `filtered_ast` (function list and node-type statistics), `filtered_cfg` (control-flow paths), and `filtered_dfg` (data-flow edges and chains) |
| `retained_elements_*.json` | JSON | Metadata describing which node and edge types are retained or removed at the selected detail level |

### Example Natural-Language Description (Level B)

```
File: test_snippets/vuln_01_stack_bof.c
Graph Construction Mode: precise_c

[AST]

- Type/Structure Definitions: Struct:UserInfo@L11
- Function init_user@L17: 0 declarations, 0 assignments, 0 branches, 1 function call.
  - Call chain: memset.
- Function read_username@L31: 1 declaration, 0 assignments, 0 branches, 3 function calls.
  - Call chain: gets -> printf -> strcpy.
...

[CFG]

- Function read_username:
  Retained control points: 8/8
  Branch nodes: 0
  Call nodes: 3
  Collapsed linear segments: 0

  - Path 1:
    Entry -> call gets -> call printf -> call strcpy -> return name -> Exit
...

[DFG]

- Function read_username:
  Retained edges: 4/5
  Parameter sources: 1
  Extracted chains: 2

  - Parameter source: param:u@L31
  - Data-flow chain: param:u -> call strcpy
...
```