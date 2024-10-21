import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
import re
import sys
from concurrent.futures import ThreadPoolExecutor

# Function to fetch the HTML content of a webpage
def fetch_page_content(url, headers=None):
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.text
    except requests.RequestException as e:
        # Log error instead of silencing
        print(f"Error fetching {url}: {e}")
    return None

def extract_parameters(html_content, base_url):
    parameters = set()
    soup = BeautifulSoup(html_content, "html.parser")

    # Find form-related input tags and other types of input fields
    form_tags = soup.find_all(["input", "textarea", "select", "form"])
    for tag in form_tags:
        param_name = tag.get("name")
        if param_name:
            parameters.add(param_name)

    # Include hidden input fields
    hidden_fields = soup.find_all("input", type="hidden")
    for hidden in hidden_fields:
        param_name = hidden.get("name")
        if param_name:
            parameters.add(param_name)

    # Extract parameters from query strings in anchor tags
    for link in soup.find_all("a", href=True):
        parsed_url = urlparse(link["href"])
        query_params = parse_qs(parsed_url.query)
        for param_name in query_params:
            parameters.add(param_name)

    # Look for parameters in script tags or inline event handlers
    for script in soup.find_all("script"):
        # Basic regex to find parameter-like patterns in script content
        matches = re.findall(r'[?&](\w+)=', script.text)
        parameters.update(matches)

    # Return found parameters
    return parameters

# Function to read target URLs from a file
def read_target_urls(file_path):
    with open(file_path, "r") as file:
        urls = file.read().splitlines()
    return ["https://" + url if not url.startswith("https://") else url for url in urls]

# Function to process a single URL
def process_url(target_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Referer": target_url
    }

    # Fetch content
    html_content = fetch_page_content(target_url, headers)
    if not html_content:
        return set()

    # Extract parameters
    parameters = extract_parameters(html_content, target_url)
    return parameters

# Main execution flow
def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <target_urls_file_path>")
        sys.exit(1)

    # Read URLs from file
    target_urls_file = sys.argv[1]
    target_urls = read_target_urls(target_urls_file)

    # Use ThreadPoolExecutor for parallel processing of URLs
    all_parameters = set()
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(process_url, target_urls))

    # Collect all parameters
    for params in results:
        all_parameters.update(params)

    # Output the collected parameters
    for param in all_parameters:
        print(param)

if __name__ == "__main__":
    main()
