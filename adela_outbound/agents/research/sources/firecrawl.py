async def scrape(url: str) -> dict:
    return {
        'success': False,
        'markdown': '',
        'url': url,
        'title': None,
        'description': None,
        'error': 'not implemented',
    }
