# find all the even numbers up to 100


# Brute force:
for i in range(1, 101):
    if i % 2 == 0:
        print(i)

# optimized
for i in range(1, 101, 2):
    print(i)

