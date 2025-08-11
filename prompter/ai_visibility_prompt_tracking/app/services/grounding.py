from __future__ import annotations
from dataclasses import dataclass
from typing import List

@dataclass
class RetrievedDoc:
    url: str
    title: str | None
    snippet: str
    publish_date: str | None
    fetch_time: str | None
    snippet_hash: str

def retrieve_web(query: str, country_code: str, max_docs: int = 8, policy: dict | None = None, proxy_endpoint: str | None = None) -> List[RetrievedDoc]:
    # TODO: Plug your web search/fetch with proxy here; return RetrievedDoc list
    return []

def build_context(docs: List[RetrievedDoc], char_budget: int = 8000) -> tuple[str, list[dict]]:
    lines, cits, total = [], [], 0
    for i, d in enumerate(docs, start=1):
        header = f"[{i}] {d.title or d.url}"
        body = d.snippet.strip().replace("\n"," ")
        block = f"{header}\n{body}\n"
        if total + len(block) > char_budget:
            break
        lines.append(block); total += len(block)
        cits.append({"url": d.url, "title": d.title, "publish_date": d.publish_date, "fetch_time": d.fetch_time, "snippet_hash": d.snippet_hash})
    return "\n".join(lines).strip(), cits
