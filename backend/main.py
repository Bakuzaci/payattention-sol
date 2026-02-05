"""
PayAttention.sol - Solana Meme Coin Tracker
Clean, simple, works.
"""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

import httpx
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, create_engine, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.future import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ============================================================================
# Database Models
# ============================================================================

Base = declarative_base()

class Token(Base):
    __tablename__ = "tokens"
    
    id = Column(Integer, primary_key=True)
    coingecko_id = Column(String(100), unique=True, index=True)
    address = Column(String(100), nullable=True)  # Solana address if available
    name = Column(String(200))
    symbol = Column(String(50))
    image = Column(Text, nullable=True)
    
    # Category from CoinGecko
    category = Column(String(100))  # pump-fun, solana-meme-coins, ai-meme-coins
    
    # Market data (updated each snapshot)
    market_cap = Column(Float, default=0)
    volume_24h = Column(Float, default=0)
    price = Column(Float, default=0)
    price_change_24h = Column(Float, default=0)
    
    # Social links
    twitter = Column(Text, nullable=True)
    telegram = Column(Text, nullable=True)
    website = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Database setup
DATABASE_URL = "sqlite+aiosqlite:///./payattention.db"
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ============================================================================
# CoinGecko Data Fetcher
# ============================================================================

COINGECKO_API = "https://api.coingecko.com/api/v3"

# Categories we care about
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
            print(f"[CoinGecko] {category_id} returned {resp.status_code}")
        except Exception as e:
            print(f"[CoinGecko] Error fetching {category_id}: {e}")
    return []


async def fetch_token_details(coingecko_id: str) -> Optional[Dict]:
    """Fetch detailed token info (social links, address)."""
    async with httpx.AsyncClient() as client:
        url = f"{COINGECKO_API}/coins/{coingecko_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "false",
            "community_data": "false",
            "developer_data": "false",
        }
        try:
            resp = await client.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                platforms = data.get("platforms", {})
                links = data.get("links", {})
                
                twitter = links.get("twitter_screen_name")
                telegram = links.get("telegram_channel_identifier")
                websites = links.get("homepage", [])
                
                return {
                    "address": platforms.get("solana"),
                    "twitter": f"https://twitter.com/{twitter}" if twitter else None,
                    "telegram": f"https://t.me/{telegram}" if telegram else None,
                    "website": websites[0] if websites and websites[0] else None,
                }
        except Exception as e:
            print(f"[CoinGecko] Error fetching details for {coingecko_id}: {e}")
    return None


async def sync_tokens():
    """Fetch all tokens from CoinGecko and update database."""
    print(f"[{datetime.utcnow()}] Starting token sync...")
    
    async with async_session() as session:
        total_synced = 0
        
        for category_id, category_name in CATEGORIES:
            print(f"  Fetching {category_name}...")
            tokens = await fetch_category_tokens(category_id, limit=100)
            await asyncio.sleep(1.5)  # Rate limit
            
            for t in tokens:
                cg_id = t.get("id")
                if not cg_id:
                    continue
                
                # Check if exists
                result = await session.execute(
                    select(Token).where(Token.coingecko_id == cg_id)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Update market data
                    existing.market_cap = t.get("market_cap") or 0
                    existing.volume_24h = t.get("total_volume") or 0
                    existing.price = t.get("current_price") or 0
                    existing.price_change_24h = t.get("price_change_percentage_24h") or 0
                    existing.image = t.get("image")
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new token
                    new_token = Token(
                        coingecko_id=cg_id,
                        name=t.get("name", "Unknown"),
                        symbol=(t.get("symbol") or "???").upper(),
                        image=t.get("image"),
                        category=category_id,
                        market_cap=t.get("market_cap") or 0,
                        volume_24h=t.get("total_volume") or 0,
                        price=t.get("current_price") or 0,
                        price_change_24h=t.get("price_change_percentage_24h") or 0,
                    )
                    session.add(new_token)
                    total_synced += 1
            
            await session.commit()
            print(f"    Synced {len(tokens)} tokens from {category_name}")
        
        # Fetch social links for top 30 tokens (by market cap)
        print("  Fetching social links for top tokens...")
        top_result = await session.execute(
            select(Token)
            .where(Token.twitter.is_(None))
            .order_by(Token.market_cap.desc())
            .limit(30)
        )
        top_tokens = top_result.scalars().all()
        
        for token in top_tokens:
            details = await fetch_token_details(token.coingecko_id)
            await asyncio.sleep(1.5)  # Rate limit
            
            if details:
                token.address = details.get("address")
                token.twitter = details.get("twitter")
                token.telegram = details.get("telegram")
                token.website = details.get("website")
        
        await session.commit()
        print(f"[{datetime.utcnow()}] Sync complete. {total_synced} new tokens added.")


# ============================================================================
# FastAPI App
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown."""
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database initialized.")
    
    # Start scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(sync_tokens, "interval", minutes=15, id="sync")
    scheduler.start()
    print("Scheduler started (syncs every 15 min).")
    
    # Initial sync after 3 seconds
    scheduler.add_job(sync_tokens, "date", run_date=datetime.now() + timedelta(seconds=3))
    
    yield
    
    scheduler.shutdown()
    print("Shutdown complete.")


app = FastAPI(title="PayAttention.sol", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"status": "online", "app": "PayAttention.sol"}


@app.get("/api/categories")
async def get_categories():
    """Get all categories with stats."""
    async with async_session() as session:
        result = []
        
        for category_id, category_name in CATEGORIES:
            # Get stats for this category
            stats = await session.execute(
                select(
                    func.count(Token.id),
                    func.sum(Token.market_cap),
                    func.sum(Token.volume_24h),
                ).where(Token.category == category_id)
            )
            count, total_mcap, total_vol = stats.one()
            
            result.append({
                "id": category_id,
                "name": category_name,
                "token_count": count or 0,
                "total_market_cap": total_mcap or 0,
                "total_volume_24h": total_vol or 0,
            })
        
        return result


@app.get("/api/tokens")
async def get_tokens(
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort: str = Query("market_cap", regex="^(market_cap|volume_24h|price_change_24h)$"),
):
    """Get tokens, optionally filtered by category."""
    async with async_session() as session:
        query = select(Token)
        
        if category:
            query = query.where(Token.category == category)
        
        # Sort
        if sort == "volume_24h":
            query = query.order_by(Token.volume_24h.desc())
        elif sort == "price_change_24h":
            query = query.order_by(Token.price_change_24h.desc())
        else:
            query = query.order_by(Token.market_cap.desc())
        
        query = query.offset(offset).limit(limit)
        
        result = await session.execute(query)
        tokens = result.scalars().all()
        
        return [
            {
                "id": t.coingecko_id,
                "address": t.address,
                "name": t.name,
                "symbol": t.symbol,
                "image": t.image,
                "category": t.category,
                "market_cap": t.market_cap,
                "volume_24h": t.volume_24h,
                "price": t.price,
                "price_change_24h": t.price_change_24h,
                "twitter": t.twitter,
                "telegram": t.telegram,
                "website": t.website,
            }
            for t in tokens
        ]


@app.get("/api/tokens/{token_id}")
async def get_token(token_id: str):
    """Get a single token by CoinGecko ID."""
    async with async_session() as session:
        result = await session.execute(
            select(Token).where(Token.coingecko_id == token_id)
        )
        t = result.scalar_one_or_none()
        
        if not t:
            return {"error": "Token not found"}
        
        return {
            "id": t.coingecko_id,
            "address": t.address,
            "name": t.name,
            "symbol": t.symbol,
            "image": t.image,
            "category": t.category,
            "market_cap": t.market_cap,
            "volume_24h": t.volume_24h,
            "price": t.price,
            "price_change_24h": t.price_change_24h,
            "twitter": t.twitter,
            "telegram": t.telegram,
            "website": t.website,
        }


@app.post("/api/sync")
async def trigger_sync():
    """Manually trigger a sync."""
    await sync_tokens()
    return {"status": "ok", "message": "Sync complete"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
