#!/usr/bin/env python3
"""
向量数据库构建脚本
==================

功能：
- 遍历codelibrary文件夹中的所有代码文件
- 读取文件内容
- 将代码文件构建到向量数据库
- 支持多种编程语言

使用方法：
python build_vector_db.py
"""

import os

# 设置HuggingFace镜像站点，解决网络连接问题
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.code_agent import CodeDetectionAgent


def get_language_from_extension(filename):
    """
    根据文件扩展名判断编程语言
    
    参数：
    - filename: 文件名
    
    返回：
    - str: 编程语言名称
    """
    ext = os.path.splitext(filename)[1].lower()
    
    language_map = {
        '.py': 'python',
        '.go': 'go',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.java': 'java',
        '.c': 'c',
        '.cpp': 'cpp',
        '.cs': 'csharp',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin'
    }
    
    return language_map.get(ext, 'unknown')


def collect_code_files(directory):
    """
    收集指定目录中的所有代码文件
    
    参数：
    - directory: 要遍历的目录
    
    返回：
    - list: 代码文件列表，每个元素包含content和path
    """
    code_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            # 获取文件扩展名
            ext = os.path.splitext(file)[1].lower()
            
            # 只处理代码文件
            if ext in ['.py', '.go', '.js', '.ts', '.java', '.c', '.cpp', '.cs', '.rb', '.php', '.swift', '.kt']:
                file_path = os.path.join(root, file)
                
                try:
                    # 读取文件内容
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 只添加非空文件
                    if content.strip():
                        code_files.append({
                            'content': content,
                            'path': file_path
                        })
                        print(f"[收集] 已收集: {file_path}")
                    else:
                        print(f"[收集] 跳过空文件: {file_path}")
                        
                except Exception as e:
                    print(f"[收集] 读取文件失败 {file_path}: {e}")
    
    return code_files


def main():
    """
    主函数
    """
    print("=== 开始构建向量数据库 ===")
    
    # 检查codelibrary目录是否存在
    codelibrary_dir = "codelibrary"
    if not os.path.exists(codelibrary_dir):
        print(f"错误: {codelibrary_dir} 目录不存在")
        sys.exit(1)
    
    # 收集所有代码文件
    print("1. 收集代码文件...")
    code_files = collect_code_files(codelibrary_dir)
    
    if not code_files:
        print("错误: 未收集到任何代码文件")
        sys.exit(1)
    
    print(f"2. 共收集到 {len(code_files)} 个代码文件")
    
    # 按语言分组
    files_by_language = {}
    for file in code_files:
        language = get_language_from_extension(file['path'])
        if language not in files_by_language:
            files_by_language[language] = []
        files_by_language[language].append(file)
    
    print("3. 按语言分组结果:")
    for lang, files in files_by_language.items():
        print(f"   - {lang}: {len(files)} 个文件")
    
    # 初始化CodeDetectionAgent（跳过LLM和CodeParser初始化以加快速度）
    print("4. 初始化代码检测智能体...")
    agent = CodeDetectionAgent(skip_llm=True, skip_parser=True)
    
    # 构建向量数据库
    print("5. 构建向量数据库...")
    total_files = 0
    batch_size = 200  # 减少每批处理文件数量，降低内存使用
    
    for language, files in files_by_language.items():
        if language != 'unknown' and files:
            print(f"   处理 {language} 语言: {len(files)} 个文件")
            
            # 分批处理文件
            for i in range(0, len(files), batch_size):
                batch = files[i:i + batch_size]
                print(f"      处理批次 {i//batch_size + 1}/{(len(files) + batch_size - 1)//batch_size}: {len(batch)} 个文件")
                try:
                    agent.build_vector_database(batch, language)
                    total_files += len(batch)
                    print(f"      已处理 {total_files} 个文件")
                except MemoryError:
                    print("      内存不足，尝试减小批次大小...")
                    # 进一步减小批次大小
                    small_batch_size = 50
                    for j in range(0, len(batch), small_batch_size):
                        small_batch = batch[j:j + small_batch_size]
                        print(f"        处理小批次 {j//small_batch_size + 1}/{(len(batch) + small_batch_size - 1)//small_batch_size}: {len(small_batch)} 个文件")
                        agent.build_vector_database(small_batch, language)
                        total_files += len(small_batch)
                        print(f"        已处理 {total_files} 个文件")
    
    print(f"\n=== 构建完成 ===")
    print(f"共处理 {total_files} 个代码文件")
    # 保存到 backend/faiss_index 目录
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(backend_dir, "backend", "faiss_index")
    agent.vectorstore.save_local(index_path)
    print(f"向量数据库已保存到 {index_path} 目录")


if __name__ == '__main__':
    main()
