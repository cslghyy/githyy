from __future__ import annotations

import json
import re
import urllib.parse
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .models import EvidenceSource, PaperRequest

DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "paper-agent-workflow/0.1 (+https://github.com/cslghyy/githyy)",
}


class SourceRetrievalError(RuntimeError):
    """Raised when the workflow cannot retrieve verifiable sources."""


@dataclass(frozen=True, slots=True)
class IndicatorDefinition:
    code: str
    label: str
    description: str
    tags: tuple[str, ...]


INDICATOR_CATALOG: tuple[IndicatorDefinition, ...] = (
    IndicatorDefinition("NY.GDP.MKTP.KD.ZG", "GDP增长率", "国内生产总值年增长率", ("经济", "增长", "gdp", "宏观", "market")),
    IndicatorDefinition("GB.XPD.RSDV.GD.ZS", "研发支出占GDP比重", "Research and development expenditure (% of GDP)", ("研发", "创新", "科技", "技术", "innovation")),
    IndicatorDefinition("SE.XPD.TOTL.GD.ZS", "教育支出占GDP比重", "Government expenditure on education (% of GDP)", ("教育", "高校", "教学", "教育投入")),
    IndicatorDefinition("IT.NET.USER.ZS", "互联网使用率", "Individuals using the Internet (% of population)", ("数字", "互联网", "平台", "digital")),
    IndicatorDefinition("SL.UEM.TOTL.ZS", "失业率", "Unemployment, total (% of total labor force)", ("就业", "劳动力", "产业", "labor")),
    IndicatorDefinition("FP.CPI.TOTL.ZG", "通货膨胀率", "Inflation, consumer prices (annual %)", ("价格", "消费", "市场", "通胀")),
    IndicatorDefinition("NE.TRD.GNFS.ZS", "贸易开放度", "Trade (% of GDP)", ("贸易", "开放", "出口", "进口")),
    IndicatorDefinition("SP.POP.TOTL", "总人口", "Population, total", ("人口", "城市", "区域", "demographic")),
    IndicatorDefinition("NV.IND.MANF.ZS", "制造业增加值占GDP比重", "Manufacturing, value added (% of GDP)", ("制造", "工业", "产业升级")),
    IndicatorDefinition("EG.ELC.ACCS.ZS", "电力可及率", "Access to electricity (% of population)", ("能源", "基础设施", "低碳", "可持续")),
)


def fetch_json(url: str) -> Any:
    request = urllib.request.Request(url, headers=DEFAULT_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SourceRetrievalError(f"无法访问来源接口: {url}") from exc


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def parse_openalex_work(item: dict[str, Any]) -> dict[str, Any]:
    authors = []
    for author_item in item.get("authorships", []):
        author = author_item.get("author", {})
        name = author.get("display_name")
        if name:
            authors.append(name)
    primary_location = item.get("primary_location") or {}
    landing_page = primary_location.get("landing_page_url") or primary_location.get("pdf_url") or item.get("id", "")
    return {
        "title": item.get("display_name", "").strip(),
        "summary": (item.get("abstract_inverted_index") and "摘要可通过 OpenAlex 记录补充查看。") or "未提供摘要。",
        "url": landing_page,
        "publisher": "OpenAlex",
        "year": str(item.get("publication_year") or ""),
        "authors": authors,
        "verification": {"doi": item.get("doi"), "openalex_id": item.get("id")},
    }


def parse_crossref_work(item: dict[str, Any]) -> dict[str, Any]:
    authors = []
    for author_item in item.get("author", []):
        given = author_item.get("given", "")
        family = author_item.get("family", "")
        name = f"{given} {family}".strip()
        if name:
            authors.append(name)
    title_list = item.get("title") or [""]
    year = ""
    date_parts = (((item.get("published-print") or item.get("published-online") or {}).get("date-parts")) or [[None]])
    if date_parts and date_parts[0] and date_parts[0][0]:
        year = str(date_parts[0][0])
    return {
        "title": str(title_list[0]).strip(),
        "summary": item.get("abstract", "") or "Crossref 记录未返回摘要，请打开文献落地页核验。",
        "url": item.get("URL", ""),
        "publisher": "Crossref",
        "year": year,
        "authors": authors,
        "verification": {"doi": item.get("DOI"), "crossref_type": item.get("type")},
    }


class LiteratureSearcher:
    def search(self, request: PaperRequest) -> list[EvidenceSource]:
        query = " ".join([request.title, request.research_content, *request.keywords]).strip()
        encoded = urllib.parse.quote(query)
        openalex_url = f"https://api.openalex.org/works?search={encoded}&per-page={max(request.literature_limit, 5)}"
        crossref_url = (
            "https://api.crossref.org/works"
            f"?query.bibliographic={encoded}&rows={max(request.literature_limit, 5)}&select=DOI,title,URL,author,abstract,type,published-print,published-online"
        )

        seen: set[str] = set()
        results: list[EvidenceSource] = []

        for provider_name, payload_getter, item_getter, parser in (
            ("OpenAlex", lambda: fetch_json(openalex_url), lambda payload: payload.get("results", []), parse_openalex_work),
            (
                "Crossref",
                lambda: fetch_json(crossref_url),
                lambda payload: payload.get("message", {}).get("items", []),
                parse_crossref_work,
            ),
        ):
            try:
                payload = payload_getter()
            except SourceRetrievalError:
                continue
            for item in item_getter(payload):
                parsed = parser(item)
                dedupe_key = normalize_text(parsed["verification"].get("doi") or parsed["title"])
                if not parsed["title"] or not parsed["url"] or dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                results.append(
                    EvidenceSource(
                        source_id="",
                        source_type="literature",
                        title=parsed["title"],
                        summary=parsed["summary"],
                        url=parsed["url"],
                        publisher=parsed["publisher"],
                        year=parsed["year"] or None,
                        authors=parsed["authors"],
                        verification=parsed["verification"] | {"provider": provider_name},
                    )
                )
                if len(results) >= request.literature_limit:
                    return results
        return results


def infer_country_codes(request: PaperRequest) -> list[str]:
    if request.country_codes:
        return request.country_codes
    context = f"{request.title} {request.research_content}".lower()
    codes = ["1W"]
    if any(token in context for token in ("中国", "china", "chinese")):
        codes.insert(0, "CN")
    elif any(token in context for token in ("美国", "usa", "united states")):
        codes.insert(0, "US")
    else:
        codes.insert(0, "CN")
    return codes


def select_indicators(request: PaperRequest) -> list[IndicatorDefinition]:
    if request.indicator_codes:
        requested = {code.upper() for code in request.indicator_codes}
        selected = [item for item in INDICATOR_CATALOG if item.code in requested]
        if selected:
            return selected[: request.data_limit]

    context = normalize_text(" ".join([request.title, request.research_content, *request.keywords]))
    scored: list[tuple[int, IndicatorDefinition]] = []
    for indicator in INDICATOR_CATALOG:
        score = 0
        for tag in indicator.tags:
            if normalize_text(tag) in context:
                score += 1
        if score:
            scored.append((score, indicator))
    if not scored:
        return list(INDICATOR_CATALOG[: min(request.data_limit, 4)])
    scored.sort(key=lambda item: (-item[0], item[1].code))
    return [item[1] for item in scored[: request.data_limit]]


class DataCollector:
    def collect(self, request: PaperRequest) -> list[EvidenceSource]:
        country_codes = infer_country_codes(request)
        indicators = select_indicators(request)
        results: list[EvidenceSource] = []

        for indicator in indicators:
            for country_code in country_codes:
                url = (
                    f"https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator.code}"
                    "?format=json&per_page=10&mrv=3"
                )
                try:
                    payload = fetch_json(url)
                except SourceRetrievalError:
                    continue
                observations = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
                latest = next((item for item in observations if item.get("value") is not None), None)
                if latest is None:
                    continue
                country_name = latest.get("country", {}).get("value", country_code)
                results.append(
                    EvidenceSource(
                        source_id="",
                        source_type="data",
                        title=f"{indicator.label} - {country_name}",
                        summary=(
                            f"{country_name} 在 {latest.get('date')} 年的 {indicator.label} 为 {latest.get('value')}。"
                            f" 指标释义：{indicator.description}"
                        ),
                        url=f"https://data.worldbank.org/indicator/{indicator.code}",
                        publisher="World Bank Open Data",
                        year=str(latest.get("date") or ""),
                        verification={"indicator_code": indicator.code, "country_code": country_code},
                        metadata={
                            "indicator_code": indicator.code,
                            "indicator_label": indicator.label,
                            "country": country_name,
                            "value": latest.get("value"),
                            "unit": latest.get("unit", ""),
                        },
                    )
                )
                if len(results) >= request.data_limit:
                    return results
        return results
