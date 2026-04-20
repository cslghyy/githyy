import unittest

from paper_agent.models import PaperRequest
from paper_agent.sources import parse_crossref_work, parse_openalex_work, select_indicators


class SourceParsingTests(unittest.TestCase):
    def test_parse_openalex_work_extracts_verification_fields(self) -> None:
        parsed = parse_openalex_work(
            {
                "display_name": "Sample Paper",
                "publication_year": 2024,
                "id": "https://openalex.org/W123",
                "doi": "https://doi.org/10.1234/example",
                "primary_location": {"landing_page_url": "https://example.com/paper"},
                "authorships": [{"author": {"display_name": "Alice"}}],
            }
        )
        self.assertEqual(parsed["title"], "Sample Paper")
        self.assertEqual(parsed["verification"]["openalex_id"], "https://openalex.org/W123")
        self.assertEqual(parsed["authors"], ["Alice"])

    def test_parse_crossref_work_extracts_authors(self) -> None:
        parsed = parse_crossref_work(
            {
                "title": ["Another Paper"],
                "URL": "https://doi.org/10.1000/demo",
                "DOI": "10.1000/demo",
                "author": [{"given": "Alice", "family": "Lee"}],
                "published-online": {"date-parts": [[2023, 5, 1]]},
                "type": "journal-article",
            }
        )
        self.assertEqual(parsed["authors"], ["Alice Lee"])
        self.assertEqual(parsed["year"], "2023")

    def test_select_indicators_prefers_matching_topics(self) -> None:
        request = PaperRequest(
            title="数字经济与高校教育投入研究",
            research_content="分析数字化基础设施和教育投入",
            keywords=["数字经济", "教育"],
        )
        selected = select_indicators(request)
        codes = {item.code for item in selected}
        self.assertIn("IT.NET.USER.ZS", codes)
        self.assertIn("SE.XPD.TOTL.GD.ZS", codes)


if __name__ == "__main__":
    unittest.main()
