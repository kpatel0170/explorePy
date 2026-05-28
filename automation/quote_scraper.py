import requests
from bs4 import BeautifulSoup

# Step 1: Send a request to the website
url = 'http://quotes.toscrape.com'
response = requests.get(url)

# Step 2: Parse the page content
soup = BeautifulSoup(response.text, 'html.parser')

# Step 3: Extract the quotes, authors, and tags
quotes = soup.find_all('div', class_='quote')

# Step 4: Print the results
for quote in quotes:
    text = quote.find('span', class_='text').text
    author = quote.find('small', class_='author').text
    tags = [tag.text for tag in quote.find_all('a', class_='tag')]

    print(f"Quote: {text}")
    print(f"Author: {author}")
    print(f"Tags: {', '.join(tags)}")
    print('-' * 80)
