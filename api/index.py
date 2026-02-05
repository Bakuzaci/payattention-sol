"""
PayAttention.sol API - Vercel Serverless Functions
"""
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from http.server import BaseHTTPRequestHandler

import httpx

# CoinGecko API
COINGECKO_API = "https://api.coingecko.com/api/v3"

CATEGORIES = [
    ("ai-meme-coins", "AI Agents"),
    ("pump-fun", "PumpFun"),
    ("solana-meme-coins", "Solana Memes"),
]


async def fetch_category_tokens(category_id: str, limit: int = 100) -> List[Dict]:
    """Fetch tokens from a CoinGecko category."""
    async with httpx.AsyncClient() as client:
        url = f"{COINGECKO_API}/coins/markets"
        params = {
            "vs_currency": "usd",
            "category": category_id,
            "order": "market_cap_desc",
            "per_page": limit,
            "page": 1,
        }
        try:
            resp = await client.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"Error: {e}")
    return []


async def get_categories() -> List[Dict]:
    """Get all categories with aggregated stats."""
    result = []
    
    for category_id, category_name in CATEGORIES:
        tokens = await fetch_category_tokens(category_id, limit=100)
        await asyncio.sleep(1.5)  # Rate limit
        
        total_mcap = sum(t.get("market_cap") or 0 for t in tokens)
        total_vol = sum(t.get("total_volume") or 0 for t in tokens)
        
        result.append({
            "id": category_id,
            "name": category_name,
            "token_count": len(tokens),
            "total_market_cap": total_mcap,
            "total_volume_24h": total_vol,
        })
    
    return result


async def get_tokens(category: Optional[str], sort: str, limit: int) -> List[Dict]:
    """Get tokens, optionally filtered by category."""
    if category:
        tokens = await fetch_category_tokens(category, limit)
    else:
        # Fetch from all categories
        all_tokens = []
        for cat_id, _ in CATEGORIES:
            tokens = await fetch_category_tokens(cat_id, limit=50)
            await asyncio.sleep(1.5)
            all_tokens.extend(tokens)
        
        # Dedupe by id
        seen = set()
        tokens = []
        for t in all_tokens:
            if t["id"] not in seen:
                seen.add(t["id"])
                tokens.append(t)
    
    # Sort
    if sort == "volume_24h":
        tokens.sort(key=lambda t: t.get("total_volume") or 0, reverse=True)
    elif sort == "price_change_24h":
        tokens.sort(key=lambda t: t.get("price_change_percentage_24h") or 0, reverse=True)
    else:
        tokens.sort(key=lambda t: t.get("market_cap") or 0, reverse=True)
    
    # Format response
    return [
        {
            "id": t.get("id"),
            "name": t.get("name"),
            "symbol": (t.get("symbol") or "").upper(),
            "image": t.get("image"),
            "category": category,
            "market_cap": t.get("market_cap"),
            "volume_24h": t.get("total_volume"),
            "price": t.get("current_price"),
            "price_change_24h": t.get("price_change_percentage_24h"),
        }
        for t in tokens[:limit]
    ]


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse path
        path = self.path.split("?")[0]
        
        # Parse query params
        params = {}
        if "?" in self.path:
            query = self.path.split("?")[1]
            for p in query.split("&"):
                if "=" in p:
                    k, v = p.split("=", 1)
                    params[k] = v
        
        # CORS headers
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Content-Type": "application/json",
        }
        
        # Route
        if path == "/api" or path == "/api/":
            response = {"status": "online", "app": "PayAttention.sol"}
        elif path == "/api/categories":
            response = asyncio.run(get_categories())
        elif path == "/api/tokens":
            category = params.get("category")
            sort = params.get("sort", "market_cap")
            limit = int(params.get("limit", "50"))
            response = asyncio.run(get_tokens(category, sort, limit))
        else:
            self.send_response(404)
            for k, v in headers.items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
            return
        
        # Send response
        self.send_response(200)
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
