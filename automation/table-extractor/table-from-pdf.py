import camelot

file = "https://raw.githubusercontent.com/tabulapdf/tabula-java/master/src/test/resources/technology/tabula/china.pdf"
# Read the PDF file
tables = camelot.read_pdf("sample.pdf") 

# Print the number of tables found
print(f'Number of tables found: {tables[0].df}')


tables.export("sample.csv", f="csv", compress=True)  # Export all tables to a CSV file
tables[0].to_csv("sample.csv")  # Export the first table to a CSV file