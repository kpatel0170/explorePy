import os
import json
import logging
from datetime import datetime
from typing import List, Dict
from requests import get
from bs4 import BeautifulSoup

# Constants
CURRENT_YEAR = datetime.now().year
DATASET_LOCATION = os.path.join(os.path.dirname(__file__), "files")
os.makedirs(DATASET_LOCATION, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0"
}

IMDB_BASE_URL = "https://www.imdb.com"
IMDB_POPULAR_MOVIES_URL = "https://www.imdb.com/chart/moviemeter/"

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("imdb_scraper.log"),
        logging.StreamHandler()
    ]
)

# Fetches information about popular movies from IMDb.
def fetch_popular_movies() -> List[Dict]:
    logging.info(f"Fetching popular movies from {IMDB_POPULAR_MOVIES_URL}")
    movie_data = []

    try:
        response = get(IMDB_POPULAR_MOVIES_URL, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        json_data = json.loads(soup.find("script", type="application/ld+json").text)

        for movie in json_data.get("itemListElement", []):
            movie_name = movie["item"].get("name", "Unknown Title")
            movie_rating = movie["item"].get("aggregateRating", {}).get("ratingValue", "N/A")
            movie_link = movie["item"].get("url", "")
            movie_data.append({"name": movie_name, "rating": movie_rating, "link": movie_link})

    except Exception as e:
        logging.error(f"Error fetching popular movies: {e}")

    return movie_data

def save_to_file(data: List[Dict], file_name: str):
    output_file_path = os.path.join(DATASET_LOCATION, file_name)
    try:
        with open(output_file_path, 'w', encoding='utf-8') as file:
            for movie in data:
                file.write(f"{movie['name']}\nLink: {movie['link']}\n"
                           f"Rating: {movie['rating']}\nCrew: {movie.get('crew', 'N/A')}\n\n")
        logging.info(f"Data saved to {output_file_path}")
    except Exception as e:
        logging.error(f"Error saving data to file {file_name}: {e}")

def main():
    logging.info("Starting IMDb scraper")
    try:
        popular_movies = fetch_popular_movies()
        save_to_file(popular_movies, "Popular_Movies.txt")

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        logging.info("IMDb scraper finished")

if __name__ == "__main__":
    main()
