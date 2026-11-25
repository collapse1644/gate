import os, urllib.request
url="https://github.com/ggml-org/llama.cpp/releases/download/b12144/cudart-llama-bin-win-cuda-13.4-x64.zip"
out=r"G:\MINI-PROJ\gate\backend\data\llama.cpp\cudart.zip"
existing=os.path.getsize(out) if os.path.exists(out) else 0
print("existing", existing)
req=urllib.request.Request(url)
req.add_header("Range", f"bytes={existing}-")
with urllib.request.urlopen(req, timeout=300) as r, open(out,"ab") as f:
    total=existing
    while True:
        chunk=r.read(1024*1024)
        if not chunk:
            break
        f.write(chunk)
        total+=len(chunk)
        print("downloaded", total, flush=True)
print("done")