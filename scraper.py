import csv
import logging
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AmazonScraper:
    def __init__(self, search_term: str, domain: str = "in", max_pages: int = 20):
        self.search_term = search_term
        self.base_url = f"https://www.amazon.{domain}"
        self.max_pages = max_pages
        self.scraped_data = []
        self.driver = self._init_driver()

    def _init_driver(self):
        """Initializes the Selenium WebDriver."""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except Exception as e:
            logging.error(f"Failed to initialize WebDriver: {e}")
            raise

    def get_data(self, soup):
        """Extracts data from a single product listing."""
        try:
            atag = soup.h2.a
            name = atag.text.strip()
            url = self.base_url + atag.get("href")
        except AttributeError:
            return None

        try:
            price = soup.find('span', 'a-offscreen').text
        except AttributeError:
            price = "N/A"

        try:
            rating = soup.i.text
            num_reviews = soup.find('span', {'class': 'a-size-base', 'dir': 'auto'}).text
        except AttributeError:
            rating = "N/A"
            num_reviews = "N/A"

        return {
            "Product Name": name,
            "Product URL": url,
            "Product Price": price,
            "Rating": rating,
            "Number of reviews": num_reviews,
        }

    def scrape(self):
        """Main scraping logic."""
        url = f"{self.base_url}/s?k={self.search_term}"
        
        for page in range(1, self.max_pages + 1):
            logging.info(f"Scraping page {page}: {url}")
            try:
                self.driver.get(url)
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                results = soup.find_all('div', {'data-component-type': 's-search-result'})

                if not results:
                    logging.warning("No results found on this page.")
                    break

                for item in results:
                    product_data = self.get_data(item)
                    if product_data:
                        self.scraped_data.append(product_data)

                # Find next page URL
                next_button = soup.find('a', {'aria-label': 'Go to next page, page 2'})
                if next_button:
                    url = self.base_url + next_button.get('href')
                    sleep(1)  # Be respectful to the server
                else:
                    logging.info("No more pages to scrape.")
                    break
            except Exception as e:
                logging.error(f"An error occurred while scraping {url}: {e}")
                break
        
        self.close()
        return self.scraped_data

    def write_to_csv(self, filename: str = "Scraped_Data.csv"):
        """Writes the scraped data to a CSV file."""
        if not self.scraped_data:
            logging.warning("No data to write to CSV.")
            return

        field_names = ["Product URL", "Product Name", "Product Price", "Rating", "Number of reviews"]
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=field_names)
                writer.writeheader()
                writer.writerows(self.scraped_data)
            logging.info(f"Data successfully written to {filename}")
        except IOError as e:
            logging.error(f"Failed to write to CSV file {filename}: {e}")

    def close(self):
        """Closes the WebDriver."""
        if self.driver:
            self.driver.quit()
            logging.info("WebDriver closed.")

def main():
    """Main function to run the scraper."""
    search_term = "bags"
    scraper = AmazonScraper(search_term=search_term, max_pages=5)
    scraped_data = scraper.scrape()
    if scraped_data:
        scraper.write_to_csv(f"{search_term}_data.csv")

if __name__ == "__main__":
    main()