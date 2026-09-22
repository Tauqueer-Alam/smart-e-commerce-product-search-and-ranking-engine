# SmartSearch Interview Report

## 1. One-Minute Explanation

SmartSearch is an e-commerce product search and ranking application. I built a Flask REST API backed by PostgreSQL, with a custom Python search engine for autocomplete, filtering, ranking, and caching. The frontend uses HTML, CSS, and vanilla JavaScript.

The main technical goal was to avoid scanning and sorting the complete product dataset for every request. At startup, the application loads products from PostgreSQL into memory and builds a Trie for word-prefix search, a price-sorted list for binary search, and an LRU cache for repeated queries. Search candidates are ranked with a fixed-size Min-Heap, so only the best 10 products are retained.

This gives the project both a practical web application and a clear demonstration of core data structures and algorithmic tradeoffs.

## 2. Technology Stack

| Area | Technology | Why it is used |
|---|---|---|
| Backend API | Python, Flask | Defines REST endpoints and coordinates the application |
| Persistence | PostgreSQL | Stores product records and supports database-level featured queries |
| Database access | SQLAlchemy | Creates connections and executes parameterized SQL |
| Search engine | Python standard library | `heapq`, `bisect`, `OrderedDict`, dictionaries, sets, and regular expressions |
| Frontend | HTML, CSS, vanilla JavaScript | Provides the search interface, filters, autocomplete, and performance panel |
| Deployment | Gunicorn | Runs the Flask application in a production-style environment |

## 3. System Architecture

```text
Browser
  |
  | HTTP requests
  v
Flask REST API
  |                         \
  | product loading           \ product details
  v                           v
Python Search Engine       PostgreSQL
  |
  +-- Trie: token-prefix matching
  +-- Min-Heap: Top-10 ranking
  +-- LRU Cache: repeated queries
  +-- Sorted prices + bisect: price range filtering
```

The main modules are:

- `app.py`: Flask routes and request/response handling.
- `db.py`: PostgreSQL connection, schema creation, seed data, and product queries.
- `dsa_engine/engine_wrapper.py`: In-memory search engine and all custom data-structure logic.
- `templates/index.html`: Main frontend page.
- `static/script.js`: API calls, debounced autocomplete, filters, and result rendering.
- `test_engine.py`: Manual integration-style engine check using database data.
- `test_score.py`: Ranking-score calculation check.

## 4. Search Request Flow

For a request such as:

```text
GET /api/search?q=nike+shoe&min_price=2000&max_price=10000
```

The application performs these steps:

1. Flask reads the query, category, and optional price parameters.
2. The engine creates a cache key containing the query and price range.
3. The LRU cache is checked first.
4. On a cache miss, each query word is traversed through the Trie. The product ID sets for all words are intersected, so every query token must match a product-name token prefix.
5. `bisect_left` and `bisect_right` find the matching section of the price-sorted list.
6. The Trie candidates and price candidates are intersected.
7. A Min-Heap of size 10 retains only the highest-scoring products.
8. Flask asks PostgreSQL for complete product records using the resulting IDs.
9. The API returns products plus metadata such as cache status, hit rate, structures used, and timing.
10. JavaScript renders the result cards and DSA performance panel.

## 5. Data Structures and Algorithms

### Trie for autocomplete and word matching

During startup, each product name is tokenized into lowercase alphanumeric words. Every character of every token is inserted into a Trie node, and each node stores the IDs of products passing through that prefix.

For example, `Nike Running Shoes` creates prefixes for `nike`, `running`, and `shoes`. A query such as `nik` reaches the `k` node and returns all products whose token starts with that prefix.

- Purpose: autocomplete and multi-word search.
- Lookup: O(L) for one token, where L is the token length.
- Multi-token search: performs one lookup per token and intersects the ID sets.

### Min-Heap for Top-K ranking

The engine does not sort every matching product. It maintains a Min-Heap with a maximum size of 10. When the heap grows beyond 10, the lowest-scoring candidate is removed.

The internal ranking value is:

```text
internal score = 0.5 * rating + 0.3 * popularity + 0.2 * relevance
```

The result is then sorted from highest to lowest score before IDs are returned.

- Purpose: return only the best 10 products.
- Complexity: O(M log K), where M is the number of candidates and K is 10.
- Space: O(K) for the ranking heap.

### LRU Cache

The cache uses Python's `OrderedDict`. A dictionary-style lookup finds a cached query, and `move_to_end` marks it as recently used. When the capacity of 100 entries is exceeded, the oldest entry is removed.

Price-filtered searches use a key such as:

```text
nike shoe|2000|10000
```

This prevents a cached result for one price range from being returned for another range.

- Cache lookup: O(1) average.
- Cache promotion: O(1).
- Eviction: O(1).
- Benefit: repeated searches avoid Trie traversal, filtering, and ranking.

### Binary search for price filtering

Products are sorted by price once during engine initialization. The `bisect` module finds the first product at or above the minimum price and the first product above the maximum price.

- Boundary lookup: O(log N).
- Ranking after filtering: O(M log K), where M is the number of products in the price range.
- Benefit: the heap ranks only products inside the selected range.

## 6. Ranking Score Shown to Users

The UI displays a normalized score from 0 to 10. Each input is normalized to a common range before applying the weights:

```text
relevance: 0.5 to 1.0 -> 0 to 1
rating:    3.0 to 5.0 -> 0 to 1
popularity: 50 to 1000 -> 0 to 1

visible score = 10 * (0.50 * normalized_relevance
                    + 0.30 * normalized_rating
                    + 0.20 * normalized_popularity)
```

The heap uses the equivalent weighted ranking order without normalization because the normalization is monotonic for the expected data ranges. Flask calculates the final display score after retrieving the product records.

## 7. Database Design

The `products` table contains:

- `id`: primary key.
- `name`: product name.
- `category`: product category.
- `price`: decimal price.
- `rating`: product rating.
- `popularity`: popularity count.
- `relevance`: search relevance value.

On startup, the application creates the table if necessary and seeds it only when it is empty. The search engine receives a snapshot of all products in memory. PostgreSQL remains the source of truth, while the in-memory structures optimize search operations.

## 8. API Endpoints

| Endpoint | Responsibility |
|---|---|
| `GET /` | Serves the frontend. |
| `GET /api/search` | Searches, filters, ranks, and returns products. |
| `GET /api/autocomplete?q=...` | Returns prefix suggestions from the Trie. |
| `GET /api/featured` | Returns featured products using a PostgreSQL `ORDER BY`. |
| `GET /api/price_range` | Returns global minimum and maximum prices. |
| `GET /api/cache_stats` | Returns cache hits, misses, and hit rate. |

## 9. Important Design Decisions

### Why load products into memory?

Search reads are frequent and the dataset is relatively small. Building indexes once at startup avoids rebuilding them for every request. PostgreSQL is still used for persistence and full product retrieval.

### Why use a heap instead of sorting?

The UI only needs the top 10 products. Sorting all candidates costs O(M log M), while a fixed-size heap costs O(M log K). Since K is 10, this is more efficient as the candidate count grows.

### Why use an LRU cache?

Search traffic often contains repeated or similar popular queries. LRU keeps recent results while automatically removing old entries, and it has predictable constant-time operations.

### Why keep category filtering in Flask?

The DSA engine returns globally ranked IDs. Flask applies the category filter after retrieving the products. This keeps the engine focused on search and ranking, although a future version could include category in the engine index for more selective ranking.

### Why use Python instead of a native extension?

A Python-only implementation is easier to run, test, deploy, and explain. The standard library provides the required algorithmic building blocks without compiler or DLL dependencies.

## 10. Testing and Validation

The project was validated with:

- Python compilation using `python -m compileall`.
- Ranking-score checks in `test_score.py`.
- Engine checks for loading products, multi-token search, autocomplete, price filtering, Top-K ordering, and cache hits.
- Static diagnostics for `app.py` and `engine_wrapper.py`.
- `git diff --check` before publishing.

A production version could add automated `pytest` tests for cache eviction, empty queries, duplicate scores, missing database connections, and category filtering.

## 11. Limitations and Future Improvements

- The in-memory index must be rebuilt when product data changes. A production system would use an update queue or periodic index refresh.
- The current LRU cache is process-local. Multiple Gunicorn workers would have separate caches; Redis could provide a shared cache.
- Category filtering currently happens after the global Top-10 selection, so a category can contain fewer results than expected. Category-aware indexing or filtering before ranking would improve this.
- PostgreSQL connection and seed credentials should be supplied entirely through environment variables in production.
- Search and ranking could be measured with a larger benchmark dataset to compare cache-hit and cache-miss latency.

## 12. Interview Questions and Short Answers

### How would you scale this system?

I would move search indexing to a dedicated search service or shared index, use Redis for a shared cache, add database indexes for metadata filters, and refresh the in-memory index asynchronously when products change.

### What happens when a product is updated?

The current process requires rebuilding the in-memory snapshot. A better design would publish a product-change event and update the affected Trie paths, price index, and cache entries incrementally.

### Why is the cache key important?

The same text query can produce different results for different price ranges. Including all search parameters in the key prevents incorrect cached responses.

### What is the biggest tradeoff?

The design trades memory and startup indexing time for faster read operations. It works well for a read-heavy catalog, but frequent writes or very large datasets would require a distributed or incremental indexing strategy.

### What would you monitor in production?

I would monitor p50/p95/p99 latency, cache hit rate, number of indexed products, search result counts, database query time, memory usage, and error rates.

## 13. Suggested Interview Closing

"This project shows how I connect algorithmic thinking with backend engineering. I used PostgreSQL for durable product data and Flask for the API, then built an in-memory Python search layer with a Trie, Min-Heap, LRU cache, and binary search. Each structure addresses a specific bottleneck, and the API exposes enough metadata to observe the search path and cache behavior." 
