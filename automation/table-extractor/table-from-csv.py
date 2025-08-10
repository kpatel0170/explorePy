import pandas as pd

# Fetch data
data = pd.read_csv("https://www.football-data.co.uk/mmz4281/2122/E0.csv")

# print(data.head())  # Show  

formated_data = data.rename(columns={"Div": "Division", "Date": "Match Date", "HomeTeam": "Home Team", "AwayTeam": "Away Team", "FTHG": "Full Time Home Goals", "FTAG": "Full Time Away Goals"})


print(formated_data.head())  # Show


