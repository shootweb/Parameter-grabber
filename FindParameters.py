# FindParameters_with_headers.py
# Updated version of your script that accepts custom headers via CLI
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urljoin
import re
import sys
from concurrent.futures import ThreadPoolExecutor
import logging
import argparse
import json
from typing import Dict, Optional

# Set up logging for detailed tracking
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def parse_headers_string(headers_str: str) -> Dict[str, str]:
    """
    Parse a headers string of the form:
    "Header1: value1; Header2: value2" into a dict.
    Semicolon separates headers. Colons separate name and value.
    """
    headers = {}
    if not headers_str:
        return headers
    parts = [p.strip() for p in headers_str.split(";") if p.strip()]
    for part in parts:
        if ":" in part:
            name, value = part.split(":", 1)
            headers[name.strip()] = value.strip()
        else:
            logging.warning(f"Ignoring malformed header part: {part}")
    return headers

# Function to fetch the HTML content of a webpage
def fetch_page_content(url: str, headers: Optional[Dict[str, str]] = None) -> Optional[str]:
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.text
        else:
            logging.info(f"Non 200 status for {url}: {response.status_code}")
    except requests.RequestException as e:
        logging.error(f"Error fetching {url}: {e}")
    return None

def extract_parameters(html_content: str, base_url: str, session: requests.Session):
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

def extract_js_parameters(js_content: str):
    """Extract parameter-like patterns from JavaScript content."""
    parameters = set()
    # Regex patterns to find parameters in JS code
    url_pattern = re.compile(r'[?&]([a-zA-Z0-9_]+)=')
    function_call_pattern = re.compile(r'([a-zA-Z0-9_]+)\s*\(')

    parameters.update(url_pattern.findall(js_content))
    parameters.update(function_call_pattern.findall(js_content))

    return parameters

# Function to filter out array-like parameters
def is_valid_parameter(param_name: str):
    return not re.match(r'.*\[.*\]', param_name)

# Function to read target URLs from a file
def read_target_urls(file_path: str):
    with open(file_path, "r", encoding="utf-8") as file:
        urls = file.read().splitlines()
    # preserve existing logic adding https if not present
    return ["https://" + url if not url.startswith("https://") else url for url in urls]

# Function to process a single URL
def process_url(target_url: str, extra_headers: Dict[str, str]):
    # Default headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Referer": target_url
    }

    # Merge user supplied headers, user supplied take precedence
    headers.update(extra_headers or {})

    with requests.Session() as session:
        session.headers.update(headers)

        # Fetch main page content using session headers
        html_content = fetch_page_content(target_url, session.headers)
        if not html_content:
            return {}

        parameters = extract_parameters(html_content, target_url, session)
        filtered_parameters = {param: f"{target_url}?{param}=" for param in parameters if is_valid_parameter(param)}

    return filtered_parameters

# Function to filter parameters so each is unique per domain
def filter_unique_per_domain(all_parameters):
    domain_parameter_map = {}

    for param, url in all_parameters.items():
        domain = urlparse(url).netloc
        if domain not in domain_parameter_map:
            domain_parameter_map[domain] = {}
        if param not in domain_parameter_map[domain]:
            domain_parameter_map[domain][param] = url

    unique_urls = {param: url for domain_params in domain_parameter_map.values() for param, url in domain_params.items()}
    return unique_urls

def main():
    parser = argparse.ArgumentParser(description="Find parameter names on list of target urls")
    parser.add_argument("target_urls_file", help="file with target urls, one per line")
    parser.add_argument("output_file", help="output file to write parameter urls")
    parser.add_argument("--headers", help='single string of headers like "Cookie: a=b; Another: value"', default=None)
    parser.add_argument("--headers-file", help="json file with headers e.g {\"Cookie\": \"a=b\", \"X-Forwarded-For\": \"1.2.3.4\"}", default=None)
    parser.add_argument("--workers", type=int, default=10, help="max parallel workers")
    args = parser.parse_args()

    # load headers from json file if provided
    extra_headers = {}
    if args.headers_file:
        try:
            with open(args.headers_file, "r", encoding="utf-8") as hf:
                extra_headers = json.load(hf)
                if not isinstance(extra_headers, dict):
                    logging.error("headers file must contain a JSON object")
                    sys.exit(1)
        except Exception as e:
            logging.error(f"Could not read headers file: {e}")
            sys.exit(1)
    elif args.headers:
        extra_headers = parse_headers_string(args.headers)

    target_urls = read_target_urls(args.target_urls_file)

    all_parameters = {}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # map needs function with single arg so we use lambda to include headers
        results = list(executor.map(lambda u: process_url(u, extra_headers), target_urls))

    for result in results:
        all_parameters.update(result)

    unique_parameters = filter_unique_per_domain(all_parameters)

    with open(args.output_file, "w", encoding="utf-8") as output_file:
        for param, url in unique_parameters.items():
            output_file.write(f"{url}\n")

    print(f"Filtered parameters and their urls have been written to {args.output_file}")

if __name__ == "__main__":
    main()
