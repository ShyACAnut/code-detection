#!/usr/bin/env python3
"""检查保存的faiss_index目录内容"""
import os
import sys
import pickle
sys.path.append(os.path.dirname(__file__))

def main():
    faiss_dir = os.path.join(os.path.dirname(__file__), 'faiss_index')
    print("="*60)
    print("检查向量库内容")
    print("="*60)
    print()
    
    files = os.listdir(faiss_dir)
    print("faiss_index目录内容:")
    for f in sorted(files):
        path = os.path.join(faiss_dir, f)
        size = os.path.getsize(path)
        print(f"  {f:40s} | {size:,} bytes")
    
    print()
    
    # 检查 index.pkl
    print("尝试加载 index.pkl...")
    index_pkl_path = os.path.join(faiss_dir, 'index.pkl')
    with open(index_pkl_path, 'rb') as f:
        index_data = pickle.load(f)
    print(f"  index.pkl类型: {type(index_data)}")
    
    if hasattr(index_data, 'index_to_docstore_id'):
        idx_map = index_data.index_to_docstore_id
        print(f"  index_to_docstore_id长度: {len(idx_map)}")
        keys = list(idx_map.keys())
        if keys:
            print(f"  索引范围: [{min(keys)} ~ {max(keys)}]")
    
    print()
    
    print("="*60)
    
    # 看看checkpoint
    print("检查checkpoint...")
    checkpoint_path = os.path.join(faiss_dir, 'checkpoint_batch_9620_backup.pkl')
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path, 'rb') as f:
            cp = pickle.load(f)
        print(f"checkpoint加载成功!")
        print(f"  checkpoint类型: {type(cp)}")

if __name__ == '__main__':
    main()
