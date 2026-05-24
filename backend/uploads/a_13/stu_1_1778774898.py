#!/usr/bin/env python3
"""检查 index.pkl 文件"""

import os
import pickle
import sys

def main():
    index_path = os.path.join(os.path.dirname(__file__), "faiss_index", "index.pkl")
    
    print(f"读取 {index_path}")
    
    if not os.path.exists(index_path):
        print("文件不存在!")
        return
    
    with open(index_path, "rb") as f:
        data = pickle.load(f)
    
    print(f"\n数据类型: {type(data)}")
    print(f"长度: {len(data) if hasattr(data, '__len__') else 'N/A'}")
    
    if isinstance(data, tuple):
        for i, item in enumerate(data):
            print(f"\n  [{i}] 类型: {type(item)}")
            if hasattr(item, '__dict__'):
                print(f"      属性: {[k for k in item.__dict__.keys() if not k.startswith('_')]}")
            if hasattr(item, '_dict'):
                print(f"      _dict 长度: {len(item._dict)}")
                if item._dict:
                    first_key = next(iter(item._dict.keys()))
                    first_val = item._dict[first_key]
                    print(f"      第一个键: {first_key}")
                    print(f"      第一个值: {type(first_val)}")
                    if hasattr(first_val, 'page_content'):
                        print(f"        page_content: {first_val.page_content[:100] if first_val.page_content else 'N/A'}")
                    if hasattr(first_val, 'metadata'):
                        print(f"        metadata: {first_val.metadata}")

if __name__ == "__main__":
    main()
