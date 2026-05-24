import re
from typing import Optional, Tuple


def detect_code_language(code: str) -> Tuple[Optional[str], float, str]:
    """
    自动检测代码的编程语言类型
    
    Args:
        code: 代码字符串
        
    Returns:
        Tuple[detected_language, confidence, reason]
        - detected_language: 检测到的语言 ('python', 'java', 'javascript', 'c', 'cpp', 'csharp') 或 None
        - confidence: 置信度 (0.0 - 1.0)
        - reason: 检测原因说明
    """
    if not code or not code.strip():
        return None, 0.0, "代码为空"
    
    code_stripped = code.strip()
    code_lower = code_stripped.lower()
    
    scores = {
        'python': 0.0,
        'java': 0.0,
        'javascript': 0.0,
        'c': 0.0,
        'cpp': 0.0,
        'csharp': 0.0,
        'go': 0.0,
    }
    
    python_patterns = [
        (r'\bdef\s+\w+\s*\(', 3.0),
        (r'\bclass\s+\w+.*:', 2.0),
        (r'\bimport\s+\w+', 1.5),
        (r'\bfrom\s+\w+\s+import', 2.0),
        (r'if\s+__name__\s*==\s*[\'"]__main__[\'"]', 3.0),
        (r'\bprint\s*\(', 1.0),
        (r'\bself\.', 2.0),
        (r'\blambda\s+', 1.5),
        (r'\bexcept\s+\w+', 2.0),
        (r'\bwith\s+\w+\s+as\s+', 2.0),
        (r':\s*$', 1.0),
        (r'\bTrue\b|\bFalse\b|\bNone\b', 1.5),
    ]
    
    java_patterns = [
        (r'\bpublic\s+class\s+\w+', 3.0),
        (r'\bpublic\s+static\s+void\s+main\s*\(', 3.5),
        (r'\bSystem\.out\.print', 3.0),
        (r'\bSystem\.in', 2.0),
        (r'\bimport\s+java\.', 3.0),
        (r'\bpackage\s+[\w\.]+;', 2.5),
        (r'\bprivate\s+\w+\s+\w+\s*[;=]', 1.5),
        (r'\bprotected\s+\w+', 1.5),
        (r'\bthrows\s+\w+/', 2.0),
        (r'\bnew\s+\w+\s*\(', 1.0),
        (r'@\w+\s*(public|private|protected)', 2.0),
    ]
    
    javascript_patterns = [
        (r'\bconst\s+\w+\s*=', 2.0),
        (r'\blet\s+\w+\s*=', 2.0),
        (r'\bvar\s+\w+\s*=', 1.5),
        (r'\bfunction\s+\w+\s*\(', 2.0),
        (r'\bfunction\s*\(', 1.5),
        (r'=>', 2.0),
        (r'\bconsole\.log\s*\(', 3.0),
        (r'\bdocument\.', 2.0),
        (r'\bwindow\.', 1.5),
        (r'\bexport\s+(default\s+)?', 2.0),
        (r'\bimport\s+.*\s+from\s+[\'"]', 2.0),
        (r'\basync\s+function', 2.5),
        (r'\bawait\s+', 2.0),
        (r'\brequire\s*\(', 2.0),
    ]
    
    c_patterns = [
        (r'#include\s*<\w+\.h>', 3.0),
        (r'\bint\s+main\s*\(', 3.5),
        (r'\bprintf\s*\(', 2.5),
        (r'\bscanf\s*\(', 2.5),
        (r'\bmalloc\s*\(', 2.0),
        (r'\bfree\s*\(', 1.5),
        (r'\bstruct\s+\w+\s*\{', 2.0),
        (r'\btypedef\s+', 1.5),
        (r'\bNULL\b', 1.5),
        (r'\bsizeof\s*\(', 1.0),
    ]
    
    cpp_patterns = [
        (r'#include\s*<iostream>', 3.5),
        (r'#include\s*<vector>', 2.0),
        (r'#include\s*<string>', 2.0),
        (r'\busing\s+namespace\s+std', 3.5),
        (r'\bstd::', 3.0),
        (r'\bcout\s*<<', 3.0),
        (r'\bcin\s*>>', 3.0),
        (r'\bendl\b', 2.5),
        (r'\bclass\s+\w+\s*\{', 2.0),
        (r'\bpublic:\s*', 2.0),
        (r'\bprivate:\s*', 2.0),
        (r'\btemplate\s*<', 2.5),
        (r'\bnew\s+\w+\s*\(', 1.0),
        (r'\bdelete\s+', 1.5),
    ]
    
    csharp_patterns = [
        (r'\busing\s+System', 3.5),
        (r'\bnamespace\s+\w+', 3.0),
        (r'\bclass\s+Program', 2.5),
        (r'\bstatic\s+void\s+Main\s*\(', 3.5),
        (r'\bConsole\.Write', 3.0),
        (r'\bConsole\.Read', 2.5),
        (r'\bpublic\s+class\s+\w+', 2.0),
        (r'\bprivate\s+\w+\s+\w+\s*[;=]', 1.5),
        (r'\bstring\s+\w+', 2.0),
        (r'\bvar\s+\w+\s*=', 1.0),
        (r'\bforeach\s*\(', 2.0),
        (r'\bget\s*\{|set\s*\{', 2.5),
    ]

    go_patterns = [
        (r'\bpackage\s+\w+', 3.0),
        (r'\bfunc\s+main\s*\(', 3.5),
        (r'\bfunc\s+\(\w+\s+\*?\w+\)\s+\w+\s*\(', 3.0),
        (r'\bfunc\s+\w+\s*\(', 2.0),
        (r'\bimport\s+"fmt"', 3.0),
        (r'\bimport\s+"', 2.0),
        (r'\bfmt\.Print', 2.5),
        (r'\bfmt\.Sprintf', 2.5),
        (r'\bgo\s+func\s*\(', 3.0),
        (r'\bchan\s+', 2.5),
        (r'\bdefer\s+', 2.5),
        (r'\bmake\s*\(', 2.0),
        (r'\bmap\s*\[', 2.0),
        (r':=', 2.5),
        (r'\bif\s+err\s*!=', 2.0),
        (r'\breturn\s+', 1.0),
        (r'\bswitch\s+', 1.5),
        (r'\bcase\s+', 1.0),
        (r'\bdefault:', 1.5),
        (r'\brange\s+', 2.5),
        (r'\bstruct\s*\{', 2.0),
        (r'\binterface\s*\{', 2.5),
        (r'\btype\s+\w+\s+struct', 2.5),
        (r'\bgoroutine', 3.0),
    ]
    
    def calculate_score(patterns: list, code: str) -> float:
        score = 0.0
        for pattern, weight in patterns:
            matches = re.findall(pattern, code, re.MULTILINE | re.IGNORECASE)
            score += len(matches) * weight
        return score
    
    scores['python'] = calculate_score(python_patterns, code_stripped)
    scores['java'] = calculate_score(java_patterns, code_stripped)
    scores['javascript'] = calculate_score(javascript_patterns, code_stripped)
    scores['c'] = calculate_score(c_patterns, code_stripped)
    scores['cpp'] = calculate_score(cpp_patterns, code_stripped)
    scores['csharp'] = calculate_score(csharp_patterns, code_stripped)
    scores['go'] = calculate_score(go_patterns, code_stripped)
    
    if code_lower.startswith('#include') and 'using namespace' in code_lower:
        scores['cpp'] += 2.0
        scores['c'] -= 1.0
    
    if 'def ' in code_stripped and ':' in code_stripped:
        if not any(kw in code_stripped for kw in ['public:', 'private:', 'protected:']):
            scores['python'] += 1.0
    
    if 'class ' in code_stripped:
        if 'class ' in code_stripped and '{' in code_stripped:
            if 'namespace' in code_lower or 'using System' in code_lower:
                scores['csharp'] += 1.5
            elif 'public class' in code_lower:
                scores['java'] += 1.0
        elif 'class ' in code_stripped and ':' in code_stripped and '{' not in code_stripped:
            scores['python'] += 1.5
    
    max_score = max(scores.values())
    
    if max_score == 0.0:
        return None, 0.0, "无法识别代码语言特征"
    
    detected_lang = max(scores, key=scores.get)
    
    total_score = sum(scores.values())
    confidence = max_score / total_score if total_score > 0 else 0.0
    
    second_max = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0
    confidence_boost = (max_score - second_max) / max_score if max_score > 0 else 0
    final_confidence = min(0.95, confidence + confidence_boost * 0.3)
    
    lang_names = {
        'python': 'Python',
        'java': 'Java',
        'javascript': 'JavaScript',
        'c': 'C',
        'cpp': 'C++',
        'csharp': 'C#',
        'go': 'Go',
    }
    
    reason = f"检测到 {lang_names[detected_lang]} 特征 (得分: {max_score:.1f}, 置信度: {final_confidence:.1%})"
    
    return detected_lang, final_confidence, reason


def validate_code_language(code: str, expected_language: str) -> Tuple[bool, str]:
    """
    验证代码是否符合预期的语言类型
    
    Args:
        code: 代码字符串
        expected_language: 预期的语言类型
        
    Returns:
        Tuple[is_valid, message]
        - is_valid: 是否符合预期
        - message: 验证消息
    """
    detected_lang, confidence, reason = detect_code_language(code)
    
    if detected_lang is None:
        return False, "无法识别代码语言，请检查代码格式"
    
    if detected_lang != expected_language:
        lang_names = {
            'python': 'Python',
            'java': 'Java',
            'javascript': 'JavaScript',
            'c': 'C',
            'cpp': 'C++',
            'csharp': 'C#',
            'go': 'Go',
        }
        detected_name = lang_names.get(detected_lang, detected_lang)
        expected_name = lang_names.get(expected_language, expected_language)
        
        return False, f"代码类型不匹配！检测到的是 {detected_name}，但期望的是 {expected_name}。请使用正确的代码类型。"
    
    if confidence < 0.5:
        return True, f"代码类型匹配，但置信度较低 ({confidence:.1%})，建议检查代码完整性"
    
    return True, f"代码类型验证通过 ({confidence:.1%} 置信度)"
