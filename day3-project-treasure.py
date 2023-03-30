
print('Welcome to Treasure Island\nYour mission is to find the treasure')

choice = input("You're at a cross road. Where do you want to go? Type \"left\" or \"right\"\n").lower()
if choice == "left":
    choice2 = input("Do you want to \"swim\" or \"wait\"\n").lower()
    if choice == "swim":
        choice3 = input('Pick any of the three roads. red, yellow and blue\n').lower()
        if choice3 == "red":
            print("The room full of fire! Game Over")
        elif choice == "treasure":
            print("You found the Treasure!! You won!")
        elif choice == "blue":
            print("The room is full of beasts. Game over!")
        else:
            print("Invalid input")
    else:
        print("Game over! you have been attacked by crocodile")
else:
    print("Game Over")
