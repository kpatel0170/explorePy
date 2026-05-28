import os

base_dir = os.path.join(os.path.dirname(__file__), "files")
os.makedirs(base_dir, exist_ok=True)

input_file_path = os.path.join(base_dir, "inputFile.txt")
pass_file_path = os.path.join(base_dir, "passFile.txt")
fail_file_path = os.path.join(base_dir, "failFile.txt")

# inputFile = open(input_file_path, "r")
# for line in inputFile:
#     line_split = line.split()
#     if line_split[2] == "P":
#         print(line)
# inputFile.close()



# loop through each line in inputFile.txt
# uncomment the following lines of code and fill in
with open(input_file_path, "r") as inputFile, \
        open(pass_file_path, "w") as passFile, \
        open(fail_file_path, "w") as failFile:
    
    # Process each line in the input file
    for line in inputFile:
        line_split = line.split()
        if len(line_split) > 2 and line_split[2] == "P":
            passFile.write(line)
        else:
            failFile.write(line)