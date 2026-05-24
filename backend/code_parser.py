# backend/code_parser.py (适配新版 tree-sitter)
import sys
import hashlib
from tree_sitter import Parser, Language
from sentence_transformers import SentenceTransformer
import numpy as np

print("=== 开始初始化 CodeParser ===")

language_objects = {}

try:
    import tree_sitter_python
    py_lang = Language(tree_sitter_python.language())
    language_objects['python'] = py_lang
    print("  [OK] 成功获取 python 语言对象")
except ImportError:
    print("  [ERROR] 未安装 tree-sitter-python，请运行: pip install tree-sitter-python")
except Exception as e:
    print(f"  [ERROR] 获取 python 语言对象失败: {e}")

try:
    import tree_sitter_java
    java_lang = Language(tree_sitter_java.language())
    language_objects['java'] = java_lang
    print("  [OK] 成功获取 java 语言对象")
except ImportError:
    print("  [ERROR] 未安装 tree-sitter-java，请运行: pip install tree-sitter-java")
except Exception as e:
    print(f"  [ERROR] 获取 java 语言对象失败: {e}")

try:
    import tree_sitter_javascript
    js_lang = Language(tree_sitter_javascript.language())
    language_objects['javascript'] = js_lang
    print("  [OK] 成功获取 javascript 语言对象")
except ImportError:
    print("  [ERROR] 未安装 tree-sitter-javascript，请运行: pip install tree-sitter-javascript")
except Exception as e:
    print(f"  [ERROR] 获取 javascript 语言对象失败: {e}")

try:
    import tree_sitter_c
    c_lang = Language(tree_sitter_c.language())
    language_objects['c'] = c_lang
    print("  [OK] 成功获取 c 语言对象")
except ImportError:
    print("  [ERROR] 未安装 tree-sitter-c，请运行: pip install tree-sitter-c")
except Exception as e:
    print(f"  [ERROR] 获取 c 语言对象失败: {e}")

try:
    import tree_sitter_cpp
    cpp_lang = Language(tree_sitter_cpp.language())
    language_objects['cpp'] = cpp_lang
    print("  [OK] 成功获取 cpp 语言对象")
except ImportError:
    print("  [ERROR] 未安装 tree-sitter-cpp，请运行: pip install tree-sitter-cpp")
except Exception as e:
    print(f"  [ERROR] 获取 cpp 语言对象失败: {e}")

try:
    import tree_sitter_c_sharp
    cs_lang = Language(tree_sitter_c_sharp.language())
    language_objects['csharp'] = cs_lang
    print("  [OK] 成功获取 csharp 语言对象")
except ImportError:
    print("  [ERROR] 未安装 tree-sitter-c-sharp，请运行: pip install tree-sitter-c-sharp")
except Exception as e:
    print(f"  [ERROR] 获取 csharp 语言对象失败: {e}")

if not language_objects:
    print("\n[ERROR] 错误：未能获取任何语言对象。")
    sys.exit(1)

# ========== 定义 CodeEmbedder 类 ==========
class CodeEmbedder:
    """使用预训练模型生成代码语义向量"""
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
    def encode(self, code: str) -> np.ndarray:
        # 简单清洗：限制长度，避免过长文本
        code_clean = code[:2000]  # 根据模型token限制调整
        embedding = self.model.encode(code_clean)
        return embedding.astype(np.float32)

# ========== 定义 CodeParser 类 ==========
class CodeParser:
    def __init__(self):
        self.parsers = {}
        print(f"\n正在为语言创建 Parser 实例...")

        for lang_name, lang_obj in language_objects.items():
            try:
                p = Parser()
                p.language = lang_obj
                self.parsers[lang_name] = p
                print(f"  [OK] {lang_name}: Parser 创建成功")
            except Exception as e:
                print(f"  [ERROR] {lang_name}: Parser 创建失败。错误: {e}")

        if self.parsers:
            print(f"\n[SUCCESS] CodeParser 初始化完成！支持语言: {list(self.parsers.keys())}")
        else:
            print("\n[ERROR] CodeParser 初始化失败：无法为任何语言创建解析器。")
            sys.exit(1)

    def parse_code(self, code_string: str, language: str) -> dict:
        """核心解析方法 - 修复版，包含空值检查和结构指纹计算"""
        if language not in self.parsers:
            print(f"[解析器] 不支持的语言: {language}")
            return None

        try:
            parser = self.parsers[language]
            # 确保输入是字节
            code_bytes = bytes(code_string, 'utf8') if isinstance(code_string, str) else code_string
            tree = parser.parse(code_bytes)
            
            if tree is None:
                print(f"[解析器] 解析失败，tree为None")
                return None
                
            root_node = tree.root_node
            
            if root_node is None:
                print(f"[解析器] 根节点为None")
                return None

            # AST转换函数
            def node_to_dict(node):
                if node is None:
                    return None
                return {
                    'type': node.type,
                    'text': node.text.decode('utf8') if node.text else None,
                    'start_point': node.start_point,
                    'end_point': node.end_point,
                    'children': [node_to_dict(child) for child in node.children]
                }

            ast_dict = node_to_dict(root_node)
            
            if ast_dict is None:
                print(f"[解析器] AST转换失败")
                return None

            # 递归收集AST中所有节点类型的函数
            def collect_node_types(node):
                if node is None:
                    return []
                types = [node.type]
                for child in node.children:
                    child_types = collect_node_types(child)
                    if child_types:
                        types.extend(child_types)
                return types
            
            node_type_list = collect_node_types(root_node)
            if not node_type_list:
                print(f"[解析器] 节点类型列表为空")
                return None
                
            structure_fingerprint = hashlib.md5(','.join(node_type_list).encode()).hexdigest()
            
            print(f"[解析器] 成功解析 {language} 代码，根节点类型: {root_node.type}，指纹: {structure_fingerprint[:8]}...")

            result = {
                'language': language,
                'ast': ast_dict,
                'structure_fingerprint': structure_fingerprint,
                'success': True,
                '_tree': tree,  # 保留原始树对象以供高级查询
            }
            
            return result
            
        except Exception as e:
            print(f"[解析器] 解析过程中出现异常: {e}")
            return None

    def get_supported_languages(self):
        """返回当前支持的语言列表"""
        return list(self.parsers.keys())

# ========== 当直接运行此脚本时的自测逻辑 ==========
if __name__ == '__main__':
    print("\n" + "="*50)
    print("开始运行 CodeParser 自测...")
    
    code_parser = CodeParser()
    
    if 'python' in code_parser.parsers:
        print(f"\n[测试 Python]")
        test_code = """def hello(name):
    print(f"Hello, {name}!")
    return len(name)"""
        try:
            result = code_parser.parse_code(test_code, 'python')
            if result is not None:
                print(f"  解析成功！")
                print(f"  根节点类型: {result['ast']['type']}")
                print(f"  结构指纹: {result['structure_fingerprint'][:16]}...")
                print(f"  子节点数: {len(result['ast']['children'])}")
                for child in result['ast']['children']:
                    if child['type'] == 'function_definition':
                        func_name_node = child['children'][1]
                        print(f"  找到函数: {func_name_node.get('text', 'N/A')}")
                        break
            else:
                print("  解析失败，返回None")
        except Exception as e:
            print(f"  解析失败: {e}")
    
    if 'java' in code_parser.parsers:
        print(f"\n[测试 Java]")
        test_code = """public class Main {
    public static void main(String[] args) {
        System.out.println("Test");
    }
}"""
        try:
            result = code_parser.parse_code(test_code, 'java')
            if result is not None:
                print(f"  解析成功！")
                print(f"  根节点类型: {result['ast']['type']}")
                print(f"  结构指纹: {result['structure_fingerprint'][:16]}...")
            else:
                print("  解析失败，返回None")
        except Exception as e:
            print(f"  解析失败: {e}")
    
    print("\n" + "="*50)
    print("自测完成。")