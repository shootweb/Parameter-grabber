import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urljoin
import re
import sys
from concurrent.futures import ThreadPoolExecutor
import logging

# Set up logging for detailed tracking
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Function to fetch the HTML content of a webpage
def fetch_page_content(url, headers=None):
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.text
    except requests.RequestException as e:
        logging.error(f"Error fetching {url}: {e}")
    return None

def extract_parameters(html_content, base_url, session):
    parameters = set()
    soup = BeautifulSoup(html_content, "html.parser")

    # Find parameters from input tags and form fields
    form_tags = soup.find_all(["input", "textarea", "select", "form"])
    for tag in form_tags:
        param_name = tag.get("name")
        if param_name:
            parameters.add(param_name)

    # Include hidden input fields parameters
    hidden_fields = soup.find_all("input", type="hidden")
    for hidden in hidden_fields:
        param_name = hidden.get("name")
        if param_name:
            parameters.add(param_name)

    # Extract parameters from anchor tags (links)
    for link in soup.find_all("a", href=True):
        parsed_url = urlparse(link["href"])
        query_params = parse_qs(parsed_url.query)
        for param_name in query_params:
            parameters.add(param_name)

    # Look for parameters in inline and external JavaScript files
    script_tags = soup.find_all("script")
    for script in script_tags:
        if script.get("src"):  # External JavaScript file
            js_url = urljoin(base_url, script["src"])
            js_content = fetch_page_content(js_url, headers=session.headers)
            if js_content:
                parameters.update(extract_js_parameters(js_content))
        else:
            # Inline JavaScript
            parameters.update(extract_js_parameters(script.text))

    return parameters

def extract_js_parameters(js_content):
    """Extract parameter-like patterns from JavaScript content."""
    parameters = set()
    # Regex patterns to find parameters in JS code
    url_pattern = re.compile(r'[?&]([a-zA-Z0-9_]+)=')  # URL-like parameters
    function_call_pattern = re.compile(r'([a-zA-Z0-9_]+)\s*\(')  # Function parameters

    parameters.update(url_pattern.findall(js_content))
    parameters.update(function_call_pattern.findall(js_content))

    return parameters

# Function to filter out array-like parameters
def is_valid_parameter(param_name):
    # Exclude parameters with array-like notation such as parameter[] or parameter[key]
    return not re.match(r'.*\[.*\]', param_name)

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

    with requests.Session() as session:
        session.headers.update(headers)
        
        # Fetch main page content
        html_content = fetch_page_content(target_url, session.headers)
        if not html_content:
            return {}

        # Extract parameters from HTML and JavaScript content
        parameters = extract_parameters(html_content, target_url, session)
        # Filter out invalid parameters
        filtered_parameters = {param: f"{target_url}?{param}=" for param in parameters if is_valid_parameter(param)}

    return filtered_parameters

# Function to filter parameters so each is unique per domain
def filter_unique_per_domain(all_parameters):
    domain_parameter_map = {}

    for param, url in all_parameters.items():
        domain = urlparse(url).netloc
        if domain not in domain_parameter_map:
            domain_parameter_map[domain] = {}
        # Only add the parameter if it hasn't been added for this domain
        if param not in domain_parameter_map[domain]:
            domain_parameter_map[domain][param] = url

    # Flatten the dictionary back into a single dictionary of unique URLs
    unique_urls = {param: url for domain_params in domain_parameter_map.values() for param, url in domain_params.items()}
    return unique_urls

# Main execution flow
def main():
    if len(sys.argv) != 3:
        print("Usage: python script.py <target_urls_file_path> <output_file_path>")
        sys.exit(1)

    # Read URLs from file
    target_urls_file = sys.argv[1]
    output_file_path = sys.argv[2]
    target_urls = read_target_urls(target_urls_file)

    # Use ThreadPoolExecutor for parallel processing of URLs
    all_parameters = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(process_url, target_urls))

    # Collect all parameters with their respective URLs
    for result in results:
        all_parameters.update(result)

    # Filter parameters to ensure uniqueness within each domain
    unique_parameters = filter_unique_per_domain(all_parameters)

    # Write the results to the output file
    with open(output_file_path, "w") as output_file:
        for param, url in unique_parameters.items():
            output_file.write(f"{url}\n")

    print(f"Filtered parameters and their URLs have been written to {output_file_path}")

if __name__ == "__main__":
    main()
