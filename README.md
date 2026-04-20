# githyy

一个面向高校教师的论文写作工作流：输入论文题目或研究内容后，自动检索**可验证的文献资料**与**带明确出处的数据**，再生成带引用标识的论文初稿。

## 功能

- 自动检索学术文献：优先从 **OpenAlex** 和 **Crossref** 获取文献元数据与落地页链接
- 自动检索研究/市场数据：优先从 **World Bank Open Data** 获取可核验指标
- 引用约束：正文只允许引用已检索到的来源编号（如 `[L1]`、`[D2]`）
- 输出结果：
  - `paper.md`：论文初稿
  - `sources.json`：文献与数据的结构化证据包
- 可选 LLM 写作：若配置 OpenAI 兼容接口，将基于真实来源生成更完整的论文文本；未配置时使用内置模板生成器

## 目录结构

```text
/home/runner/work/githyy/githyy
├── paper_agent/
├── examples/research_request.json
├── tests/
├── pyproject.toml
└── README.md
```

## 输入格式

示例文件：`/home/runner/work/githyy/githyy/examples/research_request.json`

```json
{
  "title": "数字经济背景下高校创新创业教育质量提升研究",
  "research_content": "请围绕数字经济、高校创新创业教育、人才培养质量之间的关系撰写论文。",
  "keywords": ["数字经济", "高校教育", "创新创业"],
  "country_codes": ["CN", "1W"],
  "indicator_codes": ["SE.XPD.TOTL.GD.ZS", "GB.XPD.RSDV.GD.ZS"],
  "literature_limit": 6,
  "data_limit": 6,
  "output_dir": "output"
}
```

字段说明：

- `title`：论文题目
- `research_content`：你希望重点展开的研究内容
- `keywords`：可选，帮助提高检索精度
- `country_codes`：可选，World Bank 国家/地区代码；不填时会自动推断，默认偏向 `CN` 与 `1W`
- `indicator_codes`：可选，显式指定 World Bank 指标代码
- `literature_limit` / `data_limit`：控制检索数量
- `output_dir`：输出目录

## 使用方式

### 1. 直接运行

```bash
cd /home/runner/work/githyy/githyy
python -m paper_agent.cli --input /home/runner/work/githyy/githyy/examples/research_request.json
```

### 2. 安装为命令行工具

```bash
cd /home/runner/work/githyy/githyy
python -m pip install -e .
paper-agent --input /home/runner/work/githyy/githyy/examples/research_request.json
```

## 可选：启用 OpenAI 兼容模型

如果你已经有模型服务，可设置以下环境变量：

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_API_BASE="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4.1"
```

启用后，工作流会先检索来源，再把来源包交给模型生成论文；如果模型输出了未检索到的引用编号，程序会直接报错，避免“假引用”进入结果。

## 验证

```bash
cd /home/runner/work/githyy/githyy
python -m unittest discover -s tests
```

## 适用边界

- 当前自动数据源主要接入 World Bank，适合宏观、产业、教育、就业、创新等主题
- 若你的论文需要更细颗粒度行业数据，可在后续扩展新的权威数据接口
- 输出结果是**可验证证据驱动的论文初稿**，正式投稿前仍应由教师本人补充研究方法、学术规范细节和最终论证
