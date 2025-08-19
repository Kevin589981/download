#!/usr/bin/env python3
"""
并行下载 zip_links.txt 中的所有 ZIP 链接
"""
import os
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from tqdm import tqdm

LINKS_FILE = "zip_links.txt"
DOWNLOAD_DIR = Path("downloads")
WORKERS = min(32, (os.cpu_count() or 1) * 5)  # GitHub-hosted runner 通常是 2 vCPU
CHUNK = 8192
TIMEOUT = 30
RETRY = 3

session = requests.Session()
session.headers.update({"User-Agent": "github-actions/zip-downloader"})

def read_links(path: str):
    if not Path(path).is_file():
        print(f"❌ {path} 不存在")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                yield line

def _fetch(url: str, dest: Path):
    """真正下载的函数，支持重试"""
    for attempt in range(1, RETRY + 1):
        try:
            with session.get(url, stream=True, timeout=TIMEOUT) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                fname = Path(url).name or "download.zip"
                target = dest / fname
                target.parent.mkdir(parents=True, exist_ok=True)

                with open(target, "wb") as f, tqdm(
                    total=total,
                    unit="B",
                    unit_scale=True,
                    desc=f"{fname} ({attempt})",
                    leave=False,
                ) as bar:
                    for chunk in r.iter_content(chunk_size=CHUNK):
                        if chunk:
                            f.write(chunk)
                            bar.update(len(chunk))
                return url, True
        except Exception as e:
            if attempt == RETRY:
                return url, False
            time.sleep(2 ** attempt)

def main():
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    links = list(read_links(LINKS_FILE))
    if not links:
        print("⚠️ 未发现有效链接")
        return

    print(f"📦 启动 {WORKERS} 线程并行下载 {len(links)} 个文件")
    ok = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        future_to_url = {pool.submit(_fetch, url, DOWNLOAD_DIR): url for url in links}
        for fut in tqdm(as_completed(future_to_url), total=len(links), desc="总进度"):
            url, success = fut.result()
            if success:
                ok += 1
            else:
                print(f"⚠️ 多次重试后仍失败: {url}")
    print(f"✅ 完成，成功 {ok}/{len(links)}")

if __name__ == "__main__":
    main()