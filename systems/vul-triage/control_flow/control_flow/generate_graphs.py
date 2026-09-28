"""
Generate four types of graph structures (AST / CFG / DFG / PDG) from C source code, output as JSON files.

Dependencies:
    pip install pycparser

Usage:
    python generate_graphs.py sample.c

Output directory: ./output/
    - ast.json   Abstract Syntax Tree
    - cfg.json   Control Flow Graph
    - dfg.json   Data Flow Graph
    - pdg.json   Program Dependence Graph
"""

import sys
import os
import json
from collections import defaultdict

from pycparser import parse_file, c_ast


# ============================================================
#  Utility Functions
# ============================================================

def coord_str(coord):
    """Convert pycparser's Coord object to 'file:line:col' string"""
    if coord is None:
        return None
    return f"{coord.file}:{coord.line}:{coord.column}"


def node_id(node):
    """Generate a unique ID for an AST node"""
    return f"{node.__class__.__name__}_{id(node)}"


# ============================================================
#  1. AST Generation
# ============================================================

def build_ast(ast_root, source_file=None):
    """
    Recursively traverse pycparser AST to generate a JSON structure of nodes + edges.
    Each node: { id, type, label, coord, attributes }
    Each edge: { from, to, child_name }

    source_file: If specified, only top-level declarations from this file are kept (filters out typedefs from headers).
    """
    nodes = []
    edges = []

    def _is_from_source(node):
        """Check if the node originates from the source file"""
        if source_file is None:
            return True
        if node.coord is None:
            return True
        return os.path.basename(node.coord.file) == os.path.basename(source_file)

    def visit(node, parent_id=None, child_name=None, depth=0):
        # Filter top-level nodes (depth==1) by source file
        if depth == 1 and not _is_from_source(node):
            return

        nid = node_id(node)
        attrs = {}
        for attr_name in node.attr_names:
            val = getattr(node, attr_name)
            attrs[attr_name] = str(val) if not isinstance(val, (str, int, float, bool, list)) else val

        label = node.__class__.__name__
        if isinstance(node, c_ast.FuncDecl):
            pass
        if isinstance(node, c_ast.Decl):
            label = f"Decl:{node.name}" if node.name else "Decl"
        elif isinstance(node, c_ast.ID):
            label = f"ID:{node.name}"
        elif isinstance(node, c_ast.Constant):
            label = f"Const:{node.value}"
        elif isinstance(node, c_ast.FuncCall):
            if isinstance(node.name, c_ast.ID):
                label = f"FuncCall:{node.name.name}"
        elif isinstance(node, c_ast.BinaryOp):
            label = f"BinaryOp:{node.op}"
        elif isinstance(node, c_ast.UnaryOp):
            label = f"UnaryOp:{node.op}"
        elif isinstance(node, c_ast.Assignment):
            label = f"Assign:{node.op}"

        nodes.append({
            "id": nid,
            "type": node.__class__.__name__,
            "label": label,
            "coord": coord_str(node.coord),
            "attributes": attrs,
        })
        if parent_id is not None:
            edges.append({"from": parent_id, "to": nid, "child_name": child_name})

        for cname, child in node.children():
            visit(child, nid, cname, depth + 1)

    visit(ast_root)
    return {"nodes": nodes, "edges": edges}


# ============================================================
#  2. CFG Generation
# ============================================================

class CFGBuilder(c_ast.NodeVisitor):
    """
    Build a Control Flow Graph for each function.
    Node = Statement, Edge = Execution Order.
    """

    def __init__(self):
        self.functions = {}  # func_name -> { nodes, edges }

    # ---------- Helpers ----------
    def _stmt_node(self, stmt):
        """Create a CFG node"""
        return {
            "id": node_id(stmt),
            "type": stmt.__class__.__name__,
            "label": self._stmt_label(stmt),
            "coord": coord_str(stmt.coord),
        }

    def _stmt_label(self, stmt):
        """Generate a readable label for a statement"""
        if isinstance(stmt, c_ast.FuncCall):
            if isinstance(stmt.name, c_ast.ID):
                return f"call {stmt.name.name}(...)"
            return "call ?"
        if isinstance(stmt, c_ast.Assignment):
            return f"{self._expr_str(stmt.lvalue)} {stmt.op} ..."
        if isinstance(stmt, c_ast.Return):
            return f"return {self._expr_str(stmt.expr) if stmt.expr else ''}"
        if isinstance(stmt, c_ast.Decl):
            return f"decl {stmt.name}" if stmt.name else "decl"
        if isinstance(stmt, c_ast.If):
            return f"if ({self._expr_str(stmt.cond)})"
        if isinstance(stmt, c_ast.For):
            return "for (...)"
        if isinstance(stmt, c_ast.While):
            return f"while ({self._expr_str(stmt.cond)})"
        if isinstance(stmt, c_ast.UnaryOp):
            return f"{stmt.op}{self._expr_str(stmt.expr)}"
        return stmt.__class__.__name__

    def _expr_str(self, expr):
        """Simplify expressions into strings"""
        if expr is None:
            return ""
        if isinstance(expr, c_ast.ID):
            return expr.name
        if isinstance(expr, c_ast.Constant):
            return expr.value
        if isinstance(expr, c_ast.BinaryOp):
            return f"{self._expr_str(expr.left)} {expr.op} {self._expr_str(expr.right)}"
        if isinstance(expr, c_ast.UnaryOp):
            return f"{expr.op}{self._expr_str(expr.expr)}"
        if isinstance(expr, c_ast.FuncCall):
            if isinstance(expr.name, c_ast.ID):
                return f"{expr.name.name}(...)"
            return "call(...)"
        if isinstance(expr, c_ast.StructRef):
            return f"{self._expr_str(expr.name)}->{expr.field.name}"
        if isinstance(expr, c_ast.ArrayRef):
            return f"{self._expr_str(expr.name)}[{self._expr_str(expr.subscript)}]"
        return expr.__class__.__name__

    # ---------- Function Level Entry ----------
    def visit_FuncDef(self, node):
        func_name = node.decl.name
        nodes = []
        edges = []

        entry = {"id": f"entry_{func_name}", "type": "Entry", "label": f"{func_name} ENTRY", "coord": coord_str(node.coord)}
        exit_node = {"id": f"exit_{func_name}", "type": "Exit", "label": f"{func_name} EXIT", "coord": None}
        nodes.append(entry)

        # Recursively process compound statements, returns (entry IDs list, exit IDs list)
        tail_ids = self._process_block(node.body, nodes, edges, [entry["id"]])

        nodes.append(exit_node)
        for tid in tail_ids:
            edges.append({"from": tid, "to": exit_node["id"], "label": ""})

        self.functions[func_name] = {"nodes": nodes, "edges": edges}

    def _process_block(self, compound, nodes, edges, prev_ids):
        """Process Compound (code block), returns a list of tail node IDs"""
        if compound is None or compound.block_items is None:
            return prev_ids
        current_prevs = prev_ids
        for stmt in compound.block_items:
            current_prevs = self._process_stmt(stmt, nodes, edges, current_prevs)
        return current_prevs

    def _process_stmt(self, stmt, nodes, edges, prev_ids):
        """Process a single statement, connect to prev_ids, return new tail ID list"""

        if isinstance(stmt, c_ast.If):
            cond_node = self._stmt_node(stmt)
            nodes.append(cond_node)
            for pid in prev_ids:
                edges.append({"from": pid, "to": cond_node["id"], "label": ""})

            # true branch
            true_tails = self._process_block(stmt.iftrue, nodes, edges, [cond_node["id"]]) \
                if isinstance(stmt.iftrue, c_ast.Compound) \
                else self._process_stmt(stmt.iftrue, nodes, edges, [cond_node["id"]])

            # Label the true branch edge
            for e in edges:
                if e["from"] == cond_node["id"] and e["to"] in [n["id"] for n in nodes[-len(true_tails)-5:]]:
                    if e["label"] == "":
                        e["label"] = "True"
                        break

            # false branch
            if stmt.iffalse:
                false_tails = self._process_block(stmt.iffalse, nodes, edges, [cond_node["id"]]) \
                    if isinstance(stmt.iffalse, c_ast.Compound) \
                    else self._process_stmt(stmt.iffalse, nodes, edges, [cond_node["id"]])
                for e in edges:
                    if e["from"] == cond_node["id"] and e["label"] == "":
                        e["label"] = "False"
                        break
                return true_tails + false_tails
            else:
                return true_tails + [cond_node["id"]]  # No else, cond itself is an exit

        elif isinstance(stmt, c_ast.For):
            # init
            if stmt.init:
                prev_ids = self._process_stmt(stmt.init, nodes, edges, prev_ids)
            cond_node = {"id": node_id(stmt), "type": "ForCond",
                         "label": f"for_cond ({self._expr_str(stmt.cond)})",
                         "coord": coord_str(stmt.coord)}
            nodes.append(cond_node)
            for pid in prev_ids:
                edges.append({"from": pid, "to": cond_node["id"], "label": ""})
            # body
            body_tails = self._process_block(stmt.stmt, nodes, edges, [cond_node["id"]])
            # next
            if stmt.next:
                body_tails = self._process_stmt(stmt.next, nodes, edges, body_tails)
            # back edge
            for bt in body_tails:
                edges.append({"from": bt, "to": cond_node["id"], "label": "back"})
            return [cond_node["id"]]  # Loop exits from cond

        elif isinstance(stmt, c_ast.Return):
            sn = self._stmt_node(stmt)
            nodes.append(sn)
            for pid in prev_ids:
                edges.append({"from": pid, "to": sn["id"], "label": ""})
            return []  # return has no successor

        elif isinstance(stmt, c_ast.Compound):
            return self._process_block(stmt, nodes, edges, prev_ids)

        elif isinstance(stmt, c_ast.Decl) and stmt.init and isinstance(stmt.init, c_ast.FuncCall):
            # e.g., int id = add_user(...)
            sn = {"id": node_id(stmt), "type": "DeclWithCall",
                  "label": f"decl {stmt.name} = {self._expr_str(stmt.init)}",
                  "coord": coord_str(stmt.coord)}
            nodes.append(sn)
            for pid in prev_ids:
                edges.append({"from": pid, "to": sn["id"], "label": ""})
            return [sn["id"]]

        else:
            sn = self._stmt_node(stmt)
            nodes.append(sn)
            for pid in prev_ids:
                edges.append({"from": pid, "to": sn["id"], "label": ""})
            return [sn["id"]]


def build_cfg(ast_root):
    builder = CFGBuilder()
    builder.visit(ast_root)
    return builder.functions


# ============================================================
#  3. DFG Generation (def-use chain)
# ============================================================

class DFGBuilder(c_ast.NodeVisitor):
    """
    Build function-level Data Flow Graph: tracks variable defs and uses.
    Node = Statement, Edge = Data Dependency (variable flows from def to use).
    """

    def __init__(self):
        self.functions = {}

    def visit_FuncDef(self, node):
        func_name = node.decl.name
        nodes = []
        edges = []

        # Collect parameters as initial defs
        defs = {}  # var_name -> stmt_id (last definition)
        params = node.decl.type
        if isinstance(params, c_ast.FuncDecl) and params.args:
            for param in params.args.params or []:
                if isinstance(param, c_ast.Decl) and param.name:
                    pid = f"param_{param.name}_{func_name}"
                    nodes.append({
                        "id": pid, "type": "Parameter",
                        "label": f"param: {param.name}",
                        "coord": coord_str(param.coord),
                    })
                    defs[param.name] = pid

        # Traverse function body
        if node.body and node.body.block_items:
            for stmt in node.body.block_items:
                self._process_stmt(stmt, nodes, edges, defs)

        self.functions[func_name] = {"nodes": nodes, "edges": edges}

    def _get_used_vars(self, expr):
        """Recursively extract variable names used in an expression"""
        if expr is None:
            return []
        if isinstance(expr, c_ast.ID):
            return [expr.name]
        if isinstance(expr, c_ast.BinaryOp):
            return self._get_used_vars(expr.left) + self._get_used_vars(expr.right)
        if isinstance(expr, c_ast.UnaryOp):
            return self._get_used_vars(expr.expr)
        if isinstance(expr, c_ast.FuncCall):
            used = []
            if expr.args:
                for arg in expr.args.exprs or []:
                    used += self._get_used_vars(arg)
            return used
        if isinstance(expr, c_ast.StructRef):
            return self._get_used_vars(expr.name)
        if isinstance(expr, c_ast.ArrayRef):
            return self._get_used_vars(expr.name) + self._get_used_vars(expr.subscript)
        if isinstance(expr, c_ast.Assignment):
            return self._get_used_vars(expr.rvalue)
        if isinstance(expr, c_ast.Cast):
            return self._get_used_vars(expr.expr)
        return []

    def _get_defined_var(self, stmt):
        """Get the variable name defined by the statement"""
        if isinstance(stmt, c_ast.Decl) and stmt.name:
            return stmt.name
        if isinstance(stmt, c_ast.Assignment):
            if isinstance(stmt.lvalue, c_ast.ID):
                return stmt.lvalue.name
            if isinstance(stmt.lvalue, c_ast.StructRef):
                return f"{self._expr_name(stmt.lvalue.name)}->{stmt.lvalue.field.name}"
        if isinstance(stmt, c_ast.UnaryOp) and stmt.op in ('p++', '++', 'p--', '--'):
            if isinstance(stmt.expr, c_ast.ID):
                return stmt.expr.name
        return None

    def _expr_name(self, expr):
        if isinstance(expr, c_ast.ID):
            return expr.name
        if isinstance(expr, c_ast.UnaryOp):
            return self._expr_name(expr.expr)
        return "?"

    def _process_stmt(self, stmt, nodes, edges, defs):
        if isinstance(stmt, c_ast.If):
            # cond uses variables
            sid = node_id(stmt)
            nodes.append({"id": sid, "type": "If", "label": f"if(...)", "coord": coord_str(stmt.coord)})
            for var in self._get_used_vars(stmt.cond):
                if var in defs:
                    edges.append({"from": defs[var], "to": sid, "var": var})
            # branches
            if isinstance(stmt.iftrue, c_ast.Compound) and stmt.iftrue.block_items:
                for s in stmt.iftrue.block_items:
                    self._process_stmt(s, nodes, edges, defs)
            if stmt.iffalse:
                if isinstance(stmt.iffalse, c_ast.Compound) and stmt.iffalse.block_items:
                    for s in stmt.iffalse.block_items:
                        self._process_stmt(s, nodes, edges, defs)
            return

        if isinstance(stmt, c_ast.For):
            if stmt.init:
                self._process_stmt(stmt.init, nodes, edges, defs)
            if stmt.cond:
                sid = node_id(stmt)
                nodes.append({"id": sid, "type": "ForCond", "label": "for_cond", "coord": coord_str(stmt.coord)})
                for var in self._get_used_vars(stmt.cond):
                    if var in defs:
                        edges.append({"from": defs[var], "to": sid, "var": var})
            if isinstance(stmt.stmt, c_ast.Compound) and stmt.stmt.block_items:
                for s in stmt.stmt.block_items:
                    self._process_stmt(s, nodes, edges, defs)
            if stmt.next:
                self._process_stmt(stmt.next, nodes, edges, defs)
            return

        if isinstance(stmt, c_ast.Return):
            sid = node_id(stmt)
            nodes.append({"id": sid, "type": "Return", "label": "return", "coord": coord_str(stmt.coord)})
            for var in self._get_used_vars(stmt.expr):
                if var in defs:
                    edges.append({"from": defs[var], "to": sid, "var": var})
            return

        if isinstance(stmt, c_ast.Compound):
            if stmt.block_items:
                for s in stmt.block_items:
                    self._process_stmt(s, nodes, edges, defs)
            return

        # General statements
        sid = node_id(stmt)
        label = stmt.__class__.__name__
        if isinstance(stmt, c_ast.Decl):
            label = f"decl {stmt.name}"
        elif isinstance(stmt, c_ast.Assignment):
            label = f"assign {self._get_defined_var(stmt)}"
        elif isinstance(stmt, c_ast.FuncCall):
            if isinstance(stmt.name, c_ast.ID):
                label = f"call {stmt.name.name}"

        nodes.append({"id": sid, "type": stmt.__class__.__name__, "label": label, "coord": coord_str(stmt.coord)})

        # use edge
        used = self._get_used_vars(stmt)
        # For Decl, variables used in init
        if isinstance(stmt, c_ast.Decl) and stmt.init:
            used += self._get_used_vars(stmt.init)
        for var in used:
            if var in defs:
                edges.append({"from": defs[var], "to": sid, "var": var})

        # def
        defined = self._get_defined_var(stmt)
        if defined:
            defs[defined] = sid


def build_dfg(ast_root):
    builder = DFGBuilder()
    builder.visit(ast_root)
    return builder.functions


# ============================================================
#  4. PDG Generation (Control Dependency + Data Dependency)
# ============================================================

def build_pdg(cfg_data, dfg_data):
    """
    PDG = Control Dependency (CD) + Data Dependency (DD).
    - CD is derived from condition nodes in CFG
    - DD directly reuses edges from DFG
    """
    pdg = {}
    for func_name in cfg_data:
        cfg = cfg_data[func_name]
        nodes = list(cfg["nodes"])  # Reuse CFG nodes
        edges = []

        # --- Control Dependency ---
        # Simplified: CD is from condition nodes (If/For) in CFG to their direct successors
        cond_types = {"If", "ForCond"}
        for edge in cfg["edges"]:
            from_node = next((n for n in nodes if n["id"] == edge["from"]), None)
            if from_node and from_node["type"] in cond_types:
                edges.append({
                    "from": edge["from"],
                    "to": edge["to"],
                    "type": "control_dependency",
                    "label": f"CD:{edge.get('label', '')}",
                })

        # --- Data Dependency ---
        if func_name in dfg_data:
            dfg = dfg_data[func_name]
            # Add DFG nodes (if not duplicates)
            existing_ids = {n["id"] for n in nodes}
            for dn in dfg["nodes"]:
                if dn["id"] not in existing_ids:
                    nodes.append(dn)
                    existing_ids.add(dn["id"])
            for de in dfg["edges"]:
                edges.append({
                    "from": de["from"],
                    "to": de["to"],
                    "type": "data_dependency",
                    "label": f"DD:{de.get('var', '?')}",
                })

        pdg[func_name] = {"nodes": nodes, "edges": edges}
    return pdg


# ============================================================
#   Main Entry
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("用法: python generate_graphs.py <source.c>")
        print("  将在 ./output/ 下生成 ast.json, cfg.json, dfg.json, pdg.json")
        sys.exit(1)

    source_file = sys.argv[1]
    output_dir = os.path.join(os.path.dirname(os.path.abspath(source_file)), "output")
    os.makedirs(output_dir, exist_ok=True)

    print(f"[*] 解析 {source_file} ...")
    # Use fake_libc_include to provide simplified versions of standard library headers
    script_dir = os.path.dirname(os.path.abspath(__file__))
    fake_libc = os.path.join(script_dir, "fake_libc_include")
    if not os.path.isdir(fake_libc):
        print(f"[!] fake_libc_include directory not found: {fake_libc}")
        print("    Please run: git clone https://github.com/eliben/pycparser.git /tmp/pc && cp -r /tmp/pc/utils/fake_libc_include .")
        sys.exit(1)

    ast = parse_file(source_file, use_cpp=True,
                     cpp_path='gcc',
                     cpp_args=['-E',
                               f'-I{fake_libc}',
                               '-D__attribute__(x)='])

    # 1. AST
    print("[1/4] Generating AST ...")
    ast_json = build_ast(ast, source_file=source_file)
    with open(os.path.join(output_dir, "ast.json"), "w", encoding="utf-8") as f:
        json.dump(ast_json, f, indent=2, ensure_ascii=False)
    print(f"      AST: {len(ast_json['nodes'])} nodes, {len(ast_json['edges'])} edges")

    # 2. CFG
    print("[2/4] Generating CFG ...")
    cfg_json = build_cfg(ast)
    with open(os.path.join(output_dir, "cfg.json"), "w", encoding="utf-8") as f:
        json.dump(cfg_json, f, indent=2, ensure_ascii=False)
    total_cfg = sum(len(v["nodes"]) for v in cfg_json.values())
    print(f"      CFG: {len(cfg_json)} functions, {total_cfg} total nodes")

    # 3. DFG
    print("[3/4] Generating DFG ...")
    dfg_json = build_dfg(ast)
    with open(os.path.join(output_dir, "dfg.json"), "w", encoding="utf-8") as f:
        json.dump(dfg_json, f, indent=2, ensure_ascii=False)
    total_dfg = sum(len(v["nodes"]) for v in dfg_json.values())
    print(f"      DFG: {len(dfg_json)} functions, {total_dfg} total nodes")

    # 4. PDG
    print("[4/4] Generating PDG ...")
    pdg_json = build_pdg(cfg_json, dfg_json)
    with open(os.path.join(output_dir, "pdg.json"), "w", encoding="utf-8") as f:
        json.dump(pdg_json, f, indent=2, ensure_ascii=False)
    total_pdg = sum(len(v["nodes"]) for v in pdg_json.values())
    print(f"      PDG: {len(pdg_json)} functions, {total_pdg} total nodes")

    print(f"\n[✓] All finished! Output directory: {output_dir}/")
    print(f"    - ast.json  ({os.path.getsize(os.path.join(output_dir, 'ast.json'))} bytes)")
    print(f"    - cfg.json  ({os.path.getsize(os.path.join(output_dir, 'cfg.json'))} bytes)")
    print(f"    - dfg.json  ({os.path.getsize(os.path.join(output_dir, 'dfg.json'))} bytes)")
    print(f"    - pdg.json  ({os.path.getsize(os.path.join(output_dir, 'pdg.json'))} bytes)")


if __name__ == "__main__":
    main()
