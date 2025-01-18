# The Change Making Problem - Greedy approach
# Find the minimum number of coins from a set of denominations that add up to a given amount of money.

# For example, say you have coins available of denominations 1p, 2p, 5p, 10p, 20p, 50p, £1, and £2, as in the UK.
# What is the minimum number of coins you need to make 24p?
# Three: 20p + 2p + 2p
# £1.63?
# Five: £1 + 50p + 10p + 2p + 1p

# Greedy algorithm
def make_change(target_amount):
    denominations = [200, 100, 50, 20, 10, 5, 2, 1]  # Order is important!
    coin_count = 0  # Initialise count
    values = []  # Store values here
    for coin in denominations:
        while target_amount >= coin:  # Use the current coin until its value is too large
            target_amount -= coin  # Decrease the remaining amount
            values.append(coin)  # Make a note of which coin was used
            coin_count += 1  # Increase the coin count
    return coin_count, values



print(make_change(24))  # 3: 20p + 2p + 2p
print(make_change(163))  # 5: £1 + 50p + 10p + 2p + 1p