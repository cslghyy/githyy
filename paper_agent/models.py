from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class EvidenceSource:
    source_id: str
    source_type: str
    title: str
    summary: str
    url: str
    publisher: str
    year: str | None = None
    authors: list[str] = field(default_factory=list)
    verification: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PaperRequest:
    title: str
    research_content: str
    language: str = "zh-CN"
    keywords: list[str] = field(default_factory=list)
    country_codes: list[str] = field(default_factory=list)
    literature_limit: int = 8
    data_limit: int = 6
    indicator_codes: list[str] = field(default_factory=list)
    output_dir: str = "output"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PaperRequest":
        return cls(
            title=payload["title"].strip(),
            research_content=payload["research_content"].strip(),
            language=payload.get("language", "zh-CN"),
            keywords=[str(item).strip() for item in payload.get("keywords", []) if str(item).strip()],
            country_codes=[str(item).strip().upper() for item in payload.get("country_codes", []) if str(item).strip()],
            literature_limit=max(1, min(int(payload.get("literature_limit", 8)), 20)),
            data_limit=max(1, min(int(payload.get("data_limit", 6)), 20)),
            indicator_codes=[str(item).strip().upper() for item in payload.get("indicator_codes", []) if str(item).strip()],
            output_dir=payload.get("output_dir", "output"),
        )


@dataclass(slots=True)
class PaperResult:
    request: PaperRequest
    literature: list[EvidenceSource]
    data_sources: list[EvidenceSource]
    paper_markdown: str
    reference_markdown: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": asdict(self.request),
            "literature": [item.to_dict() for item in self.literature],
            "data_sources": [item.to_dict() for item in self.data_sources],
            "paper_markdown": self.paper_markdown,
            "reference_markdown": self.reference_markdown,
        }

    def write_to_directory(self, root: str | Path) -> tuple[Path, Path]:
        output_root = Path(root)
        output_root.mkdir(parents=True, exist_ok=True)
        paper_path = output_root / "paper.md"
        sources_path = output_root / "sources.json"
        paper_path.write_text(self.paper_markdown, encoding="utf-8")
        sources_path.write_text(__import__("json").dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return paper_path, sources_path
