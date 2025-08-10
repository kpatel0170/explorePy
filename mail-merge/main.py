# TODO: Create a letter using starting_letter.txt
# for each name in invited_names.txt
# Replace the [name] placeholder with the actual name.
# Save the letters in the folder "ReadyToSend".

# Hint1: This method will help you: https://www.w3schools.com/python/ref_file_readlines.asp
# Hint2: This method will also help you: https://www.w3schools.com/python/ref_string_replace.asp
# Hint3: THis method will help you: https://www.w3schools.com/python/ref_string_strip.asp

# Read in the names from the input file
with open("./Input/Names/invited_names.txt") as data:
    names = data.readlines()

# Read in the contents of the starting letter with the correct encoding
with open("./Input/Letters/starting_letter.txt") as letter_file:
    starting_letter_contents = letter_file.read()
    # Replace the [name] placeholder with each name and save a new file for each name
    for name in names:
        # Strip any whitespace from the name
        name = name.strip()
        # Replace the [name] placeholder with the actual name
        new_letter_contents = starting_letter_contents.replace("[name]", name)
        # Save the new letter to a file
        with open(f"./Output/ReadyToSend/letter_for_{name}.txt", "w") as output_file:
            output_file.write(new_letter_contents)

