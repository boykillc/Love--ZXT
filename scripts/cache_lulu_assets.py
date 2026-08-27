from pathlib import Path
import sys
import requests

ASSET_DIR = Path("assets")
ASSET_DIR.mkdir(parents=True, exist_ok=True)

ASSETS = {
    "lulu-bg.jpg": [
        "https://file.moyubuluo.com/d/file/2026-08-03/c4752d917f116ad51a01709cade9ba16.jpg",
        "https://k.sinaimg.cn/n/sinakd/sni/345/w1191h2354/20251123/c175-006c0144a272b781d51c91522476de1f.jpg/w700d1q75cms.jpg",
    ],
    "lulu-1.gif": [
        "https://n.sinaimg.cn/sinakd20120/100/w450h450/20250323/a16a-gif966aab91a2221556decd1e2fc4932b6c.gif",
    ],
    "lulu-2.gif": [
        "https://k.sinaimg.cn/n/sinakd20114/116/w458h458/20251004/87e5-gif545e17880baacd2d2e5bc4fb46beafd9.gif",
    ],
    "lulu-3.gif": [
        "https://k.sinaimg.cn/n/sinakd20114/0/w400h400/20251004/b4e5-gife38550bb43adbfdae7ac788e74ed1038.gif",
    ],
    "lulu-4.gif": [
        "https://k.sinaimg.cn/n/sinakd20114/0/w400h400/20251004/86d2-gif76f89a900dc2812de7d5b459b2bac8e1.gif",
    ],
    "lulu-5.gif": [
        "https://k.sinaimg.cn/n/sinakd20114/100/w450h450/20251004/ca2d-gif52a1cdfbd5eef975e29dc63590074c0c.gif",
    ],
    "lulu-6.gif": [
        "https://k.sinaimg.cn/n/sinakd20114/480/w640h640/20251004/6517-gife204c1f6c83ae1953e79ef23f71e5ae5.gif",
    ],
    "lulu-7.gif": [
        "https://k.sinaimg.cn/n/sinakd20114/480/w640h640/20251004/99a9-giff8d4219580115ee99904581ba89a649b.gif",
    ],
    "lulu-8.gif": [
        "https://k.sinaimg.cn/n/sinakd20114/100/w450h450/20251004/407d-giff8d08f52c6c7243c224b7da0deefdd46.gif",
    ],
    "lulu-9.gif": [
        "https://k.sinaimg.cn/n/sinakd20108/0/w400h400/20251020/303e-gif5b8d73c297b4edfb7a54a83a2901c9e8.gif",
    ],
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36",
    "Referer": "https://www.sina.com.cn/",
}


def valid(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 1000:
        return False
    data = path.read_bytes()[:10]
    if path.suffix.lower() == ".gif":
        return data.startswith(b"GIF87a") or data.startswith(b"GIF89a")
    return data.startswith(b"\xff\xd8\xff") or data.startswith(b"\x89PNG")


def download_one(name: str, urls: list[str]) -> bool:
    target = ASSET_DIR / name
    if valid(target):
        print(f"已有本地素材：{target}")
        return True

    for url in urls:
        try:
            print(f"下载 {name}: {url}")
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            content = response.content
            target.write_bytes(content)
            if valid(target):
                print(f"下载成功：{target} ({len(content)} bytes)")
                return True
            target.unlink(missing_ok=True)
        except Exception as exc:
            print(f"下载失败 {name}: {exc}")
            target.unlink(missing_ok=True)

    return False


failed = [name for name, urls in ASSETS.items() if not download_one(name, urls)]
if failed:
    print("以下噜噜素材未能缓存：", ", ".join(failed))
    sys.exit(1)

print("全部噜噜素材已经缓存到 assets/。")
