import json
import logging
import os

from dotenv import load_dotenv
from openai import OpenAI

from schema.models import ReviewSummary

logger = logging.getLogger(__name__)

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None


def summarize_reviews(reviews_text: str) -> ReviewSummary:
    logger.info("Starting review summarization.")
    clean_text = (reviews_text or "").strip()
    if not clean_text:
        logger.warning("Skipping review summarization because reviews_text is empty.")
        return ReviewSummary(overall_sentiment="Unknown")
    if openai_client is None:
        logger.warning(
            "Skipping review summarization because OPENAI_API_KEY is not configured."
        )
        return ReviewSummary(overall_sentiment="Unknown")

    max_chars = 12000
    if len(clean_text) > max_chars:
        logger.warning(
            "Review text length %d exceeds max %d chars; truncating before summarization.",
            len(clean_text),
            max_chars,
        )
        clean_text = clean_text[:max_chars]

    try:
        response = openai_client.chat.completions.create(
            model=os.getenv("OPENAI_SUMMARY_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Summarize customer reviews. Identify positive and negative themes "
                        "and provide overall sentiment. Return JSON only."
                    ),
                },
                {"role": "user", "content": f"Reviews: {clean_text}"},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "review_summary",
                    "schema": ReviewSummary.model_json_schema(),
                },
            },
        )

        content = response.choices[0].message.content or ""
        parsed = ReviewSummary.model_validate(json.loads(content))
        logger.info("Review summarization complete.")
        return parsed
    except Exception:
        logger.exception("Review summarization failed.")
        return ReviewSummary(overall_sentiment="Unknown")
