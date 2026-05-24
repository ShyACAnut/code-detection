from __future__ import annotations

import re
from collections import Counter
from functools import lru_cache

from code_parser import CodeParser


def normalize_code(code: str) -> str:
    text = code or ""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"#.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"//.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z_]\w+|==|!=|<=|>=|[{}()\[\];,=+\-*/<>]", text)


@lru_cache(maxsize=1)
def _get_parser() -> CodeParser:
    return CodeParser()


def _collect_node_types(ast_node: dict | None) -> list[str]:
    if not ast_node:
        return []
    types = [str(ast_node.get("type", ""))]
    for child in ast_node.get("children", []) or []:
        types.extend(_collect_node_types(child))
    return [t for t in types if t]


def syntax_similarity(code_a: str, code_b: str, language: str | None = None) -> dict:
    na = normalize_code(code_a)
    nb = normalize_code(code_b)
    ta = _tokenize(na)
    tb = _tokenize(nb)
    if not ta or not tb:
        return {"score": 0.0, "matched_lines": [], "token_overlap": 0.0}

    ca, cb = Counter(ta), Counter(tb)
    common = sum((ca & cb).values())
    denom = sum(ca.values()) + sum(cb.values())
    token_overlap = (2 * common / denom) if denom else 0.0

    lines_a = {ln.strip() for ln in (code_a or "").splitlines() if ln.strip()}
    lines_b = {ln.strip() for ln in (code_b or "").splitlines() if ln.strip()}
    matched = sorted(list(lines_a.intersection(lines_b)))[:30]

    ast_score = None
    if language:
        try:
            parser = _get_parser()
            pa = parser.parse_code(code_a or "", language)
            pb = parser.parse_code(code_b or "", language)
            if pa and pb:
                ta = Counter(_collect_node_types(pa.get("ast")))
                tb = Counter(_collect_node_types(pb.get("ast")))
                common_ast = sum((ta & tb).values())
                denom_ast = sum(ta.values()) + sum(tb.values())
                ast_overlap = (2 * common_ast / denom_ast) if denom_ast else 0.0
                ast_score = round(ast_overlap * 100, 2)
        except Exception:
            ast_score = None

    if ast_score is None:
        score = round(token_overlap * 100, 2)
        layer = "token_fallback"
    else:
        # 语法层以 AST 为主，token 作为次要修正
        score = round(ast_score * 0.85 + (token_overlap * 100) * 0.15, 2)
        layer = "ast_syntax"

    return {
        "score": score,
        "matched_lines": matched,
        "token_overlap": round(token_overlap, 4),
        "ast_score": ast_score,
        "layer": layer,
    }
