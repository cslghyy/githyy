import unittest

from paper_agent.models import EvidenceSource, PaperRequest
from paper_agent.sources import SourceRetrievalError
from paper_agent.writer import TemplatePaperWriter, validate_citations
from paper_agent.workflow import PaperWorkflow


class WriterTests(unittest.TestCase):
    def test_validate_citations_rejects_unknown_source(self) -> None:
        with self.assertRaises(ValueError):
            validate_citations("Example [L9]", {"L1", "D1"})

    def test_template_writer_uses_known_citations(self) -> None:
        request = PaperRequest(title="示例标题", research_content="示例内容", keywords=["示例"])
        literature = [
            EvidenceSource(
                source_id="L1",
                source_type="literature",
                title="Paper A",
                summary="Summary",
                url="https://example.com/a",
                publisher="OpenAlex",
                authors=["Alice"],
            )
        ]
        data_sources = [
            EvidenceSource(
                source_id="D1",
                source_type="data",
                title="Data A",
                summary="Summary",
                url="https://example.com/d",
                publisher="World Bank",
                metadata={"country": "中国", "indicator_label": "教育支出", "value": 4.2},
            )
        ]
        markdown = TemplatePaperWriter().generate(request, literature, data_sources)
        validate_citations(markdown, {"L1", "D1"})
        self.assertIn("[L1]", markdown)
        self.assertIn("[D1]", markdown)

    def test_workflow_requires_at_least_one_retrieved_source(self) -> None:
        workflow = PaperWorkflow()
        workflow.literature_searcher.search = lambda request: []
        workflow.data_collector.collect = lambda request: []
        with self.assertRaises(SourceRetrievalError):
            workflow.generate(PaperRequest(title="示例", research_content="示例"))


if __name__ == "__main__":
    unittest.main()
