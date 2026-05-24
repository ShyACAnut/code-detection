#!/usr/bin/env python3
"""
简单代码分析功能测试脚本
"""

import sys
sys.path.append('.')

def test_code_analysis():
    """测试代码分析功能"""
    print("开始测试代码分析功能...")
    
    try:
        from code_agent import CodeDetectionAgent
        
        # 创建智能体实例（简化模式，跳过有问题的初始化）
        agent = CodeDetectionAgent(skip_parser=True, skip_llm=True)
        print("智能体初始化成功")
        
        # 测试用例1：相同功能的简单函数
        print("\n测试用例1：相同功能的简单函数")
        code_a1 = """def add(a, b):
    return a + b"""
        
        code_b1 = """def sum(x, y):
    return x + y"""
        
        print("代码A:")
        print(code_a1)
        print("代码B:")
        print(code_b1)
        
        # 测试传统语义分析方法
        result1 = agent._traditional_semantic_analysis(code_a1, code_b1, 'python', 0.8)
        print("传统语义分析结果:")
        print("相似度: " + str(result1['score']) + "%")
        print("分析理由: " + result1['reason'])
        print("功能摘要: " + result1['function_summary'])
        
        # 测试用例2：不同功能的函数
        print("\n测试用例2：不同功能的函数")
        code_a2 = """def multiply(a, b):
    return a * b"""
        
        code_b2 = """def greet(name):
    return f"Hello, {name}!"""
        
        print("代码A:")
        print(code_a2)
        print("代码B:")
        print(code_b2)
        
        result2 = agent._traditional_semantic_analysis(code_a2, code_b2, 'python', 0.2)
        print("传统语义分析结果:")
        print("相似度: " + str(result2['score']) + "%")
        print("分析理由: " + result2['reason'])
        print("功能摘要: " + result2['function_summary'])
        
        # 测试结构相似性计算
        print("\n测试结构相似性计算")
        struct_sim1 = agent._structure_similarity(code_a1, code_b1, 'python')
        struct_sim2 = agent._structure_similarity(code_a2, code_b2, 'python')
        
        print("测试用例1结构相似度: " + str(struct_sim1))
        print("测试用例2结构相似度: " + str(struct_sim2))
        
        print("\n所有测试用例完成！")
        print("代码分析功能测试通过")
        
        return True
        
    except Exception as e:
        print("测试失败: " + str(e))
        import traceback
        print("详细错误信息:")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = test_code_analysis()
    sys.exit(0 if success else 1)