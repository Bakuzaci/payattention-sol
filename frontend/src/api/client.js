const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function fetchCategories() {
  const res = await fetch(`${API_URL}/api/categories`);
  if (!res.ok) throw new Error('Failed to fetch categories');
  return res.json();
}

export async function fetchTokens(category = null, sort = 'market_cap', limit = 100) {
  const params = new URLSearchParams({ sort, limit: String(limit) });
  if (category) params.set('category', category);
  
  const res = await fetch(`${API_URL}/api/tokens?${params}`);
  if (!res.ok) throw new Error('Failed to fetch tokens');
  return res.json();
}

export async function fetchToken(id) {
  const res = await fetch(`${API_URL}/api/tokens/${id}`);
  if (!res.ok) throw new Error('Failed to fetch token');
  return res.json();
}
