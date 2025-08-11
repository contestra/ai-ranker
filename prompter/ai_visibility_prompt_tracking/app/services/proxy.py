from dataclasses import dataclass
from typing import Optional

@dataclass
class Proxy:
    id: str
    country_code: str
    endpoint: str

class ProxyPool:
    def __init__(self):
        self._cache: dict[str, Proxy] = {}

    def get(self, country_code: str) -> Optional[Proxy]:
        # Plug your proxy vendor here
        return Proxy(id=f"proxy-{country_code}", country_code=country_code, endpoint="http://localhost:8888")
