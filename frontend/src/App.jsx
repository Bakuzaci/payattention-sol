import { useState, useEffect } from 'react'
import { Routes, Route, Link, useParams, useSearchParams } from 'react-router-dom'
import { fetchCategories, fetchTokens, fetchToken } from './api/client'

// ============================================================================
// Utilities
// ============================================================================

function formatNumber(n) {
  if (!n && n !== 0) return '—'
  if (n >= 1e9) return `$${(n / 1e9).toFixed(2)}B`
  if (n >= 1e6) return `$${(n / 1e6).toFixed(1)}M`
  if (n >= 1e3) return `$${(n / 1e3).toFixed(0)}K`
  return `$${n.toFixed(2)}`
}

function formatPercent(n) {
  if (!n && n !== 0) return '—'
  const sign = n >= 0 ? '+' : ''
  return `${sign}${n.toFixed(1)}%`
}

const CATEGORY_EMOJI = {
  'ai-meme-coins': '🤖',
  'pump-fun': '🎰',
  'solana-meme-coins': '☀️',
}

// ============================================================================
// Header
// ============================================================================

function Header() {
  return (
    <header className="border-b border-[#222] py-4">
      <div className="max-w-6xl mx-auto px-6 flex items-center justify-between">
        <Link to="/" className="text-xl font-bold tracking-tight">
          <span className="text-yellow">PAY</span>ATTENTION<span className="text-muted">.SOL</span>
        </Link>
        <nav className="flex gap-6 text-sm">
          <Link to="/" className="text-muted hover:text-white">Dashboard</Link>
          <a href="https://twitter.com" target="_blank" className="text-muted hover:text-white">Twitter</a>
        </nav>
      </div>
    </header>
  )
}

// ============================================================================
// Dashboard (Home)
// ============================================================================

function Dashboard() {
  const [categories, setCategories] = useState([])
  const [tokens, setTokens] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [cats, toks] = await Promise.all([
          fetchCategories(),
          fetchTokens(null, 'market_cap', 20),
        ])
        setCategories(cats)
        setTokens(toks)
      } catch (e) {
        console.error(e)
      }
      setLoading(false)
    }
    load()
  }, [])

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="loading text-center text-muted">Loading...</div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      {/* Hero */}
      <div className="mb-12">
        <h1 className="text-4xl font-bold mb-2">Solana Meme Tracker</h1>
        <p className="text-muted">Real-time data from CoinGecko. Updated every 15 minutes.</p>
      </div>

      {/* Categories */}
      <section className="mb-12">
        <h2 className="text-sm font-medium text-muted uppercase tracking-wider mb-4">Categories</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {categories.map(cat => (
            <Link 
              key={cat.id} 
              to={`/category/${cat.id}`}
              className="category-card"
            >
              <div className="flex items-center gap-3 mb-4">
                <span className="text-3xl">{CATEGORY_EMOJI[cat.id] || '📊'}</span>
                <div>
                  <div className="font-semibold">{cat.name}</div>
                  <div className="text-sm text-muted">{cat.token_count} tokens</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="text-muted">Market Cap</div>
                  <div className="font-mono font-medium">{formatNumber(cat.total_market_cap)}</div>
                </div>
                <div>
                  <div className="text-muted">Volume 24h</div>
                  <div className="font-mono font-medium">{formatNumber(cat.total_volume_24h)}</div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Top Tokens */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-muted uppercase tracking-wider">Top Tokens</h2>
          <Link to="/category/solana-meme-coins" className="text-sm text-yellow hover:underline">
            View All →
          </Link>
        </div>
        <TokenTable tokens={tokens} />
      </section>
    </div>
  )
}

// ============================================================================
// Token Table
// ============================================================================

function TokenTable({ tokens }) {
  if (!tokens || tokens.length === 0) {
    return <div className="text-center text-muted py-8">No tokens found</div>
  }

  return (
    <div className="bg-card overflow-hidden">
      <div className="overflow-x-auto">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Token</th>
              <th>Price</th>
              <th>Market Cap</th>
              <th>Volume 24h</th>
              <th>Change 24h</th>
              <th>Links</th>
            </tr>
          </thead>
          <tbody>
            {tokens.map((token, i) => (
              <tr key={token.id}>
                <td className="text-muted font-mono">{i + 1}</td>
                <td>
                  <div className="flex items-center gap-3">
                    {token.image && (
                      <img src={token.image} alt="" className="w-8 h-8 rounded-full" />
                    )}
                    <div>
                      <div className="font-medium">{token.name}</div>
                      <div className="text-sm text-muted font-mono">{token.symbol}</div>
                    </div>
                  </div>
                </td>
                <td className="font-mono">{formatNumber(token.price)}</td>
                <td className="font-mono">{formatNumber(token.market_cap)}</td>
                <td className="font-mono text-muted">{formatNumber(token.volume_24h)}</td>
                <td className={`font-mono ${token.price_change_24h >= 0 ? 'text-green' : 'text-red'}`}>
                  {formatPercent(token.price_change_24h)}
                </td>
                <td>
                  <div className="flex items-center gap-2">
                    {token.twitter && (
                      <a href={token.twitter} target="_blank" className="text-blue-400 hover:text-blue-300">
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                        </svg>
                      </a>
                    )}
                    {token.telegram && (
                      <a href={token.telegram} target="_blank" className="text-sky-400 hover:text-sky-300">
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
                        </svg>
                      </a>
                    )}
                    {token.address && (
                      <a 
                        href={`https://dexscreener.com/solana/${token.address}`} 
                        target="_blank" 
                        className="text-green hover:text-white text-xs font-mono"
                      >
                        DEX
                      </a>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ============================================================================
// Category Page
// ============================================================================

function CategoryPage() {
  const { id } = useParams()
  const [tokens, setTokens] = useState([])
  const [loading, setLoading] = useState(true)
  const [sort, setSort] = useState('market_cap')

  const categoryName = {
    'ai-meme-coins': 'AI Agents',
    'pump-fun': 'PumpFun',
    'solana-meme-coins': 'Solana Memes',
  }[id] || id

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const toks = await fetchTokens(id, sort, 100)
        setTokens(toks)
      } catch (e) {
        console.error(e)
      }
      setLoading(false)
    }
    load()
  }, [id, sort])

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <Link to="/" className="text-sm text-muted hover:text-white mb-2 inline-block">← Back</Link>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <span className="text-4xl">{CATEGORY_EMOJI[id] || '📊'}</span>
            {categoryName}
          </h1>
        </div>
        <div className="flex gap-2">
          {['market_cap', 'volume_24h', 'price_change_24h'].map(s => (
            <button
              key={s}
              onClick={() => setSort(s)}
              className={`btn ${sort === s ? 'btn-active' : ''}`}
            >
              {s === 'market_cap' ? 'MCap' : s === 'volume_24h' ? 'Volume' : 'Change'}
            </button>
          ))}
        </div>
      </div>

      {/* Tokens */}
      {loading ? (
        <div className="loading text-center text-muted py-12">Loading...</div>
      ) : (
        <TokenTable tokens={tokens} />
      )}
    </div>
  )
}

// ============================================================================
// App
// ============================================================================

export default function App() {
  return (
    <div className="min-h-screen">
      <Header />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/category/:id" element={<CategoryPage />} />
      </Routes>
    </div>
  )
}
