import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests
from DrissionPage import WebPage, ChromiumOptions

# ================= 路径配置 =================
# 最终文件保存路径
#例子：SAVE_PATH = r"D:\GitHub_Desktop_Final"
SAVE_PATH =""
# 临时碎片存放路径
#例子：TEMP_DIR = r"D:\GitHub_Desktop_Temp"
TEMP_DIR =""
# 并发线程数，不够可以改，但是下面也要记得改
MAX_THREADS = 16


# ===========================================

def parasitic_download(url, start, end, chunk_id, headers):
    """
    分块并发下载逻辑。
    """
    chunk_path = os.path.join(TEMP_DIR, f"chunk_{chunk_id}.tmp")
    while True:
        downloaded = os.path.getsize(chunk_path) if os.path.exists(chunk_path) else 0
        current_start = start + downloaded

        if current_start > end:
            return

        req_headers = headers.copy()
        req_headers['Range'] = f'bytes={current_start}-{end}'

        try:
            # 大文件下载建议将 timeout 拉长，对抗跨国网络波动
            res = requests.get(url, headers=req_headers, impersonate="chrome110", stream=True, timeout=30)
            if res.status_code not in (200, 206):
                time.sleep(2)
                continue

            with open(chunk_path, "ab") as f:
                for chunk in res.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
            break
        except Exception:
            time.sleep(2)


def main():
    # 目录初始化
    if not os.path.exists(SAVE_PATH): os.makedirs(SAVE_PATH)
    if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR)

    co = ChromiumOptions().set_local_port(9222)
    #路径有不同的需求可以改，一般edge默认是这里
    co.set_browser_path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

    try:
        page = WebPage(chromium_options=co)
    except Exception as e:
        print(f"❌ 浏览器接管失败: {e}")
        return

    # 关键点：GitHub Desktop 的下载请求特征是 central.github.com
    #page.listen.start(['central.github.com', 'desktop.exe']),
    #这一段负责抓地址，点击你的下载页面，然后先f12抓包，到网络，然后cthl+l清空，点击你要下载的，看302，不知道的可以交给al看
    page.listen.start([])


    #print("🌐 正在跳转至靶场: https://desktop.github.com/")
    #page.get("https://desktop.github.com/")
    print("填网址")
    page.get("填网址")
    print("\n" + "=" * 50)
    print("👉 请手动点击页面上的 'Download for Windows' 按钮")
    print("=" * 50)

    # 等待拦截数据包
    packet = page.listen.wait(timeout=300)
    if not packet:
        print("❌ 5分钟内未检测到下载请求。")
        page.listen.stop()
        return

    page.listen.stop()
    raw_url = packet.request.url
    print(f"\n🎯 成功劫持下载血管: {raw_url}")

    # 获取浏览器请求头进行伪装，这个想改可以改
    browser_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://desktop.github.com/"
    }

    # 探测文件真实大小及最终重定向地址
    print("[*] 正在探测文件实体...")
    try:
        # GitHub 下载必须允许重定向 (allow_redirects=True)
        res = requests.get(
            raw_url,
            headers=browser_headers,
            impersonate="chrome110",
            stream=True,
            allow_redirects=True,
            timeout=20
        )
        total_size = int(res.headers.get('Content-Length', 0))
        real_url = res.url
        res.close()
    except Exception as e:
        print(f"❌ 探测失败: {e}")
        return

    if total_size <= 0:
        print("❌ 无法获取文件体积，检查网络环境。")
        return

    print(f"✅ 捕获成功！文件体积: {total_size / (1024 * 1024):.2f} MB")
    print(f"✅ 最终血管地址: {real_url[:60]}...")

    # 计算分块
    chunk_size = total_size // MAX_THREADS
    futures = []

    print(f"\n🚀 启动 {MAX_THREADS} 条血蛭，开始从 D 盘阵地发起进攻...")
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        for i in range(MAX_THREADS):
            start = i * chunk_size
            end = total_size - 1 if i == MAX_THREADS - 1 else (i + 1) * chunk_size - 1
            futures.append(executor.submit(parasitic_download, real_url, start, end, i, browser_headers))

        for future in as_completed(futures):
            future.result()

            # 合并文件
    final_file_name = "GitHubDesktopSetup-x64.exe"
    final_path = os.path.join(SAVE_PATH, final_file_name)

    print(f"\n[*] 正在将 16 个碎片合并至: {final_path}")
    with open(final_path, "wb") as f_out:
        for i in range(MAX_THREADS):
            chunk_path = os.path.join(TEMP_DIR, f"chunk_{i}.tmp")
            if os.path.exists(chunk_path):
                with open(chunk_path, "rb") as f_in:
                    f_out.write(f_in.read())
                os.remove(chunk_path)

    print(f"✅ 任务完成。退出代码 0。")


if __name__ == "__main__":
    main()
