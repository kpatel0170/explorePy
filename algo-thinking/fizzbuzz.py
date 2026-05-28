# Fizz Buzz

# Fizz Buzz is a game for two or more players

# • Take it in turns to count aloud from 1 to 100, but each time you are going to say a multiple of 3, replace it with the word "fizz"

# For multiples of 5, say "buzz'" and for numbers that are multiples of both 3 and 5, say "fizz, buzz"

# print(10 % 3)
# print(3 % 3)

# for i in range(1, 101):
#     if i % 3 == 0 and i % 5 != 0:
#         print("fizz")
#     elif i % 5 == 0 and i % 3 != 0:
#         print("buzz")
#     elif i % 5 == 0 and i % 3 == 0:
#         print("fizzbuzz")
#     else:
#         print(i)


# more approachable and easy to read
for i in range(1, 101):
    if i % 5 == 0 and i % 3 == 0:
        print("fizzbuzz")
    elif i % 3 == 0:
        print("fizz")
    elif i % 5 == 0:
        print("buzz")
    else:
        print(i)
