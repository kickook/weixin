import logging
from typing import Any, Dict, Optional

import requests

import config

logger = logging.getLogger(__name__)


class DifyClient:
    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        self.api_url = (api_url or config.DIFY_API_URL or '').rstrip('/')
        self.api_key = api_key or config.DIFY_API_KEY
        self.timeout = config.DIFY_TIMEOUT

    @property
    def enabled(self) -> bool:
        return bool(self.api_url and self.api_key)

    def send_alert(self, payload: Dict[str, Any]) -> Optional[str]:
        if not self.enabled:
            logger.info("Dify integration disabled; skipping alert payload")
            return None

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
        }
        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.exception("Failed to call Dify API", exc_info=exc)
            return None

        data = response.json()
        # Dify responses typically contain either a 'data' or 'result' field depending on workflow type
        if isinstance(data, dict):
            if 'result' in data and isinstance(data['result'], dict):
                return data['result'].get('answer') or data['result'].get('output')
            if 'answer' in data:
                return data.get('answer')
            if 'data' in data and isinstance(data['data'], dict):
                return data['data'].get('answer') or data['data'].get('output_text')
        return None


def build_alert_payload(alert_context: Dict[str, Any]) -> Dict[str, Any]:
    base_payload = {
        'inputs': alert_context,
        'response_mode': 'blocking',
    }
    return base_payload
