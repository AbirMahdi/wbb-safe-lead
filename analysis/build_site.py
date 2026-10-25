"""Embed site.json into the page; write preview (artifact) and standalone index.html (GitHub Pages)."""
import os
page = open("web/page.html").read()
data = open("web/data/site.json").read().replace("</", "<\\/")
page = page.replace("__DATA__", data)
os.makedirs("site", exist_ok=True)
open("site/preview.html", "w").write(page)
head, body = page.split("<!--/head-->", 1)
full = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        + head + '\n</head>\n<body>\n' + body + '\n</body>\n</html>\n')
open("site/index.html", "w").write(full)
print("index.html", len(full), "bytes")
