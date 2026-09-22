import bisect
import heapq
import re
import time
from collections import OrderedDict


_products = []
_product_map = {}
_price_sorted = []
_price_values = []
_trie = {"children": {}, "ids": set()}
_cache = OrderedDict()
_cache_capacity = 100
_cache_hits = 0
_cache_misses = 0
_last_engine_time_us = 0


def _tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def _score(product):
    return (product["rating"] * 0.5
            + product["popularity"] * 0.3
            + product["relevance"] * 0.2)


def _matching_ids(tokens):
    if not tokens:
        return set()
    matching = None
    for token in tokens:
        node = _trie
        for character in token:
            node = node["children"].get(character)
            if node is None:
                return set()
        token_ids = node["ids"]
        matching = token_ids if matching is None else matching & token_ids
        if not matching:
            return set()
    return matching


def _top_k(products, limit=10):
    heap = []
    for product in products:
        item = (_score(product), product["id"], product)
        if len(heap) < limit:
            heapq.heappush(heap, item)
        elif item[:2] > heap[0][:2]:
            heapq.heapreplace(heap, item)
    return [item[2]["id"] for item in sorted(heap, key=lambda item: item[:2], reverse=True)]


def _cache_get(key):
    global _cache_hits
    if key not in _cache:
        return None
    _cache_hits += 1
    _cache.move_to_end(key)
    return _cache[key]


def _cache_put(key, value):
    _cache[key] = value
    _cache.move_to_end(key)
    if len(_cache) > _cache_capacity:
        _cache.popitem(last=False)


def _search(query, min_price=None, max_price=None):
    global _cache_misses, _last_engine_time_us
    started = time.perf_counter_ns()
    cache_key = query if min_price is None else f"{query}|{int(min_price)}|{int(max_price)}"
    cached = _cache_get(cache_key)
    if cached is not None:
        _last_engine_time_us = (time.perf_counter_ns() - started) // 1000
        return cached

    _cache_misses += 1
    tokens = _tokenize(query)
    if min_price is None:
        candidates = _products if not tokens else [
            _product_map[product_id] for product_id in _matching_ids(tokens)
        ]
    else:
        start = bisect.bisect_left(_price_values, min_price)
        end = bisect.bisect_right(_price_values, max_price)
        candidates = _price_sorted[start:end]
        if tokens:
            matching = _matching_ids(tokens)
            candidates = [product for product in candidates if product["id"] in matching]

    result = _top_k(candidates)
    _cache_put(cache_key, result)
    _last_engine_time_us = (time.perf_counter_ns() - started) // 1000
    return result


def load_products(product_list):
    global _products, _product_map, _price_sorted, _price_values
    global _trie, _cache, _cache_hits, _cache_misses
    _products = [dict(product) for product in product_list]
    _product_map = {product["id"]: product for product in _products}
    _price_sorted = sorted(_products, key=lambda product: product["price"])
    _price_values = [product["price"] for product in _price_sorted]
    _trie = {"children": {}, "ids": set()}
    for product in _products:
        for token in set(_tokenize(product["name"])):
            node = _trie
            for character in token:
                node = node["children"].setdefault(
                    character, {"children": {}, "ids": set()}
                )
                node["ids"].add(product["id"])
    _cache = OrderedDict()
    _cache_hits = 0
    _cache_misses = 0
    return len(_products)

def get_loaded_count():
    return len(_products)

def get_cache_hits():
    return _cache_hits

def get_cache_misses():
    return _cache_misses

def get_last_engine_time_us():
    return _last_engine_time_us

def reset_cache_stats():
    global _cache_hits, _cache_misses
    _cache_hits = 0
    _cache_misses = 0

def autocomplete(prefix):
    tokens = _tokenize(prefix)
    if not tokens:
        return []
    matching = _matching_ids(tokens)
    return _top_k([_product_map[product_id] for product_id in matching], limit=8)

def search_products(query):
    """Returns (ids, cache_hit)."""
    hits_before = get_cache_hits()
    result = _search(query)
    return result, get_cache_hits() > hits_before

def search_with_price(query, min_price, max_price):
    """Returns (ids, cache_hit). Uses Binary Search + Min-Heap in Python."""
    hits_before = get_cache_hits()
    result = _search(query, min_price, max_price)
    return result, get_cache_hits() > hits_before
