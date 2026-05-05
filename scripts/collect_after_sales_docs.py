# coding=utf-8
"""
批量抓取公开售后网页，转为 Markdown 并保存图片。

设计目标：
1. 保留可读的 Markdown，便于后续导入知识库、切分和让 AI 读取
2. 同时保留原始 HTML 快照，避免只剩“处理后文本”而丢失原始结构
3. 目录按 品牌 / 类型 组织，方便后续扩充
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag
from html2text import HTML2Text


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_OUTPUT_ROOT = Path("mock_data/knowledge/after_sales_public_docs")

# 常见正文容器，优先尝试这些节点
CONTENT_SELECTORS = [
    "article",
    "main",
    "[role='main']",
    ".article",
    ".article-content",
    ".article-body",
    ".post-content",
    ".entry-content",
    ".content",
    ".main-content",
    ".doc-content",
    ".markdown-body",
    ".support-content",
    ".solution-content",
    "#content",
    "#main",
    "#article",
]

# 这些节点大概率是导航、页脚、浮层，正文内也尽量去掉
DROP_SELECTORS = [
    "script",
    "style",
    "noscript",
    "header",
    "footer",
    "nav",
    "aside",
    "form",
    "button",
    "iframe",
    "svg",
    "canvas",
    ".breadcrumb",
    ".breadcrumbs",
    ".nav",
    ".navbar",
    ".footer",
    ".header",
    ".share",
    ".social",
    ".sidebar",
    ".recommend",
    ".related",
    ".advertisement",
    ".ads",
    ".cookie",
    ".modal",
    ".popup",
]


@dataclass
class FetchItem:
    url: str
    brand: str
    category: str
    slug: str | None = None
    title: str | None = None
    selector: str | None = None
    save_html: bool = True


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "doc"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_items(config_path: Path) -> list[FetchItem]:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("配置文件必须是 JSON 数组")

    items: list[FetchItem] = []
    for row in data:
        if not isinstance(row, dict):
            raise ValueError("配置文件中的每一项都必须是对象")
        items.append(
            FetchItem(
                url=row["url"],
                brand=row["brand"],
                category=row["category"],
                slug=row.get("slug"),
                title=row.get("title"),
                selector=row.get("selector"),
                save_html=row.get("save_html", True),
            )
        )
    return items


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def get_link_density(node: Tag) -> float:
    full_text = node.get_text(" ", strip=True)
    if not full_text:
        return 1.0
    link_text = " ".join(link.get_text(" ", strip=True) for link in node.find_all("a"))
    return len(link_text) / max(len(full_text), 1)


def score_content_node(node: Tag) -> float:
    text = node.get_text(" ", strip=True)
    if len(text) < 80:
        return -1

    heading_count = len(node.find_all(re.compile(r"^h[1-6]$")))
    paragraph_count = len(node.find_all(["p", "li"]))
    image_count = len(node.find_all("img"))
    link_density = get_link_density(node)

    score = len(text)
    score += heading_count * 120
    score += paragraph_count * 30
    score += image_count * 20
    score -= int(link_density * 1200)
    return score


def select_content_root(soup: BeautifulSoup, selector: str | None) -> Tag:
    if selector:
        node = soup.select_one(selector)
        if isinstance(node, Tag):
            return node

    candidates: list[Tag] = []
    for candidate in CONTENT_SELECTORS:
        candidates.extend([node for node in soup.select(candidate) if isinstance(node, Tag)])

    if candidates:
        candidates = sorted(candidates, key=score_content_node, reverse=True)
        best = candidates[0]
        if score_content_node(best) > 100:
            return best

    body = soup.body
    if isinstance(body, Tag):
        return body
    return soup


def clean_content(root: Tag) -> Tag:
    root = BeautifulSoup(str(root), "html.parser")

    for selector in DROP_SELECTORS:
        for node in root.select(selector):
            node.decompose()

    for node in list(root.find_all(["div", "section", "ul", "ol"])):
        text_len = len(node.get_text(" ", strip=True))
        link_density = get_link_density(node)
        if text_len < 400 and link_density > 0.55 and not node.find("img"):
            node.decompose()

    # 清掉过于空洞的标签，减少噪音
    for node in root.find_all():
        if node.name in {"div", "section", "span"} and not node.get_text(strip=True) and not node.find("img"):
            node.decompose()

    return root


def absolutize_links(root: Tag, page_url: str) -> None:
    for tag in root.find_all(href=True):
        href = tag.get("href")
        if href:
            tag["href"] = urljoin(page_url, href)
    for tag in root.find_all(src=True):
        src = tag.get("src")
        if src:
            tag["src"] = urljoin(page_url, src)


def guess_extension(url: str, content_type: str | None) -> str:
    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"}:
        return suffix
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if ext:
            return ext
    return ".bin"


def download_images(session: requests.Session, root: Tag, asset_dir: Path) -> int:
    ensure_dir(asset_dir)
    downloaded = 0

    for index, img in enumerate(root.find_all("img"), start=1):
        src = img.get("src")
        if not src or src.startswith("data:"):
            continue

        try:
            response = session.get(src, timeout=(10, 20))
            response.raise_for_status()
        except requests.RequestException:
            continue

        ext = guess_extension(src, response.headers.get("Content-Type"))
        file_name = f"image_{index:03d}{ext}"
        file_path = asset_dir / file_name
        file_path.write_bytes(response.content)
        img["src"] = file_name
        downloaded += 1

    return downloaded


def html_to_markdown(html: str) -> str:
    converter = HTML2Text()
    converter.body_width = 0
    converter.ignore_links = False
    converter.ignore_images = False
    converter.ignore_tables = False
    converter.single_line_break = False
    converter.protect_links = True
    markdown = converter.handle(html)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()
    return markdown


def extract_title(soup: BeautifulSoup, fallback: str | None = None) -> str:
    if fallback:
        return fallback.strip()

    meta = soup.find("meta", attrs={"property": "og:title"})
    if meta and meta.get("content"):
        return str(meta["content"]).strip()

    if soup.title and soup.title.string:
        return soup.title.string.strip()

    h1 = soup.find("h1")
    if h1:
        return h1.get_text(" ", strip=True)

    return "未命名文档"


def build_markdown(title: str, item: FetchItem, markdown_body: str) -> str:
    lines = [
        f"# {title}",
        "",
        f"- 来源: {item.url}",
        f"- 品牌: {item.brand}",
        f"- 类型: {item.category}",
        "",
        "## 正文",
        "",
        markdown_body,
        "",
    ]
    return "\n".join(lines)


def save_raw_html(target_path: Path, html: str) -> None:
    target_path.write_text(html, encoding="utf-8")


def fetch_one(session: requests.Session, item: FetchItem, output_root: Path) -> dict[str, Any]:
    response = session.get(item.url, timeout=(10, 20))
    response.raise_for_status()

    response.encoding = (
        response.encoding
        if response.encoding and response.encoding.upper() != "ISO-8859-1"
        else response.apparent_encoding
    )
    html = response.text
    soup = BeautifulSoup(html, "html.parser")

    title = extract_title(soup, item.title)
    slug = item.slug or slugify(title)
    doc_dir = output_root / item.brand / item.category / slug
    ensure_dir(doc_dir)

    content_root = select_content_root(soup, item.selector)
    content_root = clean_content(content_root)
    absolutize_links(content_root, item.url)

    assets_dir = doc_dir / "assets"
    image_count = download_images(session, content_root, assets_dir)
    markdown_body = html_to_markdown(str(content_root))

    markdown_path = doc_dir / f"{slug}.md"
    markdown_path.write_text(build_markdown(title, item, markdown_body), encoding="utf-8")

    if item.save_html:
        save_raw_html(doc_dir / f"{slug}.html", html)

    return {
        "title": title,
        "slug": slug,
        "path": str(markdown_path),
        "images": image_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="批量抓取公开售后网页并转为 Markdown")
    parser.add_argument(
        "--config",
        default="scripts/after_sales_doc_sources.example.json",
        help="URL 配置文件路径（JSON 数组）",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="输出目录，默认写入 mock_data/knowledge/after_sales_public_docs",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    output_root = Path(args.output_root)

    if not config_path.exists():
        raise FileNotFoundError(f"未找到配置文件: {config_path}")

    ensure_dir(output_root)
    items = load_items(config_path)
    session = build_session()

    summary: list[dict[str, Any]] = []
    for item in items:
        try:
            result = fetch_one(session, item, output_root)
            summary.append({"url": item.url, "status": "ok", **result})
            print(f"[OK] {item.url} -> {result['path']}", flush=True)
        except Exception as exc:  # noqa: BLE001
            summary.append({"url": item.url, "status": "error", "error": str(exc)})
            print(f"[ERROR] {item.url} -> {exc}", flush=True)

    summary_path = output_root / "_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"已写入汇总: {summary_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
