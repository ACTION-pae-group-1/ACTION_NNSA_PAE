import re
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "llms.txt"

text = SOURCE.read_text(encoding="utf-8")
urls = list(
    dict.fromkeys(
        url
        for url in re.findall(r"\]\((https?://[^)]+\.md(?:\?[^)]*)?)\)", text)
        if urlparse(url).path.endswith(".md")
        and not re.match(r"^/v\d+/", urlparse(url).path)
    )
)


def download(url):
    parsed = urlparse(url)
    path = Path(unquote(parsed.path).lstrip("/"))
    if ".." in path.parts:
        return f"SKIP {url}: unsafe path"

    destination = ROOT / path
    try:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(
            request, timeout=30, context=ssl._create_unverified_context()
        ) as response:
            content = response.read()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return f"OK   {path}"
    except Exception as exc:
        return f"FAIL {url}: {exc}"


print(f"Downloading {len(urls)} Markdown files into {ROOT}")

with ThreadPoolExecutor(max_workers=10) as pool:
    for result in as_completed([pool.submit(download, url) for url in urls]):
        print(result.result())
