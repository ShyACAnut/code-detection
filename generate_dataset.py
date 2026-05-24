import json
import random
import string

def generate_random_name(length=6):
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))

def generate_code_pair():
    patterns = [
        {
            'code_a': f'def {generate_random_name()}(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(0, n-i-1):\n            if arr[j] > arr[j+1]:\n                arr[j], arr[j+1] = arr[j+1], arr[j]\n    return arr',
            'code_b': f'def {generate_random_name()}(array):\n    length = len(array)\n    for i in range(length):\n        for j in range(0, length-i-1):\n            if array[j] > array[j+1]:\n                array[j], array[j+1] = array[j+1], array[j]\n    return array'
        },
        {
            'code_a': f'def {generate_random_name()}(nums):\n    max_val = nums[0]\n    for num in nums:\n        if num > max_val:\n            max_val = num\n    return max_val',
            'code_b': f'def {generate_random_name()}(numbers):\n    max_value = numbers[0]\n    for n in numbers:\n        if n > max_value:\n            max_value = n\n    return max_value'
        },
        {
            'code_a': f'def {generate_random_name()}(n):\n    if n < 2:\n        return False\n    for i in range(2, int(n**0.5)+1):\n        if n % i == 0:\n            return False\n    return True',
            'code_b': f'def {generate_random_name()}(num):\n    if num < 2:\n        return False\n    for i in range(2, int(num**0.5)+1):\n        if num % i == 0:\n            return False\n    return True'
        },
        {
            'code_a': f'def {generate_random_name()}(n):\n    a, b = 0, 1\n    result = []\n    for _ in range(n):\n        result.append(a)\n        a, b = b, a + b\n    return result',
            'code_b': f'def {generate_random_name()}(n):\n    first, second = 0, 1\n    sequence = []\n    for _ in range(n):\n        sequence.append(first)\n        first, second = second, first + second\n    return sequence'
        },
        {
            'code_a': f'def {generate_random_name()}(n):\n    if n <= 1:\n        return 1\n    return n * {generate_random_name()}(n-1)',
            'code_b': f'def {generate_random_name()}(n):\n    if n <= 1:\n        return 1\n    return n * {generate_random_name()}(n-1)'
        },
        {
            'code_a': f'def {generate_random_name()}(s):\n    return s[::-1]',
            'code_b': f'def {generate_random_name()}(str_input):\n    return str_input[::-1]'
        },
        {
            'code_a': f'def {generate_random_name()}(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1',
            'code_b': f'def {generate_random_name()}(array, target_value):\n    low, high = 0, len(array) - 1\n    while low <= high:\n        middle = (low + high) // 2\n        if array[middle] == target_value:\n            return middle\n        elif array[middle] < target_value:\n            low = middle + 1\n        else:\n            high = middle - 1\n    return -1'
        },
        {
            'code_a': f'def {generate_random_name()}(nums):\n    total = 0\n    for num in nums:\n        total += num\n    return total',
            'code_b': f'def {generate_random_name()}(numbers):\n    result = 0\n    for n in numbers:\n        result += n\n    return result'
        },
        {
            'code_a': f'def {generate_random_name()}(lst):\n    return list(set(lst))',
            'code_b': f'def {generate_random_name()}(input_list):\n    return list(set(input_list))'
        },
        {
            'code_a': f'def {generate_random_name()}(s1, s2):\n    return sorted(s1) == sorted(s2)',
            'code_b': f'def {generate_random_name()}(str1, str2):\n    return sorted(str1) == sorted(str2)'
        },
        {
            'code_a': f'def {generate_random_name()}(s):\n    return s == s[::-1]',
            'code_b': f'def {generate_random_name()}(string):\n    return string == string[::-1]'
        },
        {
            'code_a': f'def {generate_random_name()}(base, exp):\n    if exp == 0:\n        return 1\n    if exp < 0:\n        return 1 / {generate_random_name()}(base, -exp)\n    return base * {generate_random_name()}(base, exp-1)',
            'code_b': f'def {generate_random_name()}(base_num, exponent):\n    if exponent == 0:\n        return 1\n    if exponent < 0:\n        return 1 / {generate_random_name()}(base_num, -exponent)\n    return base_num * {generate_random_name()}(base_num, exponent-1)'
        },
        {
            'code_a': f'def {generate_random_name()}(nums, target):\n    for i in range(len(nums)):\n        for j in range(i+1, len(nums)):\n            if nums[i] + nums[j] == target:\n                return [i, j]\n    return []',
            'code_b': f'def {generate_random_name()}(arr, target_sum):\n    for i in range(len(arr)):\n        for j in range(i+1, len(arr)):\n            if arr[i] + arr[j] == target_sum:\n                return [i, j]\n    return []'
        },
        {
            'code_a': f'def {generate_random_name()}(arr):\n    for i in range(len(arr)):\n        min_idx = i\n        for j in range(i+1, len(arr)):\n            if arr[j] < arr[min_idx]:\n                min_idx = j\n        arr[i], arr[min_idx] = arr[min_idx], arr[i]\n    return arr',
            'code_b': f'def {generate_random_name()}(array):\n    for i in range(len(array)):\n        min_index = i\n        for j in range(i+1, len(array)):\n            if array[j] < array[min_index]:\n                min_index = j\n        array[i], array[min_index] = array[min_index], array[i]\n    return array'
        },
        {
            'code_a': f'def {generate_random_name()}(arr):\n    for i in range(1, len(arr)):\n        key = arr[i]\n        j = i - 1\n        while j >= 0 and arr[j] > key:\n            arr[j+1] = arr[j]\n            j -= 1\n        arr[j+1] = key\n    return arr',
            'code_b': f'def {generate_random_name()}(input_list):\n    for i in range(1, len(input_list)):\n        current = input_list[i]\n        j = i - 1\n        while j >= 0 and input_list[j] > current:\n            input_list[j+1] = input_list[j]\n            j -= 1\n        input_list[j+1] = current\n    return input_list'
        }
    ]
    return random.choice(patterns)

data = []
for _ in range(2000):
    pair = generate_code_pair()
    data.append({'code_a': pair['code_a'], 'code_b': pair['code_b']})

with open('test_dataset_2000.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)

print('生成完成！文件已保存为 test_dataset_2000.json')