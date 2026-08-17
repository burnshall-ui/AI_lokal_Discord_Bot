import os
import logging
import requests
import redis
import json
from typing import Optional, Dict, List
from cachetools import TTLCache
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("ESI")

class ESIClient:
    def __init__(self):
        self.base_url = os.getenv("ESI_BASE_URL", "https://esi.evetech.net/latest")
        self.user_agent = os.getenv("ESI_USER_AGENT", "EVE-Discord-Bot/1.0")
        self.cache_ttl = int(os.getenv("ESI_CACHE_TTL", "300"))
        try:
            self.redis_client = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=int(os.getenv("REDIS_PORT", "6379")), password=os.getenv("REDIS_PASSWORD") or None, db=0, decode_responses=True)
            self.redis_client.ping()
            logger.info("Redis verbunden")
        except Exception as e:
            # Falling back to the in-memory cache is fine, but a wrong password
            # looks exactly like Redis being absent — so say which it was.
            logger.warning("Redis nicht verfügbar (%s), nutze In-Memory-Cache", e)
            self.redis_client = None
        self.memory_cache = TTLCache(maxsize=1000, ttl=self.cache_ttl)
        self.session = requests.Session()
    def _get_cached(self, key):
        if self.redis_client:
            try:
                data = self.redis_client.get(key)
                if data: return json.loads(data)
            except: pass
        return self.memory_cache.get(key)
    def _set_cached(self, key, data, ttl=None):
        if not ttl: ttl = self.cache_ttl
        if self.redis_client:
            try: self.redis_client.setex(key, ttl, json.dumps(data))
            except: pass
        self.memory_cache[key] = data
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _request(self, endpoint, cache=True):
        if cache:
            cached = self._get_cached(f"esi:{endpoint}")
            if cached: return cached
        try:
            r = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
            r.raise_for_status()
            data = r.json()
            if cache: self._set_cached(f"esi:{endpoint}", data)
            return data
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404: return None
            raise
    def search_type(self, search_term):
        result = self._request(f"/search/?categories=inventory_type&search={search_term}&strict=false")
        if result and "inventory_type" in result:
            types = []
            for tid in result["inventory_type"][:5]:
                info = self.get_type_info(tid)
                if info: types.append(info)
            return types
        return None
    def get_type_info(self, type_id):
        return self._request(f"/universe/types/{type_id}/")
    def get_market_prices(self, type_id, region_id=10000002):
        orders = self._request(f"/markets/{region_id}/orders/?type_id={type_id}")
        if not orders: return None
        buys = [o for o in orders if o["is_buy_order"]]
        sells = [o for o in orders if not o["is_buy_order"]]
        return {"type_id": type_id, "buy_max": max([o["price"] for o in buys]) if buys else 0, "sell_min": min([o["price"] for o in sells]) if sells else 0, "buy_volume": sum([o["volume_remain"] for o in buys]), "sell_volume": sum([o["volume_remain"] for o in sells])}
    def get_server_status(self):
        return self._request("/status/", cache=False)

_esi_client = None
def get_esi_client():
    global _esi_client
    if not _esi_client: _esi_client = ESIClient()
    return _esi_client
