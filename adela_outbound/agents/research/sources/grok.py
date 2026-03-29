async def get_founder_context(company_name: str, twitter_handle: str = None) -> dict:
    return {
        'success': False,
        'recent_focus': '',
        'pain_points_mentioned': [],
        'notable_posts': [],
        'error': 'not implemented',
    }
