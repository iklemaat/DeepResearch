import os
import json
import requests
from qwen_agent.tools.base import BaseTool, register_tool

@register_tool('brave_search')
class BraveSearch(BaseTool):
    """
    This tool performs a web search using the Brave Search API.
    """
    name = 'brave_search'
    description = 'Performs a web search using the Brave Search API.'
    parameters = [
        {
            'name': 'query',
            'type': 'string',
            'description': 'The search query.',
            'required': True
        },
        {
            'name': 'country',
            'type': 'string',
            'description': 'The country to search from (e.g., US, GB, FR).',
            'required': False
        },
        {
            'name': 'search_lang',
            'type': 'string',
            'description': 'The search language (e.g., en, es, fr).',
            'required': False
        },
        {
            'name': 'safesearch',
            'type': 'string',
            'description': 'Safesearch setting (off, moderate, strict).',
            'required': False
        },
        {
            'name': 'freshness',
            'type': 'string',
            'description': 'Filter results by date (pd: past day, pw: past week, pm: past month, py: past year, or a date range YYYY-MM-DDtoYYYY-MM-DD).',
            'required': False
        },
        {
            'name': 'result_filter',
            'type': 'string',
            'description': 'Comma-separated list of result types to include (e.g., discussions,faq,infobox,news,query,summarizer,videos,web,locations).',
            'required': False
        },
        {
            'name': 'spellcheck',
            'type': 'boolean',
            'description': 'Whether to spellcheck the query.',
            'required': False
        },
        {
            'name': 'offset',
            'type': 'integer',
            'description': 'The zero-based offset for pagination.',
            'required': False
        }
    ]

    def call(self, params: str, **kwargs) -> str:
        """
        Calls the Brave Search API with the given parameters.
        """
        try:
            params = json.loads(params)
            query = params.get('query')
            if not query:
                return 'Error: The "query" parameter is required.'

            api_key = os.getenv('BRAVE_API_KEY')
            if not api_key:
                return 'Error: The BRAVE_API_KEY environment variable is not set.'

            headers = {
                'X-Subscription-Token': api_key,
                'Accept': 'application/json'
            }

            # Prepare the query parameters, removing any that are not provided
            search_params = {
                'q': query,
                'country': params.get('country'),
                'search_lang': params.get('search_lang'),
                'safesearch': params.get('safesearch'),
                'freshness': params.get('freshness'),
                'result_filter': params.get('result_filter'),
                'spellcheck': params.get('spellcheck'),
                'offset': params.get('offset')
            }
            search_params = {k: v for k, v in search_params.items() if v is not None}

            response = requests.get(
                'https://api.search.brave.com/res/v1/web/search',
                headers=headers,
                params=search_params
            )
            response.raise_for_status()
            return json.dumps(response.json())

        except json.JSONDecodeError:
            return 'Error: Invalid JSON format for parameters.'
        except requests.exceptions.RequestException as e:
            return f'Error: An error occurred while calling the Brave Search API: {e}'
        except Exception as e:
            return f'An unexpected error occurred: {e}'
