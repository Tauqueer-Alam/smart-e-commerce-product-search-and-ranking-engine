import ctypes
import os

_lib_name = "engine2.dll" if os.name == "nt" else "libengine.so"
_lib_dir  = os.path.dirname(os.path.abspath(__file__))
_lib_path = os.path.join(_lib_dir, _lib_name)

if os.name == "nt":
    os.add_dll_directory(_lib_dir)

try:
    _engine = ctypes.CDLL(_lib_path)
    print(f"[engine_wrapper] Loaded: {_lib_path}")
except OSError as e:
    print(f"[engine_wrapper] ERROR loading engine: {e}")
    _engine = None

if _engine:
    _engine.load_products.argtypes  = [ctypes.c_char_p]
    _engine.load_products.restype   = ctypes.c_int

    _engine.get_loaded_count.argtypes = []
    _engine.get_loaded_count.restype  = ctypes.c_int

    _engine.get_cache_hits.argtypes   = []
    _engine.get_cache_hits.restype    = ctypes.c_int

    _engine.get_cache_misses.argtypes = []
    _engine.get_cache_misses.restype  = ctypes.c_int

    _engine.reset_cache_stats.argtypes = []
    _engine.reset_cache_stats.restype  = None

    _engine.autocomplete.argtypes    = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    _engine.autocomplete.restype     = None

    _engine.search_products.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    _engine.search_products.restype  = None

    _engine.search_with_price.argtypes = [ctypes.c_char_p, ctypes.c_double, ctypes.c_double,
                                          ctypes.c_char_p, ctypes.c_int]
    _engine.search_with_price.restype  = None

    _engine.get_last_engine_time_us.argtypes = []
    _engine.get_last_engine_time_us.restype  = ctypes.c_longlong


def load_products(product_list):
    if not _engine:
        return 0
    lines = []
    for p in product_list:
        name = p['name'].replace('|', '-')
        lines.append(f"{p['id']}|{name}|{p['price']}|{p['rating']}|{p['popularity']}|{p['relevance']}")
    csv_data = "\n".join(lines)
    n = _engine.load_products(csv_data.encode("utf-8"))
    print(f"[engine_wrapper] load_products: {n} products loaded into C++ engine")
    return n

def get_loaded_count():
    return _engine.get_loaded_count() if _engine else 0

def get_cache_hits():
    return _engine.get_cache_hits() if _engine else 0

def get_cache_misses():
    return _engine.get_cache_misses() if _engine else 0

def get_last_engine_time_us():
    """Return the real C++ engine time (chrono) from the last search, in microseconds."""
    return _engine.get_last_engine_time_us() if _engine else 0

def reset_cache_stats():
    if _engine:
        _engine.reset_cache_stats()

def _parse_ids(buf_val):
    raw = buf_val.decode("utf-8")
    return [int(x) for x in raw.split(",") if x] if raw else []

def autocomplete(prefix):
    if not _engine:
        return []
    buf = ctypes.create_string_buffer(4096)
    _engine.autocomplete(prefix.encode("utf-8"), buf, 4096)
    return _parse_ids(buf.value)

def search_products(query):
    """Returns (ids, cache_hit)."""
    if not _engine:
        return [], False
    hits_before = get_cache_hits()
    buf = ctypes.create_string_buffer(4096)
    _engine.search_products(query.encode("utf-8"), buf, 4096)
    cache_hit = get_cache_hits() > hits_before
    return _parse_ids(buf.value), cache_hit

def search_with_price(query, min_price, max_price):
    """Returns (ids, cache_hit). Uses Binary Search + Min-Heap in C++."""
    if not _engine:
        return [], False
    hits_before = get_cache_hits()
    buf = ctypes.create_string_buffer(4096)
    _engine.search_with_price(
        query.encode("utf-8"),
        ctypes.c_double(min_price),
        ctypes.c_double(max_price),
        buf, 4096
    )
    cache_hit = get_cache_hits() > hits_before
    return _parse_ids(buf.value), cache_hit
