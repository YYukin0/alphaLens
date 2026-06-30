import json

from openai import AsyncOpenAI

from app.config import Settings
from app.core.logging import get_logger
from app.schemas.analysis import ANALYSIS_TYPE_VALUES

logger = get_logger(__name__)

PROMPTS: dict[str, str] = {
    "summary": """You are a senior equity research analyst at an institutional buy-side firm.
Summarize this SEC filing for an investment committee in 3-5 concise bullet points.
Focus on material business developments, financial performance, and strategic direction.
Return plain markdown bullet points only.""",
    "risks": """You are a risk analyst reviewing an SEC filing.
Extract the most material risks and risk factor changes. Return markdown with:
- A short overview (2 sentences max)
- Top 5 risks as bullet points with brief impact notes
If Risk Factors section content is limited, infer risks from available text and note uncertainty.""",
    "kpis": """You are a financial analyst extracting KPIs from an SEC filing.
Return markdown with a table-like list of key metrics found or implied:
- Revenue / growth
- Margins
- Cash flow highlights
- Segment performance
- Guidance or outlook metrics
Use bullet points. Mark estimates with (estimated) if not explicit.""",
    "mda": """You are analyzing Management's Discussion & Analysis (MD&A).
Return markdown covering:
- Business performance drivers
- Liquidity and capital resources
- Known trends and uncertainties
- Management outlook
Keep it concise and institutional in tone.""",
}


class OpenAIFilingAnalyzer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        if not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        return self._client

    def _truncate(self, content: str, max_chars: int = 18000) -> str:
        if len(content) <= max_chars:
            return content
        return content[:max_chars] + "\n\n[Content truncated for analysis...]"

    async def analyze(self, analysis_type: str, filing_content: str, filing_type: str) -> str:
        if analysis_type not in ANALYSIS_TYPE_VALUES:
            raise ValueError(f"Unsupported analysis type: {analysis_type}")

        prompt = PROMPTS[analysis_type]
        content = self._truncate(filing_content)

        response = await self.client.chat.completions.create(
            model=self.settings.openai_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": (
                        f"Filing type: {filing_type}\n\n"
                        f"Filing content:\n{content}"
                    ),
                },
            ],
        )

        result = (response.choices[0].message.content or "").strip()
        if not result:
            raise ValueError(f"Empty analysis result for type '{analysis_type}'")

        logger.info("filing_analysis_complete", analysis_type=analysis_type, chars=len(result))
        return result

    async def compare_filings(
        self,
        current_content: str,
        prior_content: str,
        current_type: str,
        prior_type: str,
    ) -> str:
        response = await self.client.chat.completions.create(
            model=self.settings.openai_model,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Compare two SEC filings and summarize material changes for equity analysts. "
                        "Return markdown with sections: Overview, Financial Changes, Risk Changes, "
                        "Strategic Changes, Analyst Takeaways."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "current": {"type": current_type, "content": self._truncate(current_content, 12000)},
                            "prior": {"type": prior_type, "content": self._truncate(prior_content, 12000)},
                        }
                    ),
                },
            ],
        )
        return (response.choices[0].message.content or "").strip()
