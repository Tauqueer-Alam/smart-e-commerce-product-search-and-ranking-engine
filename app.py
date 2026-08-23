import time
from flask import Flask, render_template, request, jsonify
import db
import dsa_engine.engine_wrapper as engine

app = Flask(__name__)

def initialize_engine():
    print("Fetching all products from PostgreSQL...")
    products = db.get_all_products()
    print(f"Feeding {len(products)} products to C++ engine (Trie + Heap + LRU + BinarySearch)...")
    loaded = engine.load_products(products)
    print(f"C++ engine ready: {loaded} products loaded.")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/categories', methods=['GET'])
def categories():
    return jsonify(list(db.SEED_CATALOG.keys()))

@app.route('/api/price_range', methods=['GET'])
def price_range():
    """Return the global min/max price for the slider."""
    p_min, p_max = db.get_price_range()
    return jsonify({"min": p_min, "max": p_max})

@app.route('/api/featured', methods=['GET'])
def featured():
    category = request.args.get('category', '').strip()
    products = db.get_featured_products(category if category and category != 'All' else None)
    for p in products:
        # Normalize each term to 0–1 before weighting
        # relevance: 0.5–1.0 → 0–1,  rating: 3.0–5.0 → 0–1,  popularity: 50–1000 → 0–1
        rel_n = (p['relevance'] - 0.5) / 0.5
        rat_n = (p['rating'] - 3.0) / 2.0
        pop_n = (p['popularity'] - 50) / 950.0
        p['score'] = round((0.50 * rel_n + 0.30 * rat_n + 0.20 * pop_n) * 10, 2)
    return jsonify({
        "products": products,
        "meta": {
            "cache_hit": False,
            "structures_used": ["PostgreSQL ORDER BY"],
            "price_filter": False,
            "count": len(products),
            "response_time_ms": 0
        }
    })

@app.route('/api/autocomplete', methods=['GET'])
def autocomplete():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    product_ids = engine.autocomplete(query)
    products = db.get_products_by_ids(product_ids)
    return jsonify(products)

@app.route('/api/search', methods=['GET'])
def search():
    query    = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    min_p    = request.args.get('min_price', type=float, default=None)
    max_p    = request.args.get('max_price', type=float, default=None)

    # We now allow empty queries to pass through to the C++ engine (e.g. for pure price filtering)

    t_start = time.time()
    price_filter = min_p is not None and max_p is not None

    if price_filter:
        product_ids, cache_hit = engine.search_with_price(query, min_p, max_p)
        structures = ["Token Trie (word match)", "Binary Search (price range)", "Min-Heap (Top-K)", "LRU Cache"]
    else:
        product_ids, cache_hit = engine.search_products(query)
        structures = ["Token Trie (word match)", "Min-Heap (Top-K)", "LRU Cache"]

    # Real C++ engine time (chrono::high_resolution_clock)
    engine_us = engine.get_last_engine_time_us()
    engine_ms = round(engine_us / 1000.0, 3)

    products = db.get_products_by_ids(product_ids)

    # Optional category post-filter
    if category and category != 'All':
        products = [p for p in products if p.get('category', '') == category]

    for p in products:
        # Normalize each term to 0–1 before weighting
        rel_n = (p['relevance'] - 0.5) / 0.5
        rat_n = (p['rating'] - 3.0) / 2.0
        pop_n = (p['popularity'] - 50) / 950.0
        p['score'] = round((0.50 * rel_n + 0.30 * rat_n + 0.20 * pop_n) * 10, 2)

    response_ms = round((time.time() - t_start) * 1000, 2)

    # Cache stats
    hits   = engine.get_cache_hits()
    misses = engine.get_cache_misses()
    total  = hits + misses
    hit_rate = round((hits / total) * 100, 1) if total > 0 else 0.0

    return jsonify({
        "products": products,
        "meta": {
            "cache_hit": cache_hit,
            "cache_hits_total": hits,
            "cache_misses_total": misses,
            "hit_rate_pct": hit_rate,
            "structures_used": structures,
            "price_filter": price_filter,
            "count": len(products),
            "engine_time_us": engine_us,   # real C++ chrono time
            "engine_time_ms": engine_ms,   # same, in ms
            "response_time_ms": response_ms  # total API round-trip
        }
    })

@app.route('/api/cache_stats', methods=['GET'])
def cache_stats():
    hits   = engine.get_cache_hits()
    misses = engine.get_cache_misses()
    total  = hits + misses
    return jsonify({
        "hits": hits,
        "misses": misses,
        "total": total,
        "hit_rate_pct": round((hits / total) * 100, 1) if total > 0 else 0.0
    })

# Run startup tasks unconditionally so Gunicorn executes them
with app.app_context():
    db.setup_database()
    initialize_engine()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
