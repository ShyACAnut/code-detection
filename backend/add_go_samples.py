#!/usr/bin/env python3
"""向向量库中添加Go语言示例代码"""
import os
import sys
sys.path.append(os.path.dirname(__file__))

from langchain_core.documents import Document
from code_agent import CodeDetectionAgent

# 一些Go语言的示例代码，涵盖常见算法和数据结构
GO_SAMPLES = [
    {
        "path": "go/hello_world.go",
        "content": """package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}
"""
    },
    {
        "path": "go/bubble_sort.go",
        "content": """package main

import "fmt"

func bubbleSort(arr []int) []int {
    n := len(arr)
    for i := 0; i < n-1; i++ {
        for j := 0; j < n-i-1; j++ {
            if arr[j] > arr[j+1] {
                arr[j], arr[j+1] = arr[j+1], arr[j]
            }
        }
    }
    return arr
}

func main() {
    data := []int{64, 34, 25, 12, 22, 11, 90}
    fmt.Println("排序前:", data)
    result := bubbleSort(data)
    fmt.Println("排序后:", result)
}
"""
    },
    {
        "path": "go/quick_sort.go",
        "content": """package main

import "fmt"

func quickSort(arr []int) []int {
    if len(arr) <= 1 {
        return arr
    }
    pivot := arr[len(arr)/2]
    var left, right []int
    for _, x := range arr {
        if x < pivot {
            left = append(left, x)
        } else if x > pivot {
            right = append(right, x)
        }
    }
    return append(append(quickSort(left), pivot), quickSort(right)...)
}

func main() {
    data := []int{10, 7, 8, 9, 1, 5}
    fmt.Println("排序前:", data)
    sorted := quickSort(data)
    fmt.Println("排序后:", sorted)
}
"""
    },
    {
        "path": "go/merge_sort.go",
        "content": """package main

import "fmt"

func mergeSort(arr []int) []int {
    if len(arr) <= 1 {
        return arr
    }
    mid := len(arr) / 2
    left := mergeSort(arr[:mid])
    right := mergeSort(arr[mid:])
    return merge(left, right)
}

func merge(left, right []int) []int {
    result := make([]int, 0, len(left)+len(right))
    i, j := 0, 0
    for i < len(left) && j < len(right) {
        if left[i] < right[j] {
            result = append(result, left[i])
            i++
        } else {
            result = append(result, right[j])
            j++
        }
    }
    result = append(result, left[i:]...)
    result = append(result, right[j:]...)
    return result
}

func main() {
    data := []int{38, 27, 43, 3, 9, 82, 10}
    fmt.Println("排序前:", data)
    sorted := mergeSort(data)
    fmt.Println("排序后:", sorted)
}
"""
    },
    {
        "path": "go/linked_list.go",
        "content": """package main

import "fmt"

type ListNode struct {
    Val  int
    Next *ListNode
}

func createList(arr []int) *ListNode {
    if len(arr) == 0 {
        return nil
    }
    head := &ListNode{Val: arr[0]}
    current := head
    for i := 1; i < len(arr); i++ {
        current.Next = &ListNode{Val: arr[i]}
        current = current.Next
    }
    return head
}

func printList(head *ListNode) {
    for head != nil {
        fmt.Printf("%d ", head.Val)
        head = head.Next
    }
    fmt.Println()
}

func main() {
    data := []int{1, 2, 3, 4, 5}
    list := createList(data)
    printList(list)
}
"""
    },
    {
        "path": "go/binary_search.go",
        "content": """package main

import "fmt"

func binarySearch(arr []int, target int) int {
    left, right := 0, len(arr)-1
    for left <= right {
        mid := left + (right-left)/2
        if arr[mid] == target {
            return mid
        } else if arr[mid] < target {
            left = mid + 1
        } else {
            right = mid - 1
        }
    }
    return -1
}

func main() {
    data := []int{1, 3, 5, 7, 9, 11, 13}
    target := 7
    index := binarySearch(data, target)
    if index != -1 {
        fmt.Printf("找到 %d，索引: %d\n", target, index)
    } else {
        fmt.Printf("未找到 %d\n", target)
    }
}
"""
    },
    {
        "path": "go/fibonacci.go",
        "content": """package main

import "fmt"

func fibonacci(n int) int {
    if n <= 1 {
        return n
    }
    return fibonacci(n-1) + fibonacci(n-2)
}

func fibonacciIterative(n int) int {
    if n <= 1 {
        return n
    }
    a, b := 0, 1
    for i := 2; i <= n; i++ {
        a, b = b, a+b
    }
    return b
}

func main() {
    for i := 0; i < 10; i++ {
        fmt.Printf("Fib(%d) = %d\n", i, fibonacci(i))
    }
}
"""
    },
    {
        "path": "go/stack.go",
        "content": """package main

import "fmt"

type Stack struct {
    items []interface{}
}

func (s *Stack) Push(item interface{}) {
    s.items = append(s.items, item)
}

func (s *Stack) Pop() (interface{}, bool) {
    if len(s.items) == 0 {
        return nil, false
    }
    index := len(s.items) - 1
    item := s.items[index]
    s.items = s.items[:index]
    return item, true
}

func (s *Stack) Peek() (interface{}, bool) {
    if len(s.items) == 0 {
        return nil, false
    }
    return s.items[len(s.items)-1], true
}

func main() {
    stack := &Stack{}
    stack.Push(1)
    stack.Push(2)
    stack.Push(3)
    if val, ok := stack.Pop(); ok {
        fmt.Println("弹出:", val)
    }
    if val, ok := stack.Peek(); ok {
        fmt.Println("栈顶:", val)
    }
}
"""
    },
    {
        "path": "go/queue.go",
        "content": """package main

import "fmt"

type Queue struct {
    items []interface{}
}

func (q *Queue) Enqueue(item interface{}) {
    q.items = append(q.items, item)
}

func (q *Queue) Dequeue() (interface{}, bool) {
    if len(q.items) == 0 {
        return nil, false
    }
    item := q.items[0]
    q.items = q.items[1:]
    return item, true
}

func (q *Queue) Front() (interface{}, bool) {
    if len(q.items) == 0 {
        return nil, false
    }
    return q.items[0], true
}

func main() {
    queue := &Queue{}
    queue.Enqueue("a")
    queue.Enqueue("b")
    queue.Enqueue("c")
    if val, ok := queue.Dequeue(); ok {
        fmt.Println("出队:", val)
    }
    if val, ok := queue.Front(); ok {
        fmt.Println("队首:", val)
    }
}
"""
    },
    {
        "path": "go/goroutine_channel.go",
        "content": """package main

import (
    "fmt"
    "time"
)

func worker(id int, jobs <-chan int, results chan<- int) {
    for j := range jobs {
        fmt.Printf("Worker %d 开始处理任务 %d\n", id, j)
        time.Sleep(time.Second)
        fmt.Printf("Worker %d 完成任务 %d\n", id, j)
        results <- j * 2
    }
}

func main() {
    const numJobs = 5
    jobs := make(chan int, numJobs)
    results := make(chan int, numJobs)

    for w := 1; w <= 3; w++ {
        go worker(w, jobs, results)
    }

    for j := 1; j <= numJobs; j++ {
        jobs <- j
    }
    close(jobs)

    for a := 1; a <= numJobs; a++ {
        result := <-results
        fmt.Printf("得到结果: %d\n", result)
    }
}
"""
    },
]

def main():
    print("="*60)
    print("添加Go语言示例到向量库")
    print("="*60)
    
    try:
        agent = CodeDetectionAgent()
    except Exception as e:
        print(f"初始化智能体失败: {e}")
        return
    
    # 统计现有文档
    existing = {}
    for doc_id, doc in agent.vectorstore.docstore._dict.items():
        lang = doc.metadata.get('language', 'unknown')
        existing[lang] = existing.get(lang, 0) + 1
    
    print(f"现有向量库统计:")
    for lang, count in sorted(existing.items()):
        print(f"  {lang}: {count}")
    print()
    
    # 创建要添加的文档
    docs = []
    for sample in GO_SAMPLES:
        doc = Document(
            page_content=sample['content'],
            metadata={
                'path': sample['path'],
                'language': 'go',
                'source': 'go_sample'
            }
        )
        docs.append(doc)
    
    print(f"准备添加 {len(docs)} 个Go语言示例...")
    
    # 添加到向量库
    try:
        agent.vectorstore.add_documents(docs)
        print("[OK] 添加成功!")
    except Exception as e:
        print(f"添加失败: {e}")
        return
    
    # 修复 index_to_docstore_id 的键类型
    print("[INFO] 修复索引映射...")
    old_mapping = agent.vectorstore.index_to_docstore_id.copy()
    agent.vectorstore.index_to_docstore_id.clear()
    for k, v in old_mapping.items():
        int_idx = int(k) if not isinstance(k, int) else k
        str_doc_id = str(v) if not isinstance(v, str) else v
        agent.vectorstore.index_to_docstore_id[int_idx] = str_doc_id
    print(f"[OK] 修复完成，索引映射数量: {len(agent.vectorstore.index_to_docstore_id)}")
    
    # 保存向量库
    save_path = os.path.join(os.path.dirname(__file__), 'faiss_index')
    try:
        agent.vectorstore.save_local(save_path)
        print(f"[OK] 向量库已保存到: {save_path}")
    except Exception as e:
        print(f"保存失败: {e}")
        return
    
    # 再次统计
    new_stats = {}
    for doc_id, doc in agent.vectorstore.docstore._dict.items():
        lang = doc.metadata.get('language', 'unknown')
        new_stats[lang] = new_stats.get(lang, 0) + 1
    
    print()
    print("更新后的统计:")
    for lang, count in sorted(new_stats.items()):
        print(f"  {lang}: {count}")
    
    print()
    print("="*60)
    print("完成!")

if __name__ == '__main__':
    main()
