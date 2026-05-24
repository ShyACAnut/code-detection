# backend/build_vector_library.py
import os
import sys
import hashlib
sys.path.append(os.path.dirname(__file__))

from langchain_core.documents import Document
from code_agent import CodeDetectionAgent

def collect_code_files(root_dir: str, max_per_lang: int = 5000):
    """递归收集目录下的代码文件，每种语言最多收集 max_per_lang 个文件"""
    code_files = []
    ext_to_lang = {
        '.py': 'python',
        '.java': 'java',
        '.go': 'go',
        '.js': 'javascript',
        '.c': 'c',
        '.cpp': 'cpp',
        '.cs': 'csharp',
    }
    lang_count = {lang: 0 for lang in set(ext_to_lang.values())}
    
    for root, dirs, files in os.walk(root_dir):
        files.sort()  # 保证每次结果一致
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in ext_to_lang:
                continue
            lang = ext_to_lang[ext]
            if lang_count[lang] >= max_per_lang:
                continue
            full_path = os.path.join(root, file)
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                rel_path = os.path.relpath(full_path, root_dir)
                code_files.append({
                    "path": rel_path,
                    "content": content,
                    "language": lang
                })
                lang_count[lang] += 1
                print(f"已添加: {rel_path} ({lang}) [{lang_count[lang]}/{max_per_lang}]")
            except Exception as e:
                print(f"读取失败 {full_path}: {e}")
    return code_files

if __name__ == '__main__':
    CODE_LIBRARY_PATH = r"D:\aicode_\aicode\codelibrary"  # 你的代码库路径
    MAX_PER_LANG = 5000  # 每种语言最多提取的文件数
    
    print("="*60)
    print("开始构建向量数据库（自动识别语言）")
    print(f"每种语言最多提取 {MAX_PER_LANG} 个文件")
    print("="*60)
    
    code_files = collect_code_files(CODE_LIBRARY_PATH, max_per_lang=MAX_PER_LANG)
    if not code_files:
        print("没有找到任何代码文件，请检查路径。支持的扩展名: .py, .java, .go, .js, .c, .cpp, .cs")
        sys.exit(1)
    print(f"共找到 {len(code_files)} 个代码文件（已达到上限的文件已停止收集）")
    lang_stats = {}
    for file in code_files:
        lang = file['language']
        lang_stats[lang] = lang_stats.get(lang, 0) + 1
    print("各语言统计:")
    for lang, count in sorted(lang_stats.items()):
        print(f"  {lang}: {count} 个文件")
    
    # 初始化智能体（会自动加载已有的向量库或创建空索引）
    agent = CodeDetectionAgent()
    
    # 将收集的代码文件转换为 Document 对象
    documents = []
    for file in code_files:
        doc = Document(
            page_content=file['content'],
            metadata={
                "path": file['path'],
                "language": file['language'],
                "content_hash": hashlib.md5(file['content'].encode()).hexdigest()
            }
        )
        documents.append(doc)
    
    # 批量添加到向量库
    total = len(documents)
    for i in range(0, total, 100):  # 每100个一批添加，避免内存占用过大
        batch = documents[i:i+100]
        agent.vectorstore.add_documents(batch)
        print(f"[向量库] 进度: {min(i+100, total)}/{total}")
    
    # 保存索引到 backend/faiss_index 目录
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(backend_dir, "faiss_index")
    agent.vectorstore.save_local(index_path)
    
    # 获取最终统计（因为 agent.vectorstore.index.ntotal 可能未立即更新，重新加载一下）
    vector_count = agent.vectorstore.index.ntotal if hasattr(agent.vectorstore, 'index') else len(documents)
    print(f"向量数据库构建完成！共 {vector_count} 条向量")
    print(f"索引文件已保存至: {index_path}")