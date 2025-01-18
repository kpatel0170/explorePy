# 100 Doors
# • There are 100 doors in a row that are all initially closed
# • You make 100 passes by the doors
# • On the first pass, you visit every door in sequence and toggle its state (if the door is closed, you open it; if it is open, you close it)
# The second time, you only visit every second door (door 2, 4, 6, ...) and toggle it

doors = [False] * 101

# Let's do just one pass
# for i in range(1, 101):
#     doors[i] = not doors[i]  # Using `not` to invert the Boolean value.

# Time for a nested for loop

# for x in range(1, 6):
#     for y in range(1, 4):
#         print("x:", x, "y:", y)

# Detour - steps in for loop
# for i in range(1, 11, 2):
#     print(i)


# Solution:

for i in range(1, 101):
    for j in range(i, 101, i):
        doors[j] = not doors[j]

for i in range(1, 101):
    if doors[i] is True:
        print(i, end=", ")
