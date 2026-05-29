import random


def binary_search(data, target):
    low_pointer = 0
    high_pointer = len(data) - 1
    while low_pointer <= high_pointer:
        mid_point = (low_pointer + high_pointer) // 2
        if data[mid_point] == target:
            return mid_point
        elif data[mid_point] < target:
            low_pointer = mid_point + 1
        else:
            high_pointer = mid_point - 1
    return -1


def main():
    count = 10
    max_val = 100
    data = [random.randint(1, max_val) for _ in range(count)]
    data.sort()
    print("Data:", data)
    target = int(input("Enter target value: "))
    target_pos = binary_search(data, target)
    if target_pos == -1:
        print("Your target value is not in the list.")
    else:
        print("Your target value has been found at index", target_pos)


if __name__ == "__main__":
    main()
