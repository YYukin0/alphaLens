import json

from openai import AsyncOpenAI

from app.config import Settings
from app.core.logging import get_logger
from app.schemas.event import EVENT_TYPE_VALUES, SENTIMENT_VALUES, ExtractedEvent, ExtractionResult

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a financial analyst extracting structured corporate events from SEC filings.

Extract all material corporate events mentioned in the filing text. Use ONLY these event types:
{event_types}

For each event provide:
- event_type: one of the allowed types above (exact string match)
- summary: concise 1-2 sentence description of the event
- sentiment: one of {sentiments} (market impact perspective for equity holders)
- confidence: float 0.0-1.0 indicating extraction confidence

Return JSON with shape: {{"events": [{{"event_type": "...", "summary": "...", "sentiment": "...", "confidence": 0.9}}]}}
If no events are found, return {{"events": []}}.
""".format(
    event_types=", ".join(EVENT_TYPE_VALUES),
    sentiments=", ".join(SENTIMENT_VALUES),
)


class OpenAIEventExtractor:
    """Extract structured events from filing content using OpenAI."""

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

    def _truncate_content(self, content: str) -> str:
        max_chars = self.settings.openai_max_content_chars
        if len(content) <= max_chars:
            return content
        return content[:max_chars] + "\n\n[Content truncated for analysis...]"

    async def extract_events(
        self,
        filing_content: str,
        filing_type: str,
        accession_number: str,
    ) -> list[ExtractedEvent]:
        content = self._truncate_content(filing_content)

        response = await self.client.chat.completions.create(
            model=self.settings.openai_model,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Filing type: {filing_type}\n"
                        f"Accession number: {accession_number}\n\n"
                        f"Filing content:\n{content}"
                    ),
                },
            ],
        )

        raw = response.choices[0].message.content or '{"events": []}'
        parsed = json.loads(raw)
        result = ExtractionResult.model_validate(parsed)

        validated: list[ExtractedEvent] = []
        for event in result.events:
            if event.event_type not in EVENT_TYPE_VALUES:
                logger.warning("unknown_event_type", event_type=event.event_type)
                continue
            if event.sentiment not in SENTIMENT_VALUES:
                event.sentiment = "neutral"
            validated.append(event)

        logger.info(
            "events_extracted",
            accession_number=accession_number,
            count=len(validated),
        )
        return validated
