import json
import httpx
from urllib.parse import urljoin


class OpenRepositoryClient:
    def __init__(self, repository: str, timeout: float = 30.0):
        self.repository = repository.rstrip("/") + "/"
        self.client = httpx.Client(timeout=timeout)

    def item_url(self, item_id: str) -> str:
        return urljoin(self.repository, f"server/api/core/items/{item_id}")

    def get_item_json(self, item_id: str) -> dict:
        url = self.item_url(item_id)
        r = self.client.get(url)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def pretty_json(obj: dict) -> str:
        return json.dumps(obj, sort_keys=True, indent=4, ensure_ascii=False)

    def get_metadata(self, item_id: str) -> dict:
        return self.get_item_json(item_id).get("metadata", {})

    def close(self):
        self.client.close()