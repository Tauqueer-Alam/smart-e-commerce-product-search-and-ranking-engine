#include <iostream>
#include <string>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <queue>
#include <algorithm>
#include <cstring>
#include <list>
#include <sstream>
#include <chrono>
#include <cctype>

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif

using namespace std;

// ---------------------------------------------------------------------------
// Product
// ---------------------------------------------------------------------------
struct Product {
    int id;
    string name;
    double price;
    double rating;
    int popularity;
    double relevance;
    double score;

    void calculate_score() {
        // Internal heap score (raw, not the normalized /10 shown to users)
        score = rating * 0.5 + (double)popularity * 0.3 + relevance * 0.2;
    }
};

// ---------------------------------------------------------------------------
// LRU Cache  —  O(1) get/put  (HashMap + Doubly Linked List)
// ---------------------------------------------------------------------------
struct CacheItem { string query; string result_csv; };

class LRUCache {
private:
    int capacity;
    list<CacheItem> dll;
    unordered_map<string, list<CacheItem>::iterator> mp;
public:
    LRUCache(int cap) : capacity(cap) {}

    bool get(const string& query, string& out) {
        auto it = mp.find(query);
        if (it == mp.end()) return false;
        dll.splice(dll.begin(), dll, it->second);
        out = it->second->result_csv;
        return true;
    }

    void put(const string& query, const string& result_csv) {
        auto it = mp.find(query);
        if (it != mp.end()) {
            dll.splice(dll.begin(), dll, it->second);
            it->second->result_csv = result_csv;
            return;
        }
        if ((int)dll.size() == capacity) {
            mp.erase(dll.back().query);
            dll.pop_back();
        }
        dll.push_front({query, result_csv});
        mp[query] = dll.begin();
    }

    int size() { return (int)dll.size(); }
};

// ---------------------------------------------------------------------------
// Token Trie
//
// Each product name is split into word tokens:
//   "Dell Laptop Ultra 8"  ->  ["dell", "laptop", "ultra", "8"]
//
// Each token is inserted independently so that searching "laptop" finds
// "Dell Laptop Ultra 8", "Apple Laptop Ultra 4", etc.
//
// Product IDs are stored at every prefix node during insertion, so a
// prefix search is O(L) — just traverse L chars and read the list.
// ---------------------------------------------------------------------------
struct TrieNode {
    unordered_map<char, TrieNode*> children;
    vector<int> product_ids;  // IDs whose word passes through this prefix
};

// ---------------------------------------------------------------------------
// Global state
// ---------------------------------------------------------------------------
static LRUCache   g_cache(100);
static TrieNode*  g_trie_root = nullptr;
static vector<Product>             g_products;
static unordered_map<int, Product> g_product_map;  // O(1) ID lookup
static vector<Product>             g_price_sorted; // sorted by price

static int       g_cache_hits            = 0;
static int       g_cache_misses          = 0;
static long long g_last_engine_time_us   = 0; // real C++ timing via chrono

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
static string to_lower_str(const string& s) {
    string r = s;
    transform(r.begin(), r.end(), r.begin(),
              [](unsigned char c){ return (char)tolower(c); });
    return r;
}

// Split text into lowercase alphanumeric tokens
static vector<string> tokenize(const string& text) {
    vector<string> tokens;
    string word;
    for (unsigned char c : text) {
        if (isalnum(c)) word += (char)tolower(c);
        else if (!word.empty()) { tokens.push_back(word); word.clear(); }
    }
    if (!word.empty()) tokens.push_back(word);
    return tokens;
}

// Insert one token; record product id at every prefix node
static void trie_insert_token(TrieNode* root, const string& token, int id) {
    TrieNode* cur = root;
    for (char c : token) {
        if (!cur->children.count(c)) cur->children[c] = new TrieNode();
        cur = cur->children[c];
        cur->product_ids.push_back(id);
    }
}

// Tokenize product name and insert each word
static void trie_insert(TrieNode* root, const string& name, int id) {
    for (const auto& tok : tokenize(name))
        trie_insert_token(root, tok, id);
}

// Prefix search: collect all product IDs whose word starts with prefix
static void trie_search(TrieNode* root, const string& prefix,
                        unordered_set<int>& out) {
    if (!root || prefix.empty()) return;
    TrieNode* cur = root;
    for (char c : to_lower_str(prefix)) {
        auto it = cur->children.find(c);
        if (it == cur->children.end()) return;
        cur = it->second;
    }
    for (int id : cur->product_ids) out.insert(id);
}

// Multi-token prefix search: returns INTERSECTION of IDs matching all tokens
static void trie_search_intersect(TrieNode* root, const vector<string>& tokens,
                                  unordered_set<int>& out) {
    if (!root || tokens.empty()) return;
    
    unordered_set<int> current_ids;
    trie_search(root, tokens[0], current_ids);
    
    for (size_t i = 1; i < tokens.size(); i++) {
        if (current_ids.empty()) break;
        unordered_set<int> next_ids;
        trie_search(root, tokens[i], next_ids);
        
        unordered_set<int> intersection;
        for (int id : current_ids) {
            if (next_ids.count(id)) intersection.insert(id);
        }
        current_ids = std::move(intersection);
    }
    out = std::move(current_ids);
}

struct MinHeapCmp {
    bool operator()(const Product& a, const Product& b) { return a.score > b.score; }
};

static string ids_to_csv(vector<int>& ids) {
    string res;
    for (int id : ids) res += to_string(id) + ",";
    if (!res.empty()) res.pop_back();
    return res;
}

// Min-Heap Top-K from a candidate list  —  O(M log K)
static void run_min_heap(vector<Product>& candidates, vector<int>& out, int K = 10) {
    priority_queue<Product, vector<Product>, MinHeapCmp> heap;
    for (const Product& p : candidates) {
        heap.push(p);
        if ((int)heap.size() > K) heap.pop();
    }
    while (!heap.empty()) { out.push_back(heap.top().id); heap.pop(); }
    reverse(out.begin(), out.end());
}

// Binary Search lower bound (price >= min_p)
static int bs_lower(double min_p) {
    int lo = 0, hi = (int)g_price_sorted.size() - 1,
        idx = (int)g_price_sorted.size();
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        if (g_price_sorted[mid].price >= min_p) { idx = mid; hi = mid - 1; }
        else lo = mid + 1;
    }
    return idx;
}

// Binary Search upper bound (price <= max_p)
static int bs_upper(double max_p) {
    int lo = 0, hi = (int)g_price_sorted.size() - 1, idx = -1;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        if (g_price_sorted[mid].price <= max_p) { idx = mid; lo = mid + 1; }
        else hi = mid - 1;
    }
    return idx;
}

// ---------------------------------------------------------------------------
// Exported C API
// ---------------------------------------------------------------------------
extern "C" {

EXPORT int load_products(const char* csv_data) {
    if (!csv_data) return 0;
    g_products.clear();
    g_product_map.clear();
    g_price_sorted.clear();
    g_cache       = LRUCache(100);
    g_cache_hits  = 0;
    g_cache_misses= 0;
    delete g_trie_root;
    g_trie_root = new TrieNode();

    istringstream ss(csv_data);
    string line;
    while (getline(ss, line)) {
        if (line.empty()) continue;
        istringstream ls(line);
        string tok;
        Product p;
        try {
            getline(ls, tok, '|'); p.id         = stoi(tok);
            getline(ls, tok, '|'); p.name        = tok;
            getline(ls, tok, '|'); p.price       = stod(tok);
            getline(ls, tok, '|'); p.rating      = stod(tok);
            getline(ls, tok, '|'); p.popularity  = stoi(tok);
            getline(ls, tok, '|'); p.relevance   = stod(tok);
        } catch (...) { continue; }
        p.calculate_score();
        g_products.push_back(p);
        g_product_map[p.id] = p;
        trie_insert(g_trie_root, p.name, p.id);
    }

    g_price_sorted = g_products;
    sort(g_price_sorted.begin(), g_price_sorted.end(),
         [](const Product& a, const Product& b){ return a.price < b.price; });

    return (int)g_products.size();
}

EXPORT int  get_loaded_count()     { return (int)g_products.size(); }
EXPORT int  get_cache_hits()       { return g_cache_hits;   }
EXPORT int  get_cache_misses()     { return g_cache_misses; }
EXPORT void reset_cache_stats()    { g_cache_hits = 0; g_cache_misses = 0; }
EXPORT long long get_last_engine_time_us() { return g_last_engine_time_us; }

// --- Autocomplete  O(L + M log K) via Token Trie + Min-Heap ---
EXPORT void autocomplete(const char* prefix, char* out_buf, int max_len) {
    if (!g_trie_root || !prefix) { strncpy(out_buf, "", max_len); return; }
    
    // 1. Get candidate IDs matching ALL prefix tokens
    unordered_set<int> id_set;
    auto query_tokens = tokenize(string(prefix));
    trie_search_intersect(g_trie_root, query_tokens, id_set);
    
    // 2. Build candidate products
    vector<Product> candidates;
    candidates.reserve(id_set.size());
    for (int id : id_set) {
        auto it = g_product_map.find(id);
        if (it != g_product_map.end()) candidates.push_back(it->second);
    }
    
    // 3. Min-Heap for Top 8
    vector<int> ids;
    run_min_heap(candidates, ids, 8);
    
    string res = ids_to_csv(ids);
    strncpy(out_buf, res.c_str(), max_len);
}

// --- Search: Token Trie + Min-Heap + LRU Cache ---
// Complexity: O(1) LRU lookup; on miss O(L) Trie + O(M log K) Heap
// L = query length, M = Trie candidate count, K = 10
EXPORT void search_products(const char* query, char* out_buf, int max_len) {
    if (!query) { strncpy(out_buf, "", max_len); return; }
    string q(query);

    auto t_start = chrono::high_resolution_clock::now();

    // 1. LRU Cache check  O(1)
    string cached;
    if (g_cache.get(q, cached)) {
        g_cache_hits++;
        g_last_engine_time_us = chrono::duration_cast<chrono::microseconds>(
            chrono::high_resolution_clock::now() - t_start).count();
        strncpy(out_buf, cached.c_str(), max_len);
        return;
    }
    g_cache_misses++;

    // 2. Token Trie prefix search  O(L per token)
    auto query_tokens = tokenize(q);
    unordered_set<int> candidate_ids;
    trie_search_intersect(g_trie_root, query_tokens, candidate_ids);

    // 3. Build candidate Product list from O(1) map lookups
    bool has_query = !query_tokens.empty();
    vector<Product> candidates;
    if (has_query) {
        candidates.reserve(candidate_ids.size());
        for (int id : candidate_ids) {
            auto it = g_product_map.find(id);
            if (it != g_product_map.end()) candidates.push_back(it->second);
        }
    } else {
        candidates = g_products;
    }

    // 4. Min-Heap Top-10  O(M log K)
    vector<int> ids;
    run_min_heap(candidates, ids);

    string res = ids_to_csv(ids);
    g_cache.put(q, res);

    g_last_engine_time_us = chrono::duration_cast<chrono::microseconds>(
        chrono::high_resolution_clock::now() - t_start).count();

    strncpy(out_buf, res.c_str(), max_len);
}

// --- Price-filtered search: Binary Search + Token Trie intersection + Heap ---
// Complexity: O(1) LRU; on miss O(log N) BinSearch + O(L) Trie + O(M log K) Heap
EXPORT void search_with_price(const char* query, double min_p, double max_p,
                               char* out_buf, int max_len) {
    if (!query) { strncpy(out_buf, "", max_len); return; }
    string q(query);
    string cache_key = q + "|" + to_string((int)min_p) + "|" + to_string((int)max_p);

    auto t_start = chrono::high_resolution_clock::now();

    // 1. LRU Cache  O(1)
    string cached;
    if (g_cache.get(cache_key, cached)) {
        g_cache_hits++;
        g_last_engine_time_us = chrono::duration_cast<chrono::microseconds>(
            chrono::high_resolution_clock::now() - t_start).count();
        strncpy(out_buf, cached.c_str(), max_len);
        return;
    }
    g_cache_misses++;

    // 2. Token Trie candidates  O(L)
    auto query_tokens = tokenize(q);
    unordered_set<int> trie_ids;
    trie_search_intersect(g_trie_root, query_tokens, trie_ids);

    // 3. Binary Search price slice  O(log N)
    int start_idx = bs_lower(min_p);
    int end_idx   = bs_upper(max_p);

    // 4. Intersect: products in BOTH Trie results AND price range
    bool has_query = !query_tokens.empty();
    vector<Product> candidates;
    for (int i = start_idx; i <= end_idx; i++) {
        const Product& p = g_price_sorted[i];
        if (!has_query || trie_ids.count(p.id)) candidates.push_back(p);
    }

    // 5. Min-Heap Top-10  O(M log K)
    vector<int> ids;
    run_min_heap(candidates, ids);

    string res = ids_to_csv(ids);
    g_cache.put(cache_key, res);

    g_last_engine_time_us = chrono::duration_cast<chrono::microseconds>(
        chrono::high_resolution_clock::now() - t_start).count();

    strncpy(out_buf, res.c_str(), max_len);
}

} // extern "C"
