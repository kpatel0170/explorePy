# Linear Search - Brute force

def linear_search(data, target):
    for i in range(1, len(data) + 1):
        if data[i] == target:
            return i 
    return -1

    # for idx, val in enumerate(data):
    #     if val == target:
    #         return idx  # Early exit if item is found.
    # return -1



data = [4, 5, 2, 7, 1, 8]
target = 1
result = linear_search(data, target)
if result == -1:
    print("Item not found.")
else:
    print(f"Item found at position {result}.")