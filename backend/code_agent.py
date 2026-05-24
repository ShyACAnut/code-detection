"""
代码检测智能体核心模块
=====================

这个模块实现了代码相似性检测的核心算法，采用分层检测策略：
1. 哈希过滤层：快速排除完全相同的代码
2. 向量检索层：找到相似的代码片段
3. LLM语义分析层：深度分析代码逻辑相似性

技术栈：
- LangChain：用于LLM调用和向量库管理
- FAISS：用于高效的向量检索
- HuggingFace Embeddings：用于代码向量化
- 智慧AI GLM-4.5-air：用于语义分析

主要功能：
- 代码标准化和预处理
- 多层次相似性检测
- 向量数据库构建和管理
- 智能重试机制
"""

import os
import json
import re
import time
import hashlib
import numpy as np
from typing import List
from dotenv import load_dotenv
try:
    from .code_parser import CodeParser, CodeEmbedder
except ImportError:
    from code_parser import CodeParser, CodeEmbedder
from langchain_core.prompts import PromptTemplate
from langchain_community.chat_models import ChatZhipuAI
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_community.docstore.in_memory import InMemoryDocstore
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import HTTPError
import faiss

# 加载环境变量
load_dotenv()

class CodeDetectionAgent:
    """
    代码检测智能体主类
    ==================
    
    这个类实现了完整的代码相似性检测系统，采用三层检测策略：
    1. 哈希过滤层：快速排除完全相同的代码
    2. 向量检索层：找到相似的代码片段
    3. LLM语义分析层：深度分析代码逻辑相似性
    
    核心特性：
    - 分层检测提高效率
    - 支持多种编程语言
    - 智能重试机制
    - 向量数据库管理
    """

    # ============================================================================
    # LLM提示词模板
    # ============================================================================
    # 这是用于语义分析的核心提示词，指导LLM进行代码相似性判断
    similarity_prompt = PromptTemplate(
        input_variables=["language", "code_a", "code_b"],
        template="""
        你是一个资深的代码审查专家。请严格从**代码功能、逻辑结构和算法意图**的角度（忽略变量名、注释、格式等表面差异），
        分析以下两段{language}代码的相似性。

        请按以下步骤思考：
        1. 概括代码A的核心功能。
        2. 概括代码B的核心功能。
        3. 比较两者在逻辑流程、数据结构、关键算法上的异同。
        4. 基于以上分析，给出一个0-100的整体相似度评分（100表示逻辑完全等价）。

        请务必将最终输出严格格式化为一个合法的JSON对象，包含以下三个键：
        - "score": (整数)
        - "reason": (字符串，简要说明理由，**必须使用中文**)
        - "function_summary": (字符串，对代码功能的概括，**必须使用中文**)
        **注意：只输出JSON，不要输出任何其他解释或标记。**

        代码片段 A:
        ```{language}
        {code_a}
        代码片段 B:
        {language}
        {code_b}
        """
        )
    def __init__(self, skip_llm=False, skip_parser=False):
        """
        智能体初始化方法
        ================
        
        功能：
        - 初始化所有必要的组件和工具
        - 设置向量数据库
        - 配置LLM模型
        
        参数：
        - skip_llm: 是否跳过LLM初始化（用于构建向量数据库时）
        - skip_parser: 是否跳过CodeParser和CodeEmbedder初始化（用于构建向量数据库时）
        
        初始化的组件：
        1. CodeParser：代码解析器（可选）
        2. CodeEmbedder：代码向量化器（可选）
        3. ChatZhipuAI：LLM模型（可选）
        4. HuggingFaceEmbeddings：文本向量化模型
        5. FAISS：向量数据库
        
        异常处理：
        - 捕获并打印详细的初始化错误
        - 确保系统状态可追踪
        """
        try:
            # ============================================================================
            # 核心工具初始化
            # ============================================================================
            # 1. 代码解析器：用于AST解析和代码分析
            if not skip_parser:
                self.parser = CodeParser()
                
                # 2. 代码向量化器：将代码转换为向量表示
                # 由于SentenceTransformer模型加载问题，直接跳过CodeEmbedder初始化
                print("[智能体] 跳过CodeEmbedder初始化（避免模型加载问题）")
                self.embedder = None
            else:
                print("[智能体] 跳过CodeParser和CodeEmbedder初始化")
            
            # 3. LLM模型：用于语义分析和相似性判断
            if not skip_llm:
                self.llm = ChatZhipuAI(
                    api_key=os.getenv("ZHIPUAI_API_KEY"),
                    model="glm-4.5-air",          # 使用GLM-4.5-air模型进行代码分析
                    temperature=0.1,          # 低温度确保输出一致性
                    max_tokens=20000,        # 足够的token长度处理复杂代码
                    timeout=120              # 120秒超时设置
                )
            else:
                print("[智能体] 跳过LLM初始化")

            # ============================================================================
            # 向量数据库初始化
            # ============================================================================
            # 使用 backend 目录下的 faiss_index
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            index_path = os.path.join(backend_dir, "faiss_index")
            
            # 检查是否已存在向量库
            if os.path.exists(index_path):
                # 现有索引使用自定义的100维简单关键字模型，需要特殊处理
                print("[智能体] 检测到现有向量库，使用兼容模式")
                
                # 创建自定义嵌入函数以匹配现有索引的100维向量
                class SimpleKeywordEmbeddings:
                    def __init__(self):
                        self.embedding_dim = 100
                        # 与构建脚本相同的词汇表
                        self.vocab = self._build_simple_vocab()
                    
                    def _build_simple_vocab(self):
                        """构建简单词汇表（与构建脚本保持一致）"""
                        common_keywords = [
                            'def', 'class', 'import', 'from', 'if', 'else', 'for', 'while', 'return',
                            'function', 'var', 'let', 'const', 'public', 'private', 'protected',
                            'void', 'int', 'string', 'bool', 'true', 'false', 'null', 'this', 'self',
                            'new', 'try', 'catch', 'finally', 'break', 'continue', 'switch', 'case',
                            'default', 'extends', 'implements', 'interface', 'abstract', 'static',
                            'final', 'super', 'package', 'throw', 'throws', 'enum', 'assert'
                        ]
                        return {word: idx for idx, word in enumerate(common_keywords)}
                    
                    def embed_documents(self, texts):
                        """将文档列表转换为向量"""
                        embeddings = []
                        for text in texts:
                            vector = np.zeros(self.embedding_dim)
                            words = text.lower().split()
                            for word in words:
                                if word in self.vocab:
                                    idx = self.vocab[word] % self.embedding_dim
                                    vector[idx] += 1
                            
                            norm = np.linalg.norm(vector)
                            if norm > 0:
                                vector = vector / norm
                            
                            embeddings.append(vector)
                        
                        return embeddings
                    
                    def embed_query(self, text):
                        """将查询文本转换为向量"""
                        return self.embed_documents([text])[0]
                    
                    def __call__(self, text):
                        """使对象可调用，用于LangChain兼容性"""
                        return self.embed_query(text)
                
                # 使用自定义嵌入函数
                self.embeddings = SimpleKeywordEmbeddings()
                
                # 加载现有向量库
                self.vectorstore = FAISS.load_local(index_path, self.embeddings, allow_dangerous_deserialization=True)
                
                # 重建文档存储映射，解决KeyError问题
                self._rebuild_document_store()
                
                # 加载向量元数据列表
                self.vector_metadata = None
                metadata_pkl = os.path.join(index_path, 'metadata.pkl')
                if os.path.exists(metadata_pkl):
                    try:
                        import pickle
                        with open(metadata_pkl, 'rb') as f:
                            full_meta = pickle.load(f)
                            if isinstance(full_meta, dict) and 'metadata' in full_meta:
                                self.vector_metadata = full_meta['metadata']
                                print(f"[智能体] 已加载向量元数据，数量: {len(self.vector_metadata)}")
                    except Exception as e:
                        print(f"[智能体] 加载向量元数据失败: {e}")
                        self.vector_metadata = None
                
                print("[智能体] 已加载现有向量库（使用兼容的简单关键字模型）")
                print(f"[智能体] 文档数量: {len(self.vectorstore.docstore._dict)}")
                print(f"[智能体] 索引映射数量: {len(self.vectorstore.index_to_docstore_id)}")
            else:
                # 手动创建空的FAISS索引，避免from_documents对空列表的bug
                print("[智能体] 创建新的向量库")
                # 使用all-MiniLM-L6-v2模型进行新索引创建
                self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
                dimension = 384  # 与模型维度一致
                index = faiss.IndexFlatL2(dimension)  # 使用L2距离度量
                self.vectorstore = FAISS(
                    embedding_function=self.embeddings,
                    index=index,
                    docstore=InMemoryDocstore({}),  # 内存文档存储
                    index_to_docstore_id={}         # 索引到文档ID的映射
                )

            # 输出向量库状态信息
            vector_count = self.vectorstore.index.ntotal if hasattr(self.vectorstore, 'index') else 0
            print(f"[智能体] 向量库状态: {{'total_vectors': {vector_count}}}")
            print("[智能体] 初始化完成，工具已就绪。")
            
        except Exception as e:
            # 异常处理：打印详细的错误堆栈信息
            import traceback
            print("[ERROR] 初始化 CodeDetectionAgent 失败，详细错误：")
            traceback.print_exc()
            raise  # 重新抛出异常

    def _rebuild_document_store(self):
        """
        重建文档存储映射
        ================
        
        功能：
        - 修复index_to_docstore_id映射中的键类型问题（np.int64 -> str）
        - 保持FAISS.load_local加载的原始文档
        """
        try:
            # 原始文档已经通过 FAISS.load_local 加载了
            # 只需要修复 index_to_docstore_id 的键类型
            old_mapping = self.vectorstore.index_to_docstore_id.copy()
            self.vectorstore.index_to_docstore_id.clear()
            
            for idx, doc_id in old_mapping.items():
                # 确保索引键是 int 类型
                int_idx = int(idx) if not isinstance(idx, int) else idx
                self.vectorstore.index_to_docstore_id[int_idx] = str(doc_id) if not isinstance(doc_id, str) else doc_id
            
            print(f"[智能体] 文档映射修复完成，共有 {len(self.vectorstore.index_to_docstore_id)} 个文档")
            
        except Exception as e:
            print(f"[WARNING] 文档映射修复失败: {e}")
            import traceback
            traceback.print_exc()

    def _normalize_code(self, code: str) -> str:
        """
        代码标准化方法
        =============
        
        功能：
        - 移除代码中的注释和空白字符
        - 标准化代码格式以便比较
        
        处理步骤：
        1. 移除块注释（/* */）
        2. 移除行注释（# //）
        3. 移除所有空白字符（空格、换行、制表符等）
        
        参数：
        - code: 原始代码字符串
        
        返回值：
        - str: 标准化后的代码字符串
        
        使用场景：
        - 哈希过滤前的预处理
        - 代码相似性比较的基础
        """
        # 移除块注释（多行注释）
        code_no_block = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        
        # 移除行注释（Python的#和Java/C++的//）
        code_no_all = re.sub(r'#.*$|//.*$', '', code_no_block, flags=re.MULTILINE)
        
        # 移除所有空白字符（包括空格、换行、制表符等）
        code_no_whitespace = re.sub(r'\s+', '', code_no_all)
        
        return code_no_whitespace

    def _call_llm_with_retry(self, prompt: str, max_retries: int = 5):
        """
        LLM调用重试机制（增强版）
        =========================
        
        功能：
        - 处理API速率限制（429错误）
        - 实现智能指数退避重试策略
        - 添加请求频率控制
        - 支持多种错误类型处理
        
        重试策略：
        - 最大重试次数：5次（增加重试机会）
        - 智能退避：2秒、5秒、10秒、20秒、30秒
        - 支持多种错误类型：429、500、502、503、504
        - 添加请求间隔控制，避免连续请求
        
        参数：
        - prompt: 发送给LLM的提示词
        - max_retries: 最大重试次数（默认5次）
        
        返回值：
        - LLM响应结果
        
        异常处理：
        - 超过最大重试次数后使用传统分析方法
        - 非重试错误立即使用传统分析方法
        """
        # 添加请求间隔控制，避免连续请求
        time.sleep(1)  # 基础间隔1秒
        
        for attempt in range(max_retries):
            try:
                # 尝试调用LLM
                return self.llm.invoke(prompt)
                
            except Exception as e:
                # 检查是否是需要重试的错误类型
                should_retry = False
                retryable_errors = [429, 500, 502, 503, 504]  # 可重试的错误码
                
                # 检查HTTP错误码
                if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                    should_retry = (e.response.status_code in retryable_errors)
                elif isinstance(e, HTTPError) and hasattr(e, 'response'):
                    should_retry = (e.response.status_code in retryable_errors)
                
                # 根据错误消息判断
                error_str = str(e).lower()
                if any(str(code) in error_str for code in retryable_errors):
                    should_retry = True
                if 'rate limit' in error_str or 'too many requests' in error_str:
                    should_retry = True
                if 'timeout' in error_str or 'gateway' in error_str:
                    should_retry = True
                
                if should_retry:
                    # 智能退避策略：2秒、5秒、10秒、20秒、30秒
                    wait_time = min(2 ** (attempt + 1) + attempt, 30)  # 限制最大等待时间
                    error_code = "未知"
                    if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                        error_code = e.response.status_code
                    
                    print(f"[LLM] 遇到可重试错误({error_code})，{wait_time}秒后重试... (尝试 {attempt+1}/{max_retries})")
                    print(f"[LLM] 错误详情: {str(e)[:200]}")
                    time.sleep(wait_time)
                else:
                    # 非重试错误，立即使用传统分析方法
                    print(f"[LLM] 遇到不可重试错误: {str(e)[:200]}")
                    raise Exception(f"LLM调用失败（不可重试）: {str(e)[:100]}")
                    
        # 超过最大重试次数，抛出异常，让上层使用传统分析方法
        raise Exception("LLM调用失败：超过最大重试次数，将使用传统语义分析方法")

    def _quick_hash_filter(self, code_a: str, code_b: str) -> bool:
        """
        第一层检测：哈希过滤
        ==================
        
        功能：
        - 快速判断两段代码是否完全相同
        - 使用MD5哈希算法进行快速比较
        - 作为第一层过滤，提高检测效率
        
        检测流程：
        1. 标准化两段代码（移除注释和空白）
        2. 计算标准化后的MD5哈希值
        3. 比较哈希值是否相等
        
        参数：
        - code_a: 第一段代码
        - code_b: 第二段代码
        
        返回值：
        - bool: True表示代码完全相同，False表示不同
        
        性能优势：
        - O(1)时间复杂度的快速比较
        - 避免不必要的深度分析
        - 节省计算资源
        """
        # 标准化代码以便比较
        norm_a = self._normalize_code(code_a)
        norm_b = self._normalize_code(code_b)

        # 调试信息输出
        print(f"[哈希过滤] 标准化A长度: {len(norm_a)}, 内容: {norm_a[:50]}...")
        print(f"[哈希过滤] 标准化B长度: {len(norm_b)}, 内容: {norm_b[:50]}...")

        # 计算MD5哈希值
        hash_a = hashlib.md5(norm_a.encode()).hexdigest()
        hash_b = hashlib.md5(norm_b.encode()).hexdigest()

        # 输出哈希值比较结果
        print(f"[哈希过滤] 哈希A: {hash_a[:8]}...")
        print(f"[哈希过滤] 哈希B: {hash_b[:8]}...")
        print(f"[哈希过滤] 是否相等: {hash_a == hash_b}")

        # 返回哈希比较结果
        return hash_a == hash_b

    def build_vector_database(self, code_files: List[dict], language: str):
        """
        向量数据库构建方法
        ==================
        
        功能：
        - 将代码文件转换为向量并存储到FAISS向量库
        - 支持增量构建和持久化存储
        - 为后续的相似性检索做准备
        
        处理流程：
        1. 将每个代码文件转换为LangChain Document对象
        2. 为每个文档添加元数据（路径、语言、内容哈希）
        3. 批量添加到向量库（分批处理以减少内存使用）
        4. 持久化保存到本地文件系统
        
        参数：
        - code_files: 代码文件列表，每个文件包含content和path
        - language: 编程语言类型
        
        文档结构：
        - page_content: 代码内容
        - metadata: 包含路径、语言、内容哈希的元数据
        
        使用场景：
        - 初始化向量库
        - 批量添加新的代码样本
        - 更新现有向量库
        """
        # 分小批次处理，进一步减少内存使用
        chunk_size = 50
        total_docs = 0
        
        for i in range(0, len(code_files), chunk_size):
            chunk = code_files[i:i + chunk_size]
            
            # 创建文档列表
            documents = []
            
            # 遍历每个代码文件，转换为Document对象
            for file in chunk:
                # 创建Document对象，包含代码内容和元数据
                doc = Document(
                    page_content=file['content'],  # 代码内容
                    metadata={
                        "path": file['path'],          # 文件路径
                        "language": language,          # 编程语言
                        "content_hash": hashlib.md5(file['content'].encode()).hexdigest()  # 内容哈希
                    }
                )
                documents.append(doc)
            
            # 批量添加文档到向量库
            if documents:
                self.vectorstore.add_documents(documents)
                total_docs += len(documents)
                
                # 每处理1000个文件保存一次，减少内存压力
                if total_docs % 1000 == 0:
                    # 持久化保存向量库到本地文件系统
                    self.vectorstore.save_local("faiss_index")
                    print(f"[向量库] 已添加 {total_docs} 个文档到向量库")
                    print("[向量库] 向量库已保存到 faiss_index")
        
        # 最终保存
        if total_docs > 0:
            self.vectorstore.save_local("faiss_index")
            print(f"[向量库] 已添加 {total_docs} 个文档到向量库")
            print("[向量库] 向量库已保存到 faiss_index")

    def _structure_similarity(self, ast_info_a: dict, ast_info_b: dict) -> float:
        """
        第二层检测：结构指纹相似度
        ========================
        
        功能：
        - 比较两段代码的AST结构指纹
        - 判断代码在结构层面是否相似
        - 返回二元的相似度结果（0或1）
        
        检测原理：
        - 使用AST解析生成结构指纹
        - 比较指纹是否完全相同
        - 相同的结构指纹表示相同的代码结构
        
        参数：
        - ast_info_a: 第一段代码的AST信息
        - ast_info_b: 第二段代码的AST信息
        
        返回值：
        - float: 1.0表示结构相同，0.0表示结构不同
        
        使用场景：
        - 检测代码结构的相似性
        - 发现算法层面的抄袭
        - 作为LLM分析的前置过滤
        """
        # 检查输入参数有效性
        if ast_info_a is None or ast_info_b is None:
            print(f"[结构相似度] 警告: 输入参数为空")
            return 0.0

        # 获取结构指纹
        fp_a = ast_info_a.get('structure_fingerprint')
        fp_b = ast_info_b.get('structure_fingerprint')

        # 比较指纹
        if fp_a and fp_b:
            # 二元比较：相同为1.0，不同为0.0
            similarity = 1.0 if fp_a == fp_b else 0.0
            
            # 输出比较结果
            if fp_a == fp_b:
                print(f"[结构相似度] 指纹相同，相似度: 1.0")
            else:
                print(f"[结构相似度] 指纹不同，相似度: 0.0")
            return similarity
            
        return 0.0

    def analyze_code_similarity(self, code_a: str, code_b: str, language: str) -> dict:
        """
        智能体核心方法：四层过滤相似性分析（支持所有7种语言）
        ====================================================
        
        功能：
        - 实现完整的代码相似性检测流程
        - 采用四层过滤策略提高效率和准确性
        - 支持所有7种编程语言：Python、Java、JavaScript、C、C++、C#、Go
        - 返回详细的相似性分析结果
        
        四层过滤策略：
        1. 第0层：向量检索过滤 - 快速找到相似候选
        2. 第一层：哈希过滤 - 检测完全相同的代码
        3. 第二层：结构比对 - 分析AST结构相似性
        4. 第三层：LLM语义分析 - 深度逻辑相似性判断
        
        参数：
        - code_a: 第一段待分析的代码
        - code_b: 第二段待分析的代码
        - language: 编程语言类型
        
        返回值：
        - dict: 包含相似性分析结果和元数据
        
        使用场景：
        - 代码抄袭检测
        - 作业相似性分析
        - 代码质量评估
        """
        print(f"[智能体] 开始分析两段 {language} 代码的相似性...")

        # ============================================================================
        # 第0层：向量检索过滤（优化版）
        # ============================================================================
        # 使用向量库快速找到相似候选，提高检测效率
        vector_similarity = 0.0  # 向量相似度评分
        vector_candidates = []   # 相似候选列表
        
        try:
            # 输出向量库状态
            vector_count = self.vectorstore.index.ntotal if hasattr(self.vectorstore, 'index') else 0
            doc_count = len(self.vectorstore.docstore._dict) if hasattr(self.vectorstore.docstore, '_dict') else 0
            print(f"[向量检索] 向量库状态: 总向量数={vector_count}, 文档数={doc_count}")
            
            if self.vectorstore.index.ntotal > 0 and doc_count > 0:
                # 先将查询文本编码为向量
                query_embedding = self.embeddings.embed_query(code_a)
                
                # 只搜索有效范围内的向量 (0 ~ 43474，也就是 vector_metadata 的长度或 index_to_docstore_id 的范围)
                import numpy as np
                max_valid_idx = 43474
                if self.vector_metadata is not None:
                    max_valid_idx = min(max_valid_idx, len(self.vector_metadata) - 1)
                else:
                    max_valid_idx = max(self.vectorstore.index_to_docstore_id.keys()) if self.vectorstore.index_to_docstore_id else 30009
                
                # 获取有效范围内的向量
                valid_vectors = self.vectorstore.index.reconstruct_n(0, max_valid_idx + 1)
                query_vec = np.array([query_embedding], dtype=np.float32)
                
                # 计算距离
                diff = valid_vectors - query_vec
                dists = np.linalg.norm(diff, axis=1)
                
                # 获取最近的 k 个
                k = min(200, len(dists))
                sorted_indices = np.argsort(dists)[:k]
                indices = np.array([sorted_indices])
                distances = np.array([dists[sorted_indices]])
                
                print(f"[向量检索] 找到 {len(indices[0])} 个候选文档")
                
                # 处理搜索结果
                same_lang_count = 0
                valid_results = []
                
                for i, idx in enumerate(indices[0]):
                    if idx < 0:
                        continue
                    
                    # 先尝试通过 index_to_docstore_id 获取
                    doc_meta = None
                    doc_content = None
                    try:
                        idx_int = int(idx)
                        doc_id = self.vectorstore.index_to_docstore_id.get(idx_int, None)
                        
                        if doc_id is not None:
                            doc = self.vectorstore.docstore.search(doc_id)
                            if doc is not None:
                                doc_meta = doc.metadata
                                doc_content = doc.page_content
                    except Exception:
                        pass
                    
                    # 如果没有找到，尝试从 vector_metadata 获取
                    if doc_meta is None and self.vector_metadata is not None:
                        try:
                            idx_int = int(idx)
                            if 0 <= idx_int < len(self.vector_metadata):
                                vec_meta = self.vector_metadata[idx_int]
                                # 把 vec_meta 转换为合适的格式
                                if isinstance(vec_meta, dict):
                                    # 标准化一下 language 字段（比如 rb -> ruby，java -> java 等等
                                    lang = vec_meta.get('language', '')
                                    if lang == 'rb':
                                        lang = 'ruby'
                                    # 构造相似的字典
                                    doc_meta = {
                                        'path': vec_meta.get('file_path', ''),
                                        'language': lang
                                    }
                                    # 没有 content 留空
                                    doc_content = ""
                        except Exception:
                            pass
                    
                    if doc_meta is not None:
                        score = distances[0][i]
                        doc_lang = doc_meta.get('language', 'unknown')
                        
                        if doc_lang == language:
                            same_lang_count += 1
                            # 计算相似度
                            similarity = max(0.0, 1.0 - score / 10.0)
                            similarity = similarity ** 0.5
                            
                            vector_candidates.append((similarity, doc_meta, doc_content or ""))
                            
                            if similarity > 0.3:
                                path = doc_meta.get('path', '')
                                print(f"[向量检索] 高相似候选: 相似度={similarity:.4f}, 距离={score:.4f}, 语言={doc_lang}, 路径={path}")
                
                print(f"[向量检索] 同语言候选数: {same_lang_count}")

                # 检查目标代码是否在相似候选中
                target_hash = hashlib.md5(code_b.encode()).hexdigest()
                found_exact = False
                max_similarity = 0.0
                top_similarities = []
                
                for similarity, meta, content in vector_candidates:
                    if meta.get('content_hash') == target_hash:
                        found_exact = True
                        vector_similarity = similarity
                        print(f"[向量检索] [成功] 目标代码在候选集中，向量相似度: {vector_similarity:.4f}")
                        break
                    
                    max_similarity = max(max_similarity, similarity)
                    if similarity > 0.1:
                        top_similarities.append(similarity)
                
                # 如果没有找到完全匹配，但存在高相似度候选
                if not found_exact and vector_candidates:
                    if top_similarities:
                        top_similarities.sort(reverse=True)
                        avg_top_similarity = sum(top_similarities[:3]) / min(3, len(top_similarities))
                        vector_similarity = avg_top_similarity * 0.7
                        print(f"[向量检索] [检测] 未找到完全匹配，但存在{len(top_similarities)}个相似候选，平均相似度: {avg_top_similarity:.4f}")
                    else:
                        vector_similarity = max_similarity * 0.5
                        print(f"[向量检索] [警告] 候选相似度较低，最大相似度: {max_similarity:.4f}")
                    
            else:
                print("[向量检索] 向量库为空或文档为空，跳过该层过滤")
                
        except Exception as e:
            import traceback
            print(f"[智能体] 向量检索失败，跳过第0层过滤: {e}")
            traceback.print_exc()
            # 向量检索失败不影响后续分析

        # 记录向量检索结果
        print(f"[向量检索] 最终向量相似度: {vector_similarity:.4f}")

        # ============================================================================
        # 第一层：哈希过滤
        # ============================================================================
        # 快速检测完全相同的代码
        if self._quick_hash_filter(code_a, code_b):
            print("[智能体] 第一层过滤：检测到文本哈希相同，判定为直接复制。")
            return {
                "similarity_analysis": {
                    "score": 100,
                    "reason": "代码经过标准化处理后完全一致，疑似直接复制粘贴。"
                },
                "metadata": {
                    "filter_layer": "hash_filter",
                    "vector_similarity": vector_similarity,
                    "llm_score": 100,
                    "final_score": 100
                }
            }

        # ============================================================================
        # 第二层：结构比对
        # ============================================================================
        # 分析代码的AST结构相似性
        ast_a = None
        ast_b = None
        struct_sim = 0.0
        
        try:
            # 解析两段代码的AST
            ast_a = self.parser.parse_code(code_a, language)
            ast_b = self.parser.parse_code(code_b, language)

            # 检查AST解析结果
            if ast_a is None or ast_b is None:
                print("[智能体] 警告: 代码解析结果为None，跳过结构比对")
                # AST解析失败不影响后续分析，直接进入LLM分析
            else:
                print("[智能体] 代码解析成功。")
                struct_sim = self._structure_similarity(ast_a, ast_b)
                STRUCT_SIM_THRESHOLD = 0.0
                print(f"[结构过滤] 结构相似度: {struct_sim}, 阈值: {STRUCT_SIM_THRESHOLD}")

                if struct_sim < STRUCT_SIM_THRESHOLD:
                    print(f"[智能体] 🔍 第二层过滤：结构指纹差异过大 ({struct_sim})，判定为明显不相似。")
                    return {
                        "similarity_analysis": {
                            "score": 0,
                            "reason": "代码基础语法结构差异巨大，功能相似性极低。"
                        },
                        "metadata": {
                            "filter_layer": "structure_filter",
                            "structure_similarity": struct_sim
                        }
                    }
        except Exception as e:
            print(f"[智能体] 代码解析异常，跳过结构比对: {e}")
            # AST解析异常不影响后续分析

        print(f"[智能体] 通过前两层过滤，进入第三层LLM深度分析...")

        # ========== 第三层：LLM深度语义分析 ==========
        if ast_a and ast_b:
            print(f"\n[调试] 代码A的AST根节点类型: {ast_a.get('ast', {}).get('type')}")
            print(f"[调试] 代码A的AST子节点数: {len(ast_a.get('ast', {}).get('children', []))}")
            print(f"[调试] 代码B的AST根节点类型: {ast_b.get('ast', {}).get('type')}")
            print(f"[调试] 代码B的AST子节点数: {len(ast_b.get('ast', {}).get('children', []))}")

        # 使用 LangChain 提示模板生成 prompt
        prompt = self.similarity_prompt.format(
            language=language,
            code_a=code_a,
            code_b=code_b
        )

        # 检查LLM是否可用
        if not self.llm:
            print("[智能体] LLM不可用，使用传统语义分析方法")
            analysis_result = self._traditional_semantic_analysis(code_a, code_b, language, struct_sim)
        else:
            try:
                response = self._call_llm_with_retry(prompt)
                print(f"[调试] 响应类型: {type(response)}")
                print(f"[调试] 响应内容: {response}")
                if hasattr(response, 'content'):
                    llm_raw_output = response.content
                else:
                    llm_raw_output = str(response)
                print("[智能体] 获得大模型原始反馈。")
                print(f"[调试] LLM原始输出: {repr(llm_raw_output)}")
            except Exception as e:
                print(f"[调试] LLM调用异常: {e}")
                print("[智能体] LLM调用失败，使用传统语义分析方法")
                analysis_result = self._traditional_semantic_analysis(code_a, code_b, language, struct_sim)
          
            def extract_json(text: str) -> dict:
                # 尝试直接解析
                try:
                    return json.loads(text)
                except:
                    pass
                # 尝试提取第一个 { ... } 块
                import re
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group())
                    except:
                        pass
                # 尝试处理 markdown 代码块
                match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(1))
                    except:
                        pass
                # 都失败则抛出异常
                raise ValueError("无法从 LLM 输出中提取 JSON")

            try:
                analysis_result = extract_json(llm_raw_output)
            except Exception as e:
                print(f"[智能体] LLM返回格式异常: {e}")
                analysis_result = self._traditional_semantic_analysis(code_a, code_b, language, struct_sim)

        # ============================================================================
        # 构建最终分析结果（增强版向量整合）
        # ============================================================================
        
        # 整合向量相似度到最终评分
        llm_score = analysis_result.get("score", 0)
        
        # 根据向量相似度动态调整权重
        if vector_similarity > 0.8:  # 极高向量相似度
            # 向量相似度权重：30%，LLM评分权重：70%
            final_score = llm_score * 0.7 + vector_similarity * 0.3 * 100
            print(f"[评分整合] 极高向量相似度({vector_similarity:.4f})，向量权重30%，调整评分: {llm_score} -> {final_score:.2f}")
        elif vector_similarity > 0.6:  # 高向量相似度
            # 向量相似度权重：25%，LLM评分权重：75%
            final_score = llm_score * 0.75 + vector_similarity * 0.25 * 100
            print(f"[评分整合] 高向量相似度({vector_similarity:.4f})，向量权重25%，调整评分: {llm_score} -> {final_score:.2f}")
        elif vector_similarity > 0.4:  # 中等向量相似度
            # 向量相似度权重：15%，LLM评分权重：85%
            final_score = llm_score * 0.85 + vector_similarity * 0.15 * 100
            print(f"[评分整合] 中等向量相似度({vector_similarity:.4f})，向量权重15%，调整评分: {llm_score} -> {final_score:.2f}")
        elif vector_similarity > 0.2:  # 低向量相似度
            # 向量相似度权重：5%，LLM评分权重：95%
            final_score = llm_score * 0.95 + vector_similarity * 0.05 * 100
            print(f"[评分整合] 低向量相似度({vector_similarity:.4f})，向量权重5%，调整评分: {llm_score} -> {final_score:.2f}")
        else:
            # 极低向量相似度，主要依赖LLM评分
            final_score = llm_score
            print(f"[评分整合] 极低向量相似度({vector_similarity:.4f})，使用LLM评分: {final_score}")
        
        # 确保评分在0-100范围内
        final_score = max(0, min(100, final_score))
        
        # 更新分析结果，包含详细的向量信息
        vector_info = f"向量相似度: {vector_similarity:.2f}"
        if vector_candidates:
            vector_info += f" (检测到{len(vector_candidates)}个候选)"
        
        analysis_result["score"] = final_score
        analysis_result["reason"] = f"{analysis_result.get('reason', '')} [{vector_info}]"
        
        # 添加向量检索的详细分析
        if vector_similarity > 0.5:
            print(f"[向量影响力] 向量检索对最终评分有显著影响 (+{final_score - llm_score:.2f}分)")
        elif vector_similarity > 0.2:
            print(f"[向量影响力] 向量检索对最终评分有轻微影响 (+{final_score - llm_score:.2f}分)")
        
        final_result = {
            "similarity_analysis": analysis_result,
            "metadata": {
                "language": language,
                "ast_a_root_type": ast_a.get('ast', {}).get('type', 'N/A') if ast_a else 'N/A',
                "ast_b_root_type": ast_b.get('ast', {}).get('type', 'N/A') if ast_b else 'N/A',
                "structure_similarity": struct_sim,
                "vector_similarity": vector_similarity,
                "llm_score": llm_score,
                "final_score": final_score,
                "filter_layer": "llm_analysis",
                "agent_phase": "语义分析完成"
            }
        }
        print("[智能体] 分析流程结束。")
        return final_result

    def _traditional_semantic_analysis(self, code_a: str, code_b: str, language: str, structure_similarity: float) -> dict:
        """
        传统语义分析方法
        ================
        
        功能：
        - 当LLM不可用或调用失败时，使用传统方法进行语义分析
        - 基于代码结构相似性和简单语义特征进行分析
        - 提供合理的相似度评分和分析理由
        
        分析策略：
        - 基于结构相似性进行加权评分
        - 考虑代码长度、复杂度等特征
        - 提供合理的分析理由
        
        参数：
        - code_a: 第一段代码
        - code_b: 第二段代码
        - language: 编程语言
        - structure_similarity: 结构相似度分数
        
        返回值：
        - dict: 包含score, reason, function_summary的分析结果
        """
        # 计算代码长度相似度
        len_a = len(code_a)
        len_b = len(code_b)
        len_similarity = 1.0 - abs(len_a - len_b) / max(len_a, len_b, 1)
        
        # 计算行数相似度
        lines_a = len([line for line in code_a.split('\n') if line.strip()])
        lines_b = len([line for line in code_b.split('\n') if line.strip()])
        lines_similarity = 1.0 - abs(lines_a - lines_b) / max(lines_a, lines_b, 1)
        
        # 计算关键字相似度
        keywords = {
            'python': ['def', 'class', 'import', 'from', 'if', 'for', 'while', 'return', 'try', 'except'],
            'java': ['public', 'class', 'void', 'main', 'import', 'static', 'return', 'try', 'catch'],
            'javascript': ['function', 'var', 'let', 'const', 'if', 'for', 'while', 'return', 'try', 'catch'],
            'c': ['#include', 'int', 'main', 'void', 'return', 'if', 'for', 'while'],
            'cpp': ['#include', 'int', 'main', 'void', 'return', 'if', 'for', 'while', 'class'],
            'csharp': ['using', 'class', 'void', 'Main', 'return', 'if', 'for', 'while', 'try', 'catch'],
            'go': ['package', 'func', 'import', 'return', 'if', 'for', 'switch', 'case', 'default', 'type', 'struct', 'interface'],
        }
        
        lang_keywords = keywords.get(language, [])
        keywords_a = sum(1 for keyword in lang_keywords if keyword in code_a.lower())
        keywords_b = sum(1 for keyword in lang_keywords if keyword in code_b.lower())
        keyword_similarity = 1.0 - abs(keywords_a - keywords_b) / max(keywords_a, keywords_b, 1)
        
        # 综合评分：结构相似性权重60%，长度相似性20%，行数相似性10%，关键字相似性10%
        final_score = round(
            structure_similarity * 0.6 + 
            len_similarity * 0.2 + 
            lines_similarity * 0.1 + 
            keyword_similarity * 0.1
        )
        
        # 根据评分生成分析理由
        if final_score >= 80:
            reason = "代码在结构、长度和关键特征上高度相似，功能实现可能相同"
        elif final_score >= 60:
            reason = "代码在多个维度上表现出中等相似性，可能存在相似的实现思路"
        elif final_score >= 40:
            reason = "代码在某些方面有相似之处，但整体差异较为明显"
        elif final_score >= 20:
            reason = "代码相似性较低，主要差异体现在结构和实现方式上"
        else:
            reason = "代码差异显著，功能和实现方式可能完全不同"
        
        return {
            "score": final_score,
            "reason": reason,
            "function_summary": f"{language} 传统语义分析（结构相似度: {structure_similarity:.2f}）"
        }

    def batch_analyze_with_vector(self, query_code: str, language: str, top_k: int = 10):
        """
        向量检索批量分析方法
        ====================
        
        功能：
        - 使用向量库快速找到与查询代码最相似的代码片段
        - 返回相似度排名前K的候选代码
        - 支持大规模代码库的高效检索
        
        检测流程：
        1. 使用向量相似度搜索找到最相似的K个代码
        2. 计算向量距离（L2距离）
        3. 返回候选代码的元信息和相似度分数
        
        参数：
        - query_code: 查询代码字符串
        - language: 编程语言类型
        - top_k: 返回的最相似代码数量（默认10）
        
        返回值：
        - dict: 包含查询信息和候选结果列表
        
        使用场景：
        - 大规模代码库的相似性检索
        - 代码片段查找和匹配
        - 重复代码检测
        """
        # 使用向量相似度搜索找到最相似的代码
        docs_and_scores = self.vectorstore.similarity_search_with_score(query_code, k=top_k)
        results = [(score, doc.metadata) for doc, score in docs_and_scores]

        # 构建详细的结果列表
        detailed_results = []
        for dist, meta in results:
            detailed_results.append({
                'file_path': meta.get('path', ''),          # 代码文件路径
                'vector_distance': float(dist),              # 向量距离（越小越相似）
                'similarity_score': -1,                     # 相似度分数（预留）
                'reason': "无法获取代码内容进行二次分析",  # 分析原因
                'full_result': {}                          # 完整分析结果（预留）
            })
        
        # 返回批量分析结果
        return {
            'query': query_code[:100] + '...',            # 查询代码（截断显示）
            'total_candidates': len(results),             # 候选总数
            'results': detailed_results                   # 详细结果列表
        }

    def batch_analyze(self, code_files: List[dict], language: str) -> dict:
        """
        批量代码相似性分析方法
        =====================
        
        功能：
        - 对多个代码文件进行两两比对
        - 不依赖向量库，直接使用四层过滤策略
        - 适用于小规模代码的全面相似性分析
        
        检测策略：
        - 使用四层过滤策略进行每对代码的比较
        - 支持多种编程语言
        - 返回详细的相似性分析结果
        
        参数：
        - code_files: 代码文件列表，每个文件包含content和path
        - language: 编程语言类型
        
        返回值：
        - dict: 包含分析统计和详细的比对结果
        
        性能特点：
        - 时间复杂度：O(n²)，适合小规模分析
        - 空间复杂度：O(n)，存储比对结果
        - 支持并行处理优化
        
        使用场景：
        - 作业批量相似性检测
        - 代码库质量评估
        - 教学作业抄袭检测
        """
        total = len(code_files)
        comparisons = []

        print(f"[批量分析] 开始处理 {total} 个文件...")

        # 两两比对所有代码文件
        for i in range(total):
            for j in range(i + 1, total):
                file_a = code_files[i]
                file_b = code_files[j]

                print(f"[批量分析] 比对: {file_a['path']} <-> {file_b['path']}")
                result = self.analyze_code_similarity(
                    file_a['content'],
                    file_b['content'],
                    language
                )

                if 'error' in result:
                    similarity_score = -1
                    reason = result['error']
                    filter_layer = 'error'
                else:
                    similarity_score = result.get('similarity_analysis', {}).get('score', -1)
                    reason = result.get('similarity_analysis', {}).get('reason', '')
                    filter_layer = result.get('metadata', {}).get('filter_layer', 'unknown')

                comparisons.append({
                    "file_a": file_a['path'],
                    "file_b": file_b['path'],
                    "similarity_score": similarity_score,
                    "reason": reason,
                    "filter_layer": filter_layer,
                    "full_result": result
                })

        valid_scores = [c['similarity_score'] for c in comparisons if c['similarity_score'] >= 0]
        avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0
        max_score = max(valid_scores) if valid_scores else 0
        min_score = min(valid_scores) if valid_scores else 0

        summary = {
            "total_files": total,
            "total_comparisons": len(comparisons),
            "average_score": round(avg_score, 2),
            "max_score": max_score,
            "min_score": min_score
        }

        return {
            "summary": summary,
            "comparisons": comparisons
        }
if __name__ == '__main__':
    print("=== 开始智能体验证测试 ===")
    agent = CodeDetectionAgent()

    test_code_1 = """def calculate_sum(numbers):
        total = 0
        for num in numbers:
        total = total + num
        return total
        """

    test_code_2 = """def sum_list(elements):
        result = 0
        for item in elements:
        result += item
        return result
        """

    print("\n[测试] 分析两段'列表求和'函数...")
    result = agent.analyze_code_similarity(test_code_1, test_code_2, "python")

    print("\n=== 最终分析结果 ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("===================")