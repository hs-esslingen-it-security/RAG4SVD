#!/usr/bin/env python3
"""
General code graph compression and natural language description tool:
1) Build graph representations from input code (Priority: Precise C AST/CFG/DFG; Fallback: General heuristic graph)
2) Filter AST/CFG/DFG by A/B/C granularity
3) Convert filtered graphs to natural language (Context-oriented for vulnerability mining)

Usage:
    python vuln_flow_analyzer.py <source_file> [--output-dir <dir>] [--detail-level A|B|C|all]
"""


import argparse
import json
import os
import re
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Any, Set


DETAIL_LEVELS = {"A", "B", "C"}
LEVEL_ALIAS = {
    "a": "A", "b": "B", "c": "C",
    "low": "A", "medium": "B", "high": "C",
}

AST_KEEP_BASE = {
    "File", "Typedef", "Struct", "FuncDef", "Decl", "ArrayDecl",
    "Assignment", "FuncCall", "If", "For", "While", "Return",
    "UnaryOp", "BinaryOp", "Constant", "ID", "StructRef", "Cast",
}
AST_NOISE = {"TypeDecl", "IdentifierType", "PtrDecl", "ExprList", "Compound"}


def normalize_detail_level(level: str) -> str:
    lv = (level or "B").strip().lower()
    if lv == "all":
        return "all"
    return LEVEL_ALIAS.get(lv, lv.upper())


def detect_language(file_path: str, code: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext in {".c", ".h"}:
        return "c"
    if ext in {".cpp", ".cc", ".cxx", ".hpp"}:
        return "cpp"
    if ext in {".py"}:
        return "python"
    if ext in {".js", ".jsx", ".ts", ".tsx"}:
        return "javascript"
    if ext in {".java"}:
        return "java"

    if "#include" in code or re.search(r"\bint\s+main\s*\(", code):
        return "c"
    if re.search(r"\bdef\s+\w+\s*\(", code):
        return "python"
    if re.search(r"\bfunction\s+\w+\s*\(", code):
        return "javascript"
    return "unknown"


def coord_line(coord: Any) -> int:
    if not coord:
        return -1
    if isinstance(coord, str):
        parts = coord.split(":")
        if len(parts) >= 2 and parts[-2].isdigit():
            return int(parts[-2])
    return -1


def safe_read(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def build_precise_c_graphs(source_file: str) -> Dict[str, Any]:
    from pycparser import parse_file
    import generate_graphs as gg

    script_dir = os.path.dirname(os.path.abspath(__file__))
    fake_libc = os.path.join(script_dir, "fake_libc_include")
    if not os.path.isdir(fake_libc):
        raise FileNotFoundError(f"未找到 fake_libc_include: {fake_libc}")

    ast = parse_file(
        source_file,
        use_cpp=True,
        cpp_path="gcc",
        cpp_args=["-E", f"-I{fake_libc}", "-D__attribute__(x)="],
    )

    ast_json = gg.build_ast(ast, source_file=source_file)
    cfg_json = gg.build_cfg(ast)
    dfg_json = gg.build_dfg(ast)

    return {
        "mode": "precise_c",
        "ast": ast_json,
        "cfg": cfg_json,
        "dfg": dfg_json,
    }


def build_heuristic_graphs(code: str, language: str, source_file: str) -> Dict[str, Any]:
    lines = code.splitlines()

    ast_nodes = []
    ast_edges = []
    root_id = "root"
    ast_nodes.append({"id": root_id, "type": "File", "label": os.path.basename(source_file), "coord": f"{source_file}:1:1"})

    cfg = {"global": {"nodes": [{"id": "entry_global", "type": "Entry", "label": "global ENTRY", "coord": None}], "edges": []}}
    dfg = {"global": {"nodes": [], "edges": []}}

    last_cfg_id = "entry_global"
    var_last_def = {}

    for idx, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("//") or line.startswith("#"):
            continue

        node_id = f"line_{idx}"
        ntype = "Stmt"
        label = line[:140]

        if re.search(r"\bif\b", line):
            ntype = "If"
        elif re.search(r"\bfor\b|\bwhile\b", line):
            ntype = "Loop"
        elif re.search(r"\breturn\b", line):
            ntype = "Return"
        elif re.search(r"\w+\s*\([^)]*\)", line):
            ntype = "CallOrDecl"

        ast_nodes.append({"id": node_id, "type": ntype, "label": label, "coord": f"{source_file}:{idx}:1"})
        ast_edges.append({"from": root_id, "to": node_id, "child_name": "line"})

        cfg["global"]["nodes"].append({"id": node_id, "type": ntype, "label": label, "coord": f"{source_file}:{idx}:1"})
        cfg["global"]["edges"].append({"from": last_cfg_id, "to": node_id, "label": ""})
        last_cfg_id = node_id

        dfg["global"]["nodes"].append({"id": node_id, "type": ntype, "label": label, "coord": f"{source_file}:{idx}:1"})

        assign_match = re.match(r"(?:\w+[\w\s\*]+\s+)?(\w+)\s*=\s*(.+)", line)
        if assign_match:
            lhs = assign_match.group(1)
            rhs = assign_match.group(2)
            used_vars = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", rhs)
            for v in used_vars:
                if v in var_last_def:
                    dfg["global"]["edges"].append({"from": var_last_def[v], "to": node_id, "var": v})
            var_last_def[lhs] = node_id
        else:
            used_vars = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", line)
            for v in used_vars:
                if v in var_last_def:
                    dfg["global"]["edges"].append({"from": var_last_def[v], "to": node_id, "var": v})

    cfg["global"]["nodes"].append({"id": "exit_global", "type": "Exit", "label": "global EXIT", "coord": None})
    cfg["global"]["edges"].append({"from": last_cfg_id, "to": "exit_global", "label": ""})

    return {
        "mode": f"heuristic_{language}",
        "ast": {"nodes": ast_nodes, "edges": ast_edges},
        "cfg": cfg,
        "dfg": dfg,
    }


def build_ast_index(ast_json: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, List[str]], Dict[str, str]]:
    nodes = ast_json.get("nodes", [])
    edges = ast_json.get("edges", [])
    by_id = {n["id"]: n for n in nodes}
    children = defaultdict(list)
    parent = {}
    for e in edges:
        children[e["from"]].append(e["to"])
        parent[e["to"]] = e["from"]
    return by_id, children, parent


def subtree_nodes(root_id: str, children: Dict[str, List[str]]) -> List[str]:
    out = []
    q = deque([root_id])
    seen = set()
    while q:
        cur = q.popleft()
        if cur in seen:
            continue
        seen.add(cur)
        out.append(cur)
        for nxt in children.get(cur, []):
            q.append(nxt)
    return out


def extract_func_name(func_node_id: str, by_id: Dict[str, Dict[str, Any]], children: Dict[str, List[str]]) -> str:
    for cid in children.get(func_node_id, []):
        n = by_id.get(cid, {})
        if n.get("type") == "Decl" and ":" in n.get("label", ""):
            return n["label"].split(":", 1)[1].strip()
    return func_node_id


def simplify_func_name(name: str) -> str:
    m = re.match(r"(.+)_\d+$", name)
    return m.group(1) if m else name


def filter_ast(ast_json: Dict[str, Any], level: str) -> Dict[str, Any]:
    by_id, children, _ = build_ast_index(ast_json)
    all_nodes = ast_json.get("nodes", [])

    typedefs = []
    func_defs = []
    for n in all_nodes:
        t = n.get("type")
        if t == "Typedef":
            typedefs.append(n)
        if t == "FuncDef":
            func_defs.append(n)

    fn_items_map: Dict[str, List[Dict[str, Any]]] = {}
    fn_line_map: Dict[str, int] = {}

    if func_defs:
        for fn in func_defs:
            fn_id = fn["id"]
            fn_name = extract_func_name(fn_id, by_id, children)
            ids = subtree_nodes(fn_id, children)
            fn_items_map[fn_name] = [by_id[i] for i in ids if i in by_id]
            fn_line_map[fn_name] = coord_line(fn.get("coord"))
    else:
        # Heuristic: If no FuncDef, infer boundaries via code lines
        line_nodes = [
            n for n in all_nodes
            if n.get("id") != "root" and coord_line(n.get("coord")) > 0
        ]
        line_nodes.sort(key=lambda x: coord_line(x.get("coord")))

        current_fn = "global"
        depth = 0
        fn_items_map[current_fn] = []
        fn_line_map[current_fn] = 1

        fn_decl_re = re.compile(r"^\s*[\w\*\s]+\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^;]*\)\s*\{")
        for n in line_nodes:
            lbl = n.get("label", "")
            m = fn_decl_re.match(lbl)
            if m and depth == 0:
                current_fn = m.group(1)
                if current_fn not in fn_items_map:
                    fn_items_map[current_fn] = []
                    fn_line_map[current_fn] = coord_line(n.get("coord"))
            fn_items_map.setdefault(current_fn, []).append(n)

            depth += lbl.count("{")
            depth -= lbl.count("}")
            if depth <= 0:
                depth = 0
                current_fn = "global"

    functions = []
    signature_groups = defaultdict(list)

    for fn_name, items in fn_items_map.items():
        kept_items = []
        for x in items:
            t = x.get("type", "")
            if t in AST_NOISE:
                continue
            if level == "A":
                if t in {"FuncDef", "Decl", "ArrayDecl", "FuncCall", "CallOrDecl", "If", "For", "While", "Loop", "Return", "Assignment", "Struct", "Typedef", "Stmt"}:
                    kept_items.append(x)
            elif level == "B":
                if t in AST_KEEP_BASE or t in {"CallOrDecl", "Loop", "Stmt"}:
                    kept_items.append(x)
            else:
                kept_items.append(x)

        call_names = []
        for x in kept_items:
            label = x.get("label", "")
            if x.get("type") == "FuncCall" and ":" in label:
                call_names.append(label.split(":", 1)[1].strip())
                continue
            m = re.search(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", label)
            is_fn_decl_like = label.rstrip().endswith("{") and re.match(r"^\s*[\w\*\s]+\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\([^;]*\)\s*\{", label)
            if m and x.get("type") in {"CallOrDecl", "Stmt"} and not is_fn_decl_like:
                name = m.group(1)
                if name not in {"if", "for", "while", "switch", "return", "sizeof"}:
                    call_names.append(name)

        summary = {
            "func": fn_name,
            "line": fn_line_map.get(fn_name, -1),
            "node_count_raw": len(items),
            "node_count_kept": len(kept_items),
            "types_kept": sorted({x.get("type", "") for x in kept_items if x.get("type")}),
            "calls": call_names,
            "calls_uniq": sorted(set(call_names)),
            "conditions": [x.get("label", x.get("type", "")) for x in kept_items if x.get("type") in {"If", "For", "While", "Loop"}],
            "returns": [x.get("label", "return") for x in kept_items if x.get("type") == "Return" or "return" in x.get("label", "")],
            "declarations": [x.get("label", "") for x in kept_items if x.get("type") in {"Decl", "CallOrDecl", "Stmt"} and ";" in x.get("label", "") and "(" not in x.get("label", "")],
            "assignments": [x.get("label", "") for x in kept_items if x.get("type") == "Assignment" or "=" in x.get("label", "")],
            "constants": [x.get("label", "") for x in kept_items if x.get("type") == "Constant"],
        }
        functions.append(summary)

        sig = (
            tuple(summary["conditions"][:3]),
            tuple(summary["calls_uniq"][:5]),
            len(summary["assignments"]),
            len(summary["returns"]),
        )
        signature_groups[(simplify_func_name(fn_name), sig)].append(fn_name)

    collapsed = []
    for (_, _), names in signature_groups.items():
        if len(names) > 1:
            collapsed.append({"representative": sorted(names)[0], "count": len(names), "members": sorted(names)})

    if not typedefs:
        inferred = []
        for n in all_nodes:
            lbl = n.get("label", "")
            if re.search(r"\bstruct\b|\btypedef\b", lbl):
                inferred.append({"label": lbl, "line": coord_line(n.get("coord"))})
        typedefs = inferred[:6]

    return {
        "level": level,
        "typedefs": [{"label": t.get("label", ""), "line": coord_line(t.get("coord"))} if isinstance(t, dict) and "coord" in t else t for t in typedefs],
        "functions": sorted(functions, key=lambda x: (x["line"] if x["line"] >= 0 else 10**9, x["func"])),
        "collapsed_isomorphic_functions": collapsed,
    }


def build_cfg_index(g: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, List[Tuple[str, str]]], Dict[str, int], Dict[str, int], str, str]:
    nodes = g.get("nodes", [])
    edges = g.get("edges", [])
    node_by_id = {n["id"]: n for n in nodes}
    out_adj = defaultdict(list)
    indeg = defaultdict(int)
    outdeg = defaultdict(int)
    for e in edges:
        fr = e["from"]
        to = e["to"]
        lb = e.get("label", "")
        out_adj[fr].append((to, lb))
        indeg[to] += 1
        outdeg[fr] += 1
    entry = next((n["id"] for n in nodes if n.get("type") == "Entry"), "")
    exit_node = next((n["id"] for n in nodes if n.get("type") == "Exit"), "")
    return node_by_id, out_adj, indeg, outdeg, entry, exit_node


def enumerate_paths_cfg(out_adj: Dict[str, List[Tuple[str, str]]], entry: str, exit_node: str, cap: int) -> List[List[Tuple[str, str]]]:
    if not entry or not exit_node:
        return []
    paths = []
    q = deque([(entry, [])])
    steps = 0
    while q and len(paths) < cap and steps < cap * 300:
        steps += 1
        cur, path = q.popleft()
        if cur == exit_node:
            paths.append(path)
            continue
        for nxt, lb in out_adj.get(cur, []):
            if sum(1 for pid, _ in path if pid == nxt) > 1:
                continue
            q.append((nxt, path + [(nxt, lb)]))
    return paths


def filter_cfg(cfg_json: Dict[str, Any], level: str) -> Dict[str, Any]:
    out = {}
    for fn, g in cfg_json.items():
        node_by_id, out_adj, indeg, outdeg, entry, exit_node = build_cfg_index(g)
        nodes = g.get("nodes", [])

        branch_types = {"If", "ForCond", "While", "Loop", "For"}
        structural_types = {"Entry", "Exit", "Return"}.union(branch_types)

        if level == "A":
            keep_types = structural_types.union({"FuncCall"})
        elif level == "B":
            keep_types = structural_types.union({"FuncCall", "Decl", "Assignment", "UnaryOp"})
        else:
            keep_types = None

        kept_nodes = []
        for n in nodes:
            t = n.get("type", "")
            if keep_types is None or t in keep_types:
                kept_nodes.append(n)

        merged_linear_segments = 0
        if level in {"A", "B"}:
            for nid, n in node_by_id.items():
                t = n.get("type", "")
                if t in structural_types:
                    continue
                if keep_types is not None and t not in keep_types:
                    if indeg.get(nid, 0) == 1 and outdeg.get(nid, 0) == 1:
                        merged_linear_segments += 1

        branch_nodes = [n for n in nodes if n.get("type") in branch_types]
        call_nodes = [n for n in nodes if "call" in n.get("label", "").lower() or n.get("type") == "FuncCall"]

        paths = enumerate_paths_cfg(out_adj, entry, exit_node, cap=3 if level == "A" else 6 if level == "B" else 12)

        out[fn] = {
            "entry": entry,
            "exit": exit_node,
            "node_count_raw": len(nodes),
            "node_count_kept": len(kept_nodes),
            "branches": [{"label": n.get("label", ""), "line": coord_line(n.get("coord"))} for n in branch_nodes],
            "calls": [{"label": n.get("label", ""), "line": coord_line(n.get("coord"))} for n in call_nodes],
            "merged_linear_segments": merged_linear_segments,
            "paths": paths,
        }
    return out


def simplify_dfg_edges(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], level: str) -> List[Dict[str, Any]]:
    node_by_id = {n["id"]: n for n in nodes}
    in_edges = defaultdict(list)
    out_edges = defaultdict(list)
    for e in edges:
        in_edges[e["to"]].append(e)
        out_edges[e["from"]].append(e)

    interesting_types = {"Parameter", "FuncCall", "Return", "Assignment", "Decl", "If", "For", "While"}
    result = []

    for e in edges:
        fr = e["from"]
        to = e["to"]
        var = e.get("var", "?")
        fr_t = node_by_id.get(fr, {}).get("type", "")
        to_t = node_by_id.get(to, {}).get("type", "")
        if level == "A":
            if fr_t == "Parameter" or to_t in {"FuncCall", "Return"}:
                result.append(e)
        elif level == "B":
            if fr_t in interesting_types or to_t in interesting_types or var != "?":
                result.append(e)
        else:
            result.append(e)

    if level in {"A", "B"}:
        collapsed = []
        for e in result:
            mid = e["to"]
            if len(in_edges.get(mid, [])) == 1 and len(out_edges.get(mid, [])) == 1:
                mid_t = node_by_id.get(mid, {}).get("type", "")
                if mid_t not in {"Parameter", "FuncCall", "Return"}:
                    next_e = out_edges[mid][0]
                    collapsed.append({"from": e["from"], "to": next_e["to"], "var": e.get("var", "?")})
                    continue
            collapsed.append(e)
        result = collapsed

    uniq = []
    seen = set()
    for e in result:
        k = (e["from"], e["to"], e.get("var", "?"))
        if k in seen:
            continue
        seen.add(k)
        uniq.append(e)
    return uniq


def filter_dfg(dfg_json: Dict[str, Any], level: str) -> Dict[str, Any]:
    out = {}
    for fn, g in dfg_json.items():
        nodes = g.get("nodes", [])
        edges = g.get("edges", [])
        node_by_id = {n["id"]: n for n in nodes}

        simplified_edges = simplify_dfg_edges(nodes, edges, level)
        param_nodes = [n for n in nodes if n.get("type") == "Parameter"]

        chains = []
        out_adj = defaultdict(list)
        for e in simplified_edges:
            out_adj[e["from"]].append(e)

        per_param_cap = 4 if level == "A" else 8 if level == "B" else 16
        for p in param_nodes:
            pid = p["id"]
            q = deque([(pid, [pid])])
            local_count = 0
            while q and local_count < per_param_cap:
                cur, path = q.popleft()
                nxt_edges = out_adj.get(cur, [])
                if not nxt_edges:
                    if len(path) > 1:
                        chains.append(path)
                        local_count += 1
                    continue
                for ne in nxt_edges:
                    nxt = ne["to"]
                    if nxt in path:
                        continue
                    q.append((nxt, path + [nxt]))

        out[fn] = {
            "node_count_raw": len(nodes),
            "edge_count_raw": len(edges),
            "edge_count_kept": len(simplified_edges),
            "parameters": [{"id": n["id"], "label": n.get("label", ""), "line": coord_line(n.get("coord"))} for n in param_nodes],
            "edges": simplified_edges,
            "chains": chains,
            "node_labels": {nid: node_by_id.get(nid, {}).get("label", nid) for nid in node_by_id},
        }
    return out


def describe_ast(ast_filtered: Dict[str, Any], level: str) -> List[str]:
    lines = ["【AST】"]
    typedefs = ast_filtered.get("typedefs", [])
    if typedefs:
        show = typedefs[:2] if level == "A" else typedefs[:5] if level == "B" else typedefs
        lines.append("- Type/structure definition：" + "；".join([f"{t['label']}@L{t['line']}" for t in show]))

    collapsed = ast_filtered.get("collapsed_isomorphic_functions", [])
    collapsed_members = set()
    reps = set()
    for c in collapsed:
        reps.add(c["representative"])
        collapsed_members.update(c.get("members", []))

    for fn in ast_filtered.get("functions", []):
        name = fn["func"]
        if level in {"A", "B"} and name in collapsed_members and name not in reps:
            continue

        lno = fn["line"]
        if level == "A":
            lines.append(
                f"- Function {name}@L{lno}: Retained {fn['node_count_kept']}/{fn['node_count_raw']} semantic nodes;"
                f"Calls={', '.join(fn['calls_uniq'][:4]) or 'nothing'}; Branches={len(fn['conditions'])}; Returns={len(fn['returns'])}。"
            )
        elif level == "B":
            lines.append(
                f"- Function {name}@L{lno}: {len(fn['declarations'])} declarations, {len(fn['assignments'])} assignments, "
                f"{len(fn['conditions'])} branches, {len(fn['calls'])} calls."
            )
            if fn["calls_uniq"]:
                lines.append(f"  - Key call chain: {' -> '.join(fn['calls_uniq'][:8])}。")
            if fn["conditions"]:
                lines.append("  - Conditions/Loops: " + "；".join(fn["conditions"][:6]))
        else:
            lines.append(f"- Function {name}@L{lno}：")
            if fn["declarations"]:
                lines.append("  - Declarations: " + "; ".join(fn["declarations"][:20]))
            if fn["assignments"]:
                lines.append("  - Assignments: " + "; ".join(fn["assignments"][:20]))
            if fn["calls"]:
                lines.append("  - Calls: " + "; ".join(fn["calls"][:20]))
            if fn["conditions"]:
                lines.append("  - Conditions/Loops: " + "; ".join(fn["conditions"][:20]))
            if fn["returns"]:
                lines.append("  - Returns: " + "; ".join(fn["returns"][:10]))

    if collapsed:
        for c in collapsed[:10]:
            lines.append(f"- Isomorphic functions collapsed: {c['representative']} represents {c['count']} isomorphic functions.")
    return lines


def path_to_text(path: List[Tuple[str, str]], label_map: Dict[str, str], level: str) -> str:
    if not path:
        return "Entry"

    max_len = 6 if level == "A" else 14 if level == "B" else 24
    key_tokens = ("if", "for", "while", "return", "call")

    picked = []
    for i, (nid, lb) in enumerate(path):
        label = label_map.get(nid, nid)
        is_key = lb in {"True", "False", "back"} or any(k in label.lower() for k in key_tokens)
        if i < 2 or i >= len(path) - 2 or is_key:
            picked.append((nid, lb))

    dedup = []
    seen = set()
    for item in picked:
        if item in seen:
            continue
        seen.add(item)
        dedup.append(item)

    if len(dedup) > max_len:
        head = dedup[: max_len // 2]
        tail = dedup[-(max_len - len(head)):]
        shown = head + [("...", "")] + tail
    else:
        shown = dedup

    parts = []
    for nid, lb in shown:
        if nid == "...":
            parts.append("...")
            continue
        txt = label_map.get(nid, nid)
        if lb:
            txt = f"[{lb}] {txt}"
        parts.append(txt)

    return "Entry -> " + " -> ".join(parts)


def describe_cfg(cfg_filtered: Dict[str, Any], cfg_json: Dict[str, Any], level: str) -> List[str]:
    lines = ["", "【CFG】"]
    for fn, info in cfg_filtered.items():
        raw_nodes = info.get("node_count_raw", 0)
        kept_nodes = info.get("node_count_kept", 0)
        branches = info.get("branches", [])
        calls = info.get("calls", [])
        paths = info.get("paths", [])

        lines.append(
            f"- Function {fn}：Retained control points {kept_nodes}/{raw_nodes}; Branch nodes {len(branches)}; Call nodes {len(calls)}; "
            f"Linear segments merged {info.get('merged_linear_segments', 0)}。"
        )

        if branches and level != "A":
            btxt = "；".join([f"{b['label']}@L{b['line']}" for b in branches[:12]])
            lines.append(f"  - Branch/Loop nodes: {btxt}")

        if paths:
            nodes_map = {n["id"]: n.get("label", n["id"]) for n in cfg_json.get(fn, {}).get("nodes", [])}
            show = paths[:2] if level == "A" else paths[:4] if level == "B" else paths[:8]
            for idx, p in enumerate(show, start=1):
                lines.append(f"  - Path {idx}: {path_to_text(p, nodes_map, level)}")
    return lines


def describe_dfg(dfg_filtered: Dict[str, Any], level: str) -> List[str]:
    lines = ["", "【DFG】"]
    for fn, info in dfg_filtered.items():
        lines.append(
            f"- Function {fn}: Edges retained {info.get('edge_count_kept', 0)}/{info.get('edge_count_raw', 0)}；"
            f"Parameter sources {len(info.get('parameters', []))}; Extracted data chains {len(info.get('chains', []))}."
        )

        params = info.get("parameters", [])
        if params and level != "A":
            lines.append("  - Parameter sources: " + "；".join([f"{p['label']}@L{p['line']}" for p in params[:12]]))

        chains = info.get("chains", [])
        labels = info.get("node_labels", {})
        show = chains[:3] if level == "A" else chains[:6] if level == "B" else chains[:12]
        for ch in show:
            txt = " -> ".join([labels.get(nid, nid) for nid in ch])
            lines.append(f"  - Data chain: {txt}")

    return lines


def build_prompt(source_file: str, mode: str, level: str, ast_filtered: Dict[str, Any], cfg_filtered: Dict[str, Any], dfg_filtered: Dict[str, Any], cfg_json: Dict[str, Any]) -> str:
    header = [""]
    lines = []
    lines.extend(header)
    lines.extend(describe_ast(ast_filtered, level))
    lines.extend(describe_cfg(cfg_filtered, cfg_json, level))
    lines.extend(describe_dfg(dfg_filtered, level))
    return "\n".join(lines)


def analyze_with_level(graphs: Dict[str, Any], source_file: str, level: str) -> Dict[str, Any]:
    ast_filtered = filter_ast(graphs["ast"], level)
    cfg_filtered = filter_cfg(graphs["cfg"], level)
    dfg_filtered = filter_dfg(graphs["dfg"], level)

    prompt_text = build_prompt(
        source_file=source_file,
        mode=graphs["mode"],
        level=level,
        ast_filtered=ast_filtered,
        cfg_filtered=cfg_filtered,
        dfg_filtered=dfg_filtered,
        cfg_json=graphs["cfg"],
    )

    retained = {
        "detail_level": level,
        "ast_kept": {
            "node_types": sorted({t for f in ast_filtered.get("functions", []) for t in f.get("types_kept", [])}),
            "collapsed_isomorphic_functions": ast_filtered.get("collapsed_isomorphic_functions", []),
        },
        "cfg_kept": [
            "Entry/Exit",
            "Conditional branch/loop nodes",
            "Function call nodes",
            "Retained skeleton paths after linear segment folding"
        ],
        "dfg_kept": [
            "Parameter source nodes",
            "Cross-statement def-use edges",
            "Data chains leading to calls/returns/critical statements"
        ],
        "redundancy_removed": [
            "Type expansion noise nodes (TypeDecl/IdentifierType/PtrDecl, etc.)",
            "Pure linear statement fragments without branches or calls",
            "Intermediate transfer edges that do not affect major propagation chains"
        ]
    }

    graph_out = {
        "mode": graphs["mode"],
        "language": graphs.get("language", "unknown"),
        "detail_level": level,
        "filtered_ast": ast_filtered,
        "filtered_cfg": cfg_filtered,
        "filtered_dfg": dfg_filtered,
    }

    return {
        "prompt_text": prompt_text,
        "retained": retained,
        "graph_out": graph_out,
    }

def build_prompt_no_ast(source_file: str, mode: str, level: str, cfg_filtered: Dict[str, Any], dfg_filtered: Dict[str, Any], cfg_json: Dict[str, Any]) -> str:
    header = [""]
    lines = []
    lines.extend(header)
    lines.extend(describe_cfg(cfg_filtered, cfg_json, level))
    lines.extend(describe_dfg(dfg_filtered, level))
    return "\n".join(lines)


def analyze_with_level_no_ast(graphs: Dict[str, Any], source_file: str, level: str) -> Dict[str, Any]:
    cfg_filtered = filter_cfg(graphs["cfg"], level)
    dfg_filtered = filter_dfg(graphs["dfg"], level)

    prompt_text = build_prompt_no_ast(
        source_file=source_file,
        mode=graphs["mode"],
        level=level,
        cfg_filtered=cfg_filtered,
        dfg_filtered=dfg_filtered,
        cfg_json=graphs["cfg"],
    )

    retained = {
        "detail_level": level,
        "cfg_kept": [
            "Entry/Exit",
            "Conditional branch/loop nodes",
            "Function call nodes",
            "Retained skeleton paths after linear segment folding"
        ],
        "dfg_kept": [
            "Parameter source nodes",
            "Cross-statement def-use edges",
            "Data chains leading to calls/returns/critical statements"
        ],
        "redundancy_removed": [
            "Pure linear statement fragments without branches or calls",
            "Intermediate transfer edges that do not affect major propagation chains"
        ]
    }

    graph_out = {
        "mode": graphs["mode"],
        "language": graphs.get("language", "unknown"),
        "detail_level": level,
        "filtered_cfg": cfg_filtered,
        "filtered_dfg": dfg_filtered,
    }

    return {
        "prompt_text": prompt_text,
        "retained": retained,
        "graph_out": graph_out,
    }

def build_prompt_no_cfg(source_file: str, mode: str, level: str, ast_filtered: Dict[str, Any], dfg_filtered: Dict[str, Any]) -> str:
    header = [""]
    lines = []
    lines.extend(header)
    lines.extend(describe_ast(ast_filtered, level))
    lines.extend(describe_dfg(dfg_filtered, level))
    return "\n".join(lines)



def analyze_with_level_no_cfg(graphs: Dict[str, Any], source_file: str, level: str) -> Dict[str, Any]:
    ast_filtered = filter_ast(graphs["ast"], level)
    dfg_filtered = filter_dfg(graphs["dfg"], level)

    prompt_text = build_prompt_no_cfg(
        source_file=source_file,
        mode=graphs["mode"],
        level=level,
        ast_filtered=ast_filtered,
        dfg_filtered=dfg_filtered,
    )

    retained = {
        "detail_level": level,
        "ast_kept": {
            "node_types": sorted({t for f in ast_filtered.get("functions", []) for t in f.get("types_kept", [])}),
            "collapsed_isomorphic_functions": ast_filtered.get("collapsed_isomorphic_functions", []),
        },
        "dfg_kept": [
            "Parameter source nodes",
            "Cross-statement def-use edges",
            "Data chains leading to calls/returns/critical statements"
        ],
        "redundancy_removed": [
            "Type expansion noise nodes (TypeDecl/IdentifierType/PtrDecl, etc.)",
            "Intermediate transfer edges that do not affect major propagation chains"
        ]
    }

    graph_out = {
        "mode": graphs["mode"],
        "language": graphs.get("language", "unknown"),
        "detail_level": level,
        "filtered_ast": ast_filtered,
        "filtered_dfg": dfg_filtered,
    }

    return {
        "prompt_text": prompt_text,
        "retained": retained,
        "graph_out": graph_out,
    }

def build_prompt_no_dfg(source_file: str, mode: str, level: str, ast_filtered: Dict[str, Any], cfg_filtered: Dict[str, Any], cfg_json: Dict[str, Any]) -> str:
    header = [""]
    lines = []
    lines.extend(header)
    lines.extend(describe_ast(ast_filtered, level))
    lines.extend(describe_cfg(cfg_filtered, cfg_json, level))
    return "\n".join(lines)


def analyze_with_level_no_dfg(graphs: Dict[str, Any], source_file: str, level: str) -> Dict[str, Any]:
    ast_filtered = filter_ast(graphs["ast"], level)
    cfg_filtered = filter_cfg(graphs["cfg"], level)

    prompt_text = build_prompt_no_dfg(
        source_file=source_file,
        mode=graphs["mode"],
        level=level,
        ast_filtered=ast_filtered,
        cfg_filtered=cfg_filtered,
        cfg_json=graphs["cfg"],
    )

    retained = {
        "detail_level": level,
        "ast_kept": {
            "node_types": sorted({t for f in ast_filtered.get("functions", []) for t in f.get("types_kept", [])}),
            "collapsed_isomorphic_functions": ast_filtered.get("collapsed_isomorphic_functions", []),
        },
        "cfg_kept": [
            "Entry/Exit",
            "Conditional branch/loop nodes",
            "Function call nodes",
            "Retained skeleton paths after linear segment folding"
        ],
        "redundancy_removed": [
            "Type expansion noise nodes (TypeDecl/IdentifierType/PtrDecl, etc.)",
            "Pure linear statement fragments without branches or calls",
            "Intermediate transfer edges that do not affect major propagation chains"
        ]
    }

    graph_out = {
        "mode": graphs["mode"],
        "language": graphs.get("language", "unknown"),
        "detail_level": level,
        "filtered_ast": ast_filtered,
        "filtered_cfg": cfg_filtered,
    }

    return {
        "prompt_text": prompt_text,
        "retained": retained,
        "graph_out": graph_out,
    }

def run_pipeline(source_file: str, output_dir: str, detail_level: str) -> Dict[str, Any]:
    code = safe_read(source_file)
    language = detect_language(source_file, code)

    try:
        if language in {"c", "cpp"}:
            graphs = build_precise_c_graphs(source_file)
        else:
            graphs = build_heuristic_graphs(code, language, source_file)
    except Exception:
        graphs = build_heuristic_graphs(code, language, source_file)

    graphs["language"] = language
    os.makedirs(output_dir, exist_ok=True)

    levels = ["A", "B", "C"] if detail_level == "all" else [detail_level]
    output_files = {}
    retained_map = {}

    for lv in levels:
        analyzed = analyze_with_level(graphs, source_file, lv)

        suffix = lv.lower()
        graph_file = os.path.join(output_dir, f"analysis_graph_{suffix}.json")
        retained_file = os.path.join(output_dir, f"retained_elements_{suffix}.json")
        prompt_file = os.path.join(output_dir, f"vuln_prompt_{suffix}.txt")

        with open(graph_file, "w", encoding="utf-8") as f:
            json.dump(analyzed["graph_out"], f, ensure_ascii=False, indent=2)
        with open(retained_file, "w", encoding="utf-8") as f:
            json.dump(analyzed["retained"], f, ensure_ascii=False, indent=2)
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(analyzed["prompt_text"])

        output_files[lv] = {
            "analysis_graph": graph_file,
            "retained_elements": retained_file,
            "prompt": prompt_file,
        }
        retained_map[lv] = analyzed["retained"]

    return {
        "mode": graphs["mode"],
        "language": language,
        "detail_level": detail_level,
        "output_files": output_files,
        "retained": retained_map,
    }


def analyze_code_str(code: str, detail_level: str = "B", source_name: str = "code.c") -> Dict[str, Any]:
    """
    Analyze the code string and return the analysis results.

    Args:
        code: The source code string.
        detail_level: Detail level "A", "B", "C", or "all".
        source_name: Source file name (used for language detection and display), default is "code.c".

    Returns:
        A dictionary containing the following keys:
        - mode: Graph construction mode.
        - language: Detected language.
        - detail_level: The detail level used.
        - results: Detailed results for each level, including:
          - prompt_text: Natural language description text.
          - retained: Information on retained elements.
          - graph_out: Filtered graph data.
    """
    language = detect_language(source_name, code)

    try:
        if language in {"c", "cpp"}:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False, encoding='utf-8') as tmp:
                tmp.write(code)
                tmp_path = tmp.name
            try:
                graphs = build_precise_c_graphs(tmp_path)
            finally:
                os.unlink(tmp_path)
        else:
            graphs = build_heuristic_graphs(code, language, source_name)
    except Exception:
        graphs = build_heuristic_graphs(code, language, source_name)

    graphs["language"] = language

    levels = ["A", "B", "C"] if detail_level == "all" else [detail_level]
    results = {}

    for lv in levels:
        analyzed = analyze_with_level(graphs, source_name, lv)
        results[lv] = {
            "prompt_text": analyzed["prompt_text"],
            "retained": analyzed["retained"],
            "graph_out": analyzed["graph_out"],
        }

    return {
        "mode": graphs["mode"],
        "language": language,
        "detail_level": detail_level,
        "results": results,
    }

def analyze_code_str_no_ast(code: str, detail_level: str = "B", source_name: str = "code.c") -> Dict[str, Any]:
    """
    Analyze the code string and return the analysis results (excluding AST).

    Args:
        code: The source code string.
        detail_level: Detail level "A", "B", "C", or "all".
        source_name: Source file name (used for language detection and display), default is "code.c".

    Returns:
        A dictionary containing the following keys:
        - mode: Graph construction mode.
        - language: Detected language.
        - detail_level: The detail level used.
        - results: Detailed results for each level, including:
          - prompt_text: Natural language description text.
          - retained: Information on retained elements.
          - graph_out: Filtered graph data.
    """
    language = detect_language(source_name, code)

    try:
        if language in {"c", "cpp"}:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False, encoding='utf-8') as tmp:
                tmp.write(code)
                tmp_path = tmp.name
            try:
                graphs = build_precise_c_graphs(tmp_path)
            finally:
                os.unlink(tmp_path)
        else:
            graphs = build_heuristic_graphs(code, language, source_name)
    except Exception:
        graphs = build_heuristic_graphs(code, language, source_name)

    graphs["language"] = language

    levels = ["A", "B", "C"] if detail_level == "all" else [detail_level]
    results = {}

    for lv in levels:
        analyzed = analyze_with_level_no_ast(graphs, source_name, lv)
        results[lv] = {
            "prompt_text": analyzed["prompt_text"],
            "retained": analyzed["retained"],
            "graph_out": analyzed["graph_out"],
        }

    return {
        "mode": graphs["mode"],
        "language": language,
        "detail_level": detail_level,
        "results": results,
    }

def analyze_code_str_no_cfg(code: str, detail_level: str = "B", source_name: str = "code.c") -> Dict[str, Any]:
    """
    Analyze the code string and return the analysis results (excluding CFG).

    Args:
        code: The source code string.
        detail_level: Detail level "A", "B", "C", or "all".
        source_name: Source file name (used for language detection and display), default is "code.c".

    Returns:
        A dictionary containing the following keys:
        - mode: Graph construction mode.
        - language: Detected language.
        - detail_level: The detail level used.
        - results: Detailed results for each level, including:
          - prompt_text: Natural language description text.
          - retained: Information on retained elements.
          - graph_out: Filtered graph data.
    """
    language = detect_language(source_name, code)

    try:
        if language in {"c", "cpp"}:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False, encoding='utf-8') as tmp:
                tmp.write(code)
                tmp_path = tmp.name
            try:
                graphs = build_precise_c_graphs(tmp_path)
            finally:
                os.unlink(tmp_path)
        else:
            graphs = build_heuristic_graphs(code, language, source_name)
    except Exception:
        graphs = build_heuristic_graphs(code, language, source_name)

    graphs["language"] = language

    levels = ["A", "B", "C"] if detail_level == "all" else [detail_level]
    results = {}

    for lv in levels:
        analyzed = analyze_with_level_no_cfg(graphs, source_name, lv)
        results[lv] = {
            "prompt_text": analyzed["prompt_text"],
            "retained": analyzed["retained"],
            "graph_out": analyzed["graph_out"],
        }

    return {
        "mode": graphs["mode"],
        "language": language,
        "detail_level": detail_level,
        "results": results,
    }

def analyze_code_str_no_dfg(code: str, detail_level: str = "B", source_name: str = "code.c") -> Dict[str, Any]:
    """
    Analyze the code string and return the analysis results (excluding DFG).

    Args:
        code: The source code string.
        detail_level: Detail level "A", "B", "C", or "all".
        source_name: Source file name (used for language detection and display), default is "code.c".

    Returns:
        A dictionary containing the following keys:
        - mode: Graph construction mode.
        - language: Detected language.
        - detail_level: The detail level used.
        - results: Detailed results for each level, including:
          - prompt_text: Natural language description text.
          - retained: Information on retained elements.
          - graph_out: Filtered graph data.
    """
    language = detect_language(source_name, code)

    try:
        if language in {"c", "cpp"}:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False, encoding='utf-8') as tmp:
                tmp.write(code)
                tmp_path = tmp.name
            try:
                graphs = build_precise_c_graphs(tmp_path)
            finally:
                os.unlink(tmp_path)
        else:
            graphs = build_heuristic_graphs(code, language, source_name)
    except Exception:
        graphs = build_heuristic_graphs(code, language, source_name)

    graphs["language"] = language

    levels = ["A", "B", "C"] if detail_level == "all" else [detail_level]
    results = {}

    for lv in levels:
        analyzed = analyze_with_level_no_dfg(graphs, source_name, lv)
        results[lv] = {
            "prompt_text": analyzed["prompt_text"],
            "retained": analyzed["retained"],
            "graph_out": analyzed["graph_out"],
        }

    return {
        "mode": graphs["mode"],
        "language": language,
        "detail_level": detail_level,
        "results": results,
    }

def main():
    parser = argparse.ArgumentParser(description="General Tool for Graph-to-Natural Language Translation for Vulnerability Analysis")
    parser.add_argument("source_file", help="Input source file path")
    parser.add_argument("--output-dir", default=None, help="Output directory, default <source_dir>/output")
    parser.add_argument("--detail-level", default="C", help="A|B|C|all (low|medium|high also supported)")
    args = parser.parse_args()

    source_file = os.path.abspath(args.source_file)
    if not os.path.isfile(source_file):
        raise FileNotFoundError(f"Input file does not exist: {source_file}")

    output_dir = args.output_dir or os.path.join(os.path.dirname(source_file), "output")
    output_dir = os.path.abspath(output_dir)

    detail_level = normalize_detail_level(args.detail_level)
    if detail_level != "all" and detail_level not in DETAIL_LEVELS:
        raise ValueError("--detail-level must be A|B|C|all (or low|medium|high)")

    result = run_pipeline(source_file, output_dir, detail_level)

    print("[✓] Analysis Complete")
    print(f"  Mode: {result['mode']} Language: {result['language']} Granularity: {result['detail_level']}")
    for lv, files in result["output_files"].items():
        print(f"  [{lv}] Output: {files['analysis_graph']}")
        print(f"  [{lv}] Output: {files['retained_elements']}")
        print(f"  [{lv}] Output: {files['prompt']}")


if __name__ == "__main__":
    main()
