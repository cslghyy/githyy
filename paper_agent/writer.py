from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Iterable

from .models import EvidenceSource, PaperRequest


def build_reference_markdown(literature: Iterable[EvidenceSource], data_sources: Iterable[EvidenceSource]) -> str:
    lines = ["## 参考文献与数据来源", ""]
    for source in list(literature) + list(data_sources):
        author_segment = "、".join(source.authors[:4]) if source.authors else source.publisher
        year_segment = source.year or "n.d."
        lines.append(
            f"- [{source.source_id}] {author_segment}. 《{source.title}》. {source.publisher}, {year_segment}. {source.url}"
        )
    return "\n".join(lines)


def validate_citations(markdown: str, allowed_source_ids: set[str]) -> None:
    matches = re.findall(r"\[([A-Z]\d+(?:,\s*[A-Z]\d+)*)\]", markdown)
    cited_ids: set[str] = set()
    for match in matches:
        for token in [item.strip() for item in match.split(",")]:
            cited_ids.add(token)
    unknown = cited_ids - allowed_source_ids
    if unknown:
        raise ValueError(f"发现未检索到的引用标识: {sorted(unknown)}")


class TemplatePaperWriter:
    def generate(self, request: PaperRequest, literature: list[EvidenceSource], data_sources: list[EvidenceSource]) -> str:
        keywords = "、".join(request.keywords or [request.title])
        lit_citations = "".join(f"[{item.source_id}]" for item in literature[:3])
        data_citations = "".join(f"[{item.source_id}]" for item in data_sources[:2])

        abstract_lines = [
            f"本文围绕“{request.title}”展开，基于用户提供的研究内容与自动检索到的真实文献、权威数据构建论文初稿。"
            f" 文献综述主要来自 OpenAlex 与 Crossref 可核验记录，数据部分优先使用世界银行开放数据。"
            f" 现有研究显示，该议题通常围绕理论机制、实证检验与政策含义展开{lit_citations}。"
        ]
        if data_sources:
            abstract_lines.append(
                f" 数据检索结果表明，相关宏观或行业指标能够为研究假设、背景论证与现实问题刻画提供直接证据{data_citations}。"
            )
        abstract_lines.append(
            "在严格引用来源的前提下，本工作流输出的是一份可继续深化的学术论文草稿，可直接作为课堂研究、课题申请或正式写作的起点。"
        )

        lines = [
            f"# {request.title}",
            "",
            "## 摘要",
            "".join(abstract_lines),
            "",
            f"**关键词：** {keywords}",
            "",
            "## 一、研究背景与问题提出",
            f"{request.research_content}。结合自动检索结果，可以看到该主题在理论研究与现实应用层面均具有持续关注度。"
            f" 例如，{literature[0].title if literature else '相关代表性文献'}强调了研究对象与制度环境、技术变迁或市场结构之间的联系"
            f"{f'[{literature[0].source_id}]' if literature else ''}。",
            "",
            "## 二、文献综述",
        ]

        if literature:
            for item in literature[: min(len(literature), 6)]:
                authors = "、".join(item.authors[:3]) if item.authors else item.publisher
                lines.append(
                    f"1. {authors}在《{item.title}》中从相关视角讨论了该议题。"
                    f" 该记录的可验证来源为 {item.publisher}，可通过链接访问原始页面。"
                    f" 结合现有研究可将其归纳为理论基础、经验发现或研究方法方面的参考[{item.source_id}]。"
                )
        else:
            lines.append("当前未成功检索到文献，请补充更精确的关键词后重试。")

        lines.extend(
            [
                "",
                "## 三、研究设计与数据说明",
                "本文建议采用“理论分析 + 二手数据分析 + 文献比较”的研究路径。工作流自动抓取的数据主要用于："
                "（1）说明研究对象的现实背景；（2）为变量选择提供启发；（3）辅助讨论政策或管理含义。",
            ]
        )

        if data_sources:
            for item in data_sources:
                meta = item.metadata
                lines.append(
                    f"- {meta.get('country', '')} 的 {meta.get('indicator_label', item.title)} 在 {item.year} 年观测值为 "
                    f"{meta.get('value')}，来源于 {item.publisher}，可通过原始数据页核验[{item.source_id}]。"
                )
        else:
            lines.append("- 当前未命中可自动匹配的数据指标，可在输入中显式指定 World Bank 指标代码。")

        lines.extend(
            [
                "",
                "## 四、分析与讨论",
                "综合文献与数据证据，可以将分析逻辑概括为以下三个层面：",
                f"1. **理论层面**：现有研究提供了研究变量之间关系的解释框架{''.join(f'[{item.source_id}]' for item in literature[:2])}。",
                f"2. **现实层面**：权威公开数据说明研究问题具有客观背景与观察基础{''.join(f'[{item.source_id}]' for item in data_sources[:3])}。",
                "3. **方法层面**：后续正式论文可进一步增加模型设定、案例比较、问卷或访谈材料，以增强论证深度与学术规范性。",
                "",
                "## 五、结论与建议",
                "基于当前自动化工作流生成的证据包，论文写作可以做到“先证据、后生成”："
                " 所有文献与数据都带有明确来源链接、机构信息与可验证标识，从而减少虚构引用与数据失真风险。"
                " 对高校教师而言，该流程适合用于选题论证、综述初稿、课堂指导与基金申请前期准备。",
                "",
            ]
        )

        lines.append(build_reference_markdown(literature, data_sources))
        return "\n".join(lines)


class OpenAICompatiblePaperWriter:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4.1")

    def available(self) -> bool:
        return bool(self.api_key)

    def generate(self, request: PaperRequest, literature: list[EvidenceSource], data_sources: list[EvidenceSource]) -> str:
        source_packet = [
            {
                "source_id": item.source_id,
                "source_type": item.source_type,
                "title": item.title,
                "summary": item.summary,
                "year": item.year,
                "authors": item.authors,
                "publisher": item.publisher,
                "url": item.url,
                "metadata": item.metadata,
            }
            for item in [*literature, *data_sources]
        ]
        prompt = (
            "你是高校论文写作智能体。请仅根据提供的真实来源写一篇中文论文初稿，"
            "不得编造任何文献、数据、作者、年份或统计值。"
            "所有事实句后必须使用方括号引用，例如 [L1]、[D2]。"
            "请输出：标题、摘要、关键词、研究背景、文献综述、研究设计与数据说明、分析与讨论、结论、参考文献与数据来源。"
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "request": {
                                "title": request.title,
                                "research_content": request.research_content,
                                "keywords": request.keywords,
                            },
                            "sources": source_packet,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "temperature": 0.2,
        }
        request_obj = urllib.request.Request(
            f"{self.api_base.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        with urllib.request.urlopen(request_obj, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"]
