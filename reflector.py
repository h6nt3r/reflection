#!/usr/bin/env python3
import requests
import threading
import argparse
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
import time
import sys
import charset_normalizer

# Set the timeout limit (in seconds)
TIMEOUT = 10

# Global variables to track progress and save URLs only once
total_urls = 0
processed_urls = 0
saved_urls = set()  # Set to track saved URLs

# ANSI escape sequences for color
BOLD = '\033[1m'
RED = '\033[91m'
BOLD_RED = '\033[1;91m'  # Bold red
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
WHITE = '\033[97m'
RESET = '\033[0m'

def print_banner():
    banner = f"""
    {GREEN}#        {BOLD}{CYAN}XSS Reflection Checker{RESET}{GREEN}        #{RESET}
    {GREEN}#        {BOLD}{CYAN}Developed by Mijan{RESET}{GREEN}             #{RESET}
    """
    print(banner)

def check_reflection(url, output_file, placeholder):
    global processed_urls

    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        base_url = parsed_url._replace(query="").geturl()

        found_reflection = False

        for param in query_params:
            modified_params = query_params.copy()
            modified_params[param] = [placeholder]

            modified_url = urlunparse(parsed_url._replace(query=urlencode(modified_params, doseq=True)))

            # Make a request with a timeout
            response = requests.get(modified_url, timeout=TIMEOUT)

            if placeholder in response.text:
                found_reflection = True
                # Highlight reflected parameter in bold red
                print(f"{GREEN}[+] Reflection found on {modified_url} for parameter '{BOLD_RED}{param}{RESET}'")

                # Save the URL with placeholder keyword in the output file
                with open(output_file, 'a') as f:
                    f.write(f"{modified_url}\n")

        if found_reflection and base_url not in saved_urls:
            saved_urls.add(base_url)  # Add the base URL to the set to prevent duplicates

    except requests.exceptions.Timeout:
        print(f"{RED}[!] Timeout: The request to {url} took longer than {TIMEOUT} seconds. Moving to the next URL in 5 seconds.{RESET}")
        time.sleep(5)  # Wait before continuing to the next URL
    except requests.exceptions.RequestException as e:
        print(f"{RED}[!] Error scanning {url}: {str(e)}. Moving to the next URL in 5 seconds.{RESET}")
        time.sleep(5)  # Wait before continuing to the next URL
    finally:
        processed_urls += 1
        print(f"{BLUE}[INFO] Scanning progress: {processed_urls}/{total_urls} URLs processed.{RESET}")

def main():
    global total_urls

    print_banner()

    parser = argparse.ArgumentParser(description="Reflection Checker")
    parser.add_argument("-f", "--file", type=str, help="Path to the text file containing URLs")
    parser.add_argument("-u", "--url", type=str, help="Single URL to scan")
    parser.add_argument("--threads", type=int, default=5, help="Number of threads to use (default: 5)")
    parser.add_argument("-o", "--output", type=str, default="xss.txt", help="Output file for saving results (default: xss.txt)")
    parser.add_argument("-p", "--placeholder", type=str, default="RXSS", help="Placeholder text to use for reflection testing (default: RXSS)")

    args = parser.parse_args()

    urls = []

    if args.file:
        try:
            with open(args.file, 'rb') as f:
                detected = charset_normalizer.detect(f.read())
            encoding = detected['encoding'] or 'utf-8'

            with open(args.file, 'r', encoding=encoding) as f:
                urls = [line.strip() for line in f if line.strip()]
            total_urls = len(urls)
        except Exception as e:
            print(f"{RED}Error reading file: {str(e)}{RESET}")
            return

    elif args.url:
        urls.append(args.url.strip())
        total_urls = 1

    else:  # If no command-line argument is provided, read from stdin
        try:
            for line in sys.stdin:
                url = line.strip()
                if url:
                    urls.append(url)
            total_urls = len(urls)
        except KeyboardInterrupt:
            print("\n" + RED + "Scanning interrupted." + RESET)
            return

    if not urls:
        print(f"{RED}Error: No URLs provided. Please provide URLs via -f/--file, -u/--url, or through stdin.{RESET}")
        return

    # Set the output file
    output_file = args.output

    # Clear previous results in the output file
    open(output_file, 'w').close()

    threads = []
    for url in urls:
        while threading.active_count() - 1 >= args.threads:
            pass  # Wait for available thread slot

        thread = threading.Thread(target=check_reflection, args=(url, output_file, args.placeholder))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()