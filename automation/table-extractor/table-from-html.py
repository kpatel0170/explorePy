import pandas as pd

# Fetch all tables
simpsons = pd.read_html('https://en.wikipedia.org/wiki/List_of_The_Simpsons_episodes')

# Print the number of tables found
print(f'Number of tables found: {len(simpsons)}')

# Print the first 5 rows of each table
for idx, table in enumerate(simpsons):
    print(f"\nTable {idx}:")
    print(table.head())  # Show
