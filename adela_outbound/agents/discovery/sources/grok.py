import logging
import json

from openai import AsyncOpenAI
from adela_outbound.config import config

logger = logging.getLogger(__name__)


async def search_x_context(query: str) -> list[dict]:
    if not config.GROK_API_KEY:
        logger.warning('GROK_API_KEY not configured, skipping Grok search')
        return []

    try:
        client = AsyncOpenAI(
            api_key=config.GROK_API_KEY,
            base_url='https://api.x.ai/v1',
        )

        response = await client.chat.completions.create(
            model='grok-3-mini',
            messages=[
                {
                    'role': 'system',
                    'content': 'You are a research assistant. When asked to find people on X (Twitter), respond ONLY with a valid JSON array. No markdown formatting, no code fences, no explanation. Return raw JSON only.',
                },
                {
                    'role': 'user',
                    'content': f'Find up to 5 recent X/Twitter posts or profiles where founders or operators discuss: {query}. Return a JSON array where each element has exactly these keys: author_handle (string, @handle without the @), post_summary (string, what they said in 1-2 sentences), company_mentioned (string or null), pain_point (string or null), url (string or null). Return only the JSON array.',
                },
            ],
            max_tokens=800,
            temperature=0.1,
        )

        content = response.choices[0].message.content
        if content is None:
            return []

        content = content.strip()

        # Remove markdown code fences
        if content.startswith('```'):
            lines = content.split('\n')
            lines = [l for l in lines if not l.strip().startswith('```')]
            content = '\n'.join(lines).strip()

        if content.startswith('json'):
            content = content[4:].strip()

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f'Grok returned non-JSON content: {content[:100]}... Error: {e}')
            return []

        if not isinstance(parsed, list):
            logger.warning(f'Grok returned non-list JSON: {type(parsed)}')
            return []

        cleaned = [
            {
                'author_handle': item.get('author_handle', ''),
                'post_summary': item.get('post_summary', ''),
                'company_mentioned': item.get('company_mentioned'),
                'pain_point': item.get('pain_point'),
                'url': item.get('url'),
                '_source': 'grok',
            }
            for item in parsed
            if isinstance(item, dict)
        ]

        return cleaned

    except Exception as e:
        logger.warning(f'Grok API error: {type(e).__name__}: {e}')
        return []


# Automated testing of Grok adapter requires a live API key. Use the __main__ block for manual testing.

if __name__ == '__main__':
    import asyncio
    results = asyncio.run(search_x_context('founders scaling AI agent deployment across enterprise clients'))
    import pprint
    pprint.pprint(results)
