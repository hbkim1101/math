"""가장 최근의 CDP Page.captureScreenshot 응답(JSON)을 PNG 로 저장하고 JSON 은 지운다.
사용: save_latest_shot.py <out.png>"""
import base64
import json
import os
import sys
from pathlib import Path

logs = Path.home() / ".cursor" / "browser-logs"
files = sorted(logs.glob("cdp-response-Page.captureScreenshot-*.json"), key=os.path.getmtime)
if not files:
    raise SystemExit("no screenshot json")
src = files[-1]
data = json.load(open(src, encoding="utf-8"))
b64 = data["data"] if "data" in data else data["result"]["data"]
out = Path(sys.argv[1])
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(base64.b64decode(b64))
for f in files:
    f.unlink()
from PIL import Image  # noqa: E402
print(out, Image.open(out).size)
