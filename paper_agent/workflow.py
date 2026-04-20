from __future__ import annotations

from .models import EvidenceSource, PaperRequest, PaperResult
from .sources import DataCollector, LiteratureSearcher, SourceRetrievalError
from .writer import OpenAICompatiblePaperWriter, TemplatePaperWriter, build_reference_markdown, validate_citations


class PaperWorkflow:
    def __init__(self) -> None:
        self.literature_searcher = LiteratureSearcher()
        self.data_collector = DataCollector()
        self.template_writer = TemplatePaperWriter()
        self.llm_writer = OpenAICompatiblePaperWriter()

    def generate(self, request: PaperRequest) -> PaperResult:
        literature = self._assign_ids(self.literature_searcher.search(request), prefix="L")
        data_sources = self._assign_ids(self.data_collector.collect(request), prefix="D")
        if not literature and not data_sources:
            raise SourceRetrievalError("无法检索到可验证的文献或数据来源，请检查网络连接或补充更精确的研究关键词。")
        if self.llm_writer.available():
            paper_markdown = self.llm_writer.generate(request, literature, data_sources)
        else:
            paper_markdown = self.template_writer.generate(request, literature, data_sources)

        allowed_ids = {item.source_id for item in [*literature, *data_sources]}
        validate_citations(paper_markdown, allowed_ids)
        reference_markdown = build_reference_markdown(literature, data_sources)
        if "## 参考文献与数据来源" not in paper_markdown:
            paper_markdown = f"{paper_markdown.rstrip()}\n\n{reference_markdown}\n"
        return PaperResult(
            request=request,
            literature=literature,
            data_sources=data_sources,
            paper_markdown=paper_markdown,
            reference_markdown=reference_markdown,
        )

    @staticmethod
    def _assign_ids(items: list[EvidenceSource], prefix: str) -> list[EvidenceSource]:
        for index, item in enumerate(items, start=1):
            item.source_id = f"{prefix}{index}"
        return items
