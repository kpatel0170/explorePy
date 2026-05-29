import requests
from bs4 import BeautifulSoup

URL = "http://quotes.toscrape.com"


def main():
    response = requests.get(URL, headers={"Accept": "text/html"}, timeout=10)
    response.raise_for_status()

    parsed_response = BeautifulSoup(response.text, "html.parser")
    print(parsed_response.prettify())


if __name__ == "__main__":
    main()
