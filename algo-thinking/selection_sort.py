def find_min(xs):
    min_index = 0
    for i in range(len(xs)):
        if xs[i] < xs[min_index]:
            min_index = i
    return xs[min_index]


def selection_sort(xs):
    for i in range(len(xs) - 1):
        min_index = i
        for j in range(i + 1, len(xs)):
            if xs[j] < xs[min_index]:
                min_index = j
        xs[i], xs[min_index] = xs[min_index], xs[i]


def main():
    xs = [-4, 2, 5, 8, -7, 3, 6, -1, 7]
    print(xs)
    selection_sort(xs)
    print(xs)
    print(all(xs[i] <= xs[i + 1] for i in range(len(xs) - 1)))


if __name__ == "__main__":
    main()
