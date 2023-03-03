print("Welcome to the tip calculator\n")
total = float(input("What is the total amount? $"))
tip = int(input("What percentage tip would you like to give 10, 12, or 15? "))
people = int(input("How many people to split the bill? "))
billAmount = tip / 100 * total + total
billperPerson = round(billAmount/people, 2)
print(billAmount)
print("Each person should pay $" + billperPerson)
