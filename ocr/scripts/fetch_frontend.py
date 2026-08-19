# 前端依赖下载（离线 vendor/ 方案）
# Vue 3 + Element Plus 现成类库，下载到 static/vendor/，浏览器离线可用
# 执行: python scripts/fetch_frontend.py

import urllib.request, os
from pathlib import Path

VENDOR = Path(__file__).resolve().parent.parent / "local" / "static" / "vendor"
VENDOR.mkdir(parents=True, exist_ok=True)

FILES = {
    # Vue 3 (global build)
    "https://unpkg.com/vue@3/dist/vue.global.prod.js": "vue.global.prod.js",
    # Element Plus (css + js + 图标库)
    "https://unpkg.com/element-plus@2/dist/index.css": "element-plus.css",
    "https://unpkg.com/element-plus@2/dist/index.full.min.js": "element-plus.min.js",
    "https://unpkg.com/@element-plus/icons-vue/dist/index.iife.min.js": "element-plus-icons.min.js",
}

for url, name in FILES.items():
    dest = VENDOR / name
    if dest.exists():
        print(f"已存在: {name}")
        continue
    print(f"下载 {name} ...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        dest.write_bytes(data)
        print(f"  ✅ {name} ({len(data)/1024:.0f}KB)")
    except Exception as e:
        print(f"  ❌ {name}: {e}")

print("\n完成。验证:")
for name in os.listdir(VENDOR):
    print(f"  {name}  {os.path.getsize(VENDOR/name)//1024}KB")