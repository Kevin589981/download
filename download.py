#!/usr/bin/env python3
"""
从 zip_links.txt 中逐行读取 ZIP 链接并下载到 downloads/ 目录。
要求：
  - 每行一个 URL，允许空行/注释行（# 开头）
  - 支持 HTTP/HTTPS 重定向
  - 如果下载失败会打印错误并继续
"""
import os
import sys
import time
from pathlib import Path
import requests
from tqdm import tqdm

LINKS_FILE = "zip_links.txt"
DOWNLOAD_DIR = Path("downloads")
CHUNK_SIZE = 8192
TIMEOUT = 30  # 秒

def read_links(path: str):
    """读取并过滤出合法的链接"""
    if not os.path.isfile(path):
        print(f"❌ 文件 {path} 不存在")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            yield line

def download_file(url: str, dest: Path):
    """流式下载到本地"""
    session = requests.Session()
    session.headers.update({"User-Agent": "github-actions/zip-downloader"})
    try:
        with session.get(url, stream=True, timeout=TIMEOUT) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            fname = Path(url).name or "download.zip"
            target = dest / fname
            target.parent.mkdir(parents=True, exist_ok=True)

            with tqdm(total=total, unit="B", unit_scale=True, desc=fname) as bar:
                with open(target, "wb") as f:
                    for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            bar.update(len(chunk))
            return target
    except Exception as e:
        print(f"⚠️ 下载失败 {url} : {e}")
        return None

def main():
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    links = list(read_links(LINKS_FILE))
    if not links:
        print("⚠️ 未发现有效链接")
        return

    print(f"📦 准备下载 {len(links)} 个 ZIP 文件 …")
    success = 0
    for url in links:
        if download_file(url, DOWNLOAD_DIR):
            success += 1
        time.sleep(0.5)  # 轻量限速，避免过快
    print(f"✅ 完成，共成功 {success}/{len(links)} 个")

if __name__ == "__main__":
    main()