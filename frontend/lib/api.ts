/**
 * API client for CS2 Market Intelligence
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface Item {
  id: number;
  item_id: string;
  name: string;
  type: 'skin' | 'case' | 'sticker';
  release_date?: string;
  created_at: string;
  updated_at: string;
}

export interface PricePoint {
  timestamp: string;
  price: number;
  volume?: number;
  sma_7?: number;
  sma_30?: number;
}

export interface TrendAnalysis {
  item_id: number;
  item_name: string;
  current_price: number;
  trend_direction: 'bullish' | 'neutral' | 'bearish';
  confidence: 'low' | 'medium' | 'high';
  sma_7?: number;
  sma_30?: number;
  volatility?: number;
  trend_score?: number;
  explanation: string;
}

export interface Prediction {
  item_id: number;
  item_name: string;
  current_price: number;
  forecast_low: number;
  forecast_high: number;
  forecast_period: string;
  trend_direction: string;
  confidence: string;
}

export interface Opportunity {
  item_id: number;
  item_name: string;
  current_price: number;
  opportunity_type: 'undervalued' | 'overheated' | 'momentum';
  opportunity_score: number;
  reason: string;
  current_trend: string;
  volatility?: number;
}

export interface SourcePrice {
  timestamp: string;
  price: number;
  volume?: number;
  median_price?: number;
}

export interface MultiSourcePrices {
  item_id: string;
  name: string;
  sources: string[];
  data: {
    [source: string]: SourcePrice[];
  };
}

// Items API
export async function getItems(type?: string, skip = 0, limit = 50) {
  const url = new URL(`${API_URL}/items/`);
  if (type) url.searchParams.append('type', type);
  url.searchParams.append('skip', skip.toString());
  url.searchParams.append('limit', limit.toString());

  const response = await fetch(url.toString());
  return response.json();
}

export async function searchItems(query: string) {
  const url = new URL(`${API_URL}/items/search`);
  url.searchParams.append('q', query);

  const response = await fetch(url.toString());
  return response.json();
}

export async function getTrendingItems(limit = 10) {
  const url = new URL(`${API_URL}/items/trending`);
  url.searchParams.append('limit', limit.toString());

  const response = await fetch(url.toString());
  return response.json();
}

export async function getItem(itemId: string) {
  const response = await fetch(`${API_URL}/items/${itemId}`);
  return response.json();
}

export async function getPriceHistory(itemId: string, days = 30, skip = 0, limit = 100) {
  const url = new URL(`${API_URL}/items/${itemId}/price-history`);
  url.searchParams.append('days', days.toString());
  url.searchParams.append('skip', skip.toString());
  url.searchParams.append('limit', limit.toString());

  const response = await fetch(url.toString());
  return response.json();
}

export async function getItemTrends(itemId: string) {
  const response = await fetch(`${API_URL}/items/${itemId}/trends`);
  return response.json();
}

export async function getItemPrediction(itemId: string, period = '7_days') {
  const url = new URL(`${API_URL}/items/${itemId}/prediction`);
  url.searchParams.append('period', period);

  const response = await fetch(url.toString());
  return response.json();
}

export async function getItemEvents(itemId: string, limit = 20) {
  const url = new URL(`${API_URL}/items/${itemId}/events`);
  url.searchParams.append('limit', limit.toString());

  const response = await fetch(url.toString());
  return response.json();
}

export async function getMultiSourcePrices(
  itemId: string,
  sources: string[] = ['steam', 'skinport', 'dmarket'],
  days: number = 30
): Promise<MultiSourcePrices> {
  const sourceParam = sources.join(',');
  const url = new URL(`${API_URL}/items/${itemId}/prices`);
  url.searchParams.append('source', sourceParam);
  url.searchParams.append('days', days.toString());

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error('Failed to fetch multi-source prices');
  return response.json();
}

// Opportunities API
export async function getOpportunities(type?: string, limit = 20) {
  const url = new URL(`${API_URL}/opportunities/`);
  if (type) url.searchParams.append('type', type);
  url.searchParams.append('limit', limit.toString());

  const response = await fetch(url.toString());
  return response.json();
}

export async function getUndervaluedItems(limit = 10) {
  const url = new URL(`${API_URL}/opportunities/undervalued`);
  url.searchParams.append('limit', limit.toString());

  const response = await fetch(url.toString());
  return response.json();
}

export async function getOverheatedItems(limit = 10) {
  const url = new URL(`${API_URL}/opportunities/overheated`);
  url.searchParams.append('limit', limit.toString());

  const response = await fetch(url.toString());
  return response.json();
}

export async function getMomentumItems(limit = 10) {
  const url = new URL(`${API_URL}/opportunities/momentum`);
  url.searchParams.append('limit', limit.toString());

  const response = await fetch(url.toString());
  return response.json();
}

// Events API
export async function getEvents(type?: string, skip = 0, limit = 50) {
  const url = new URL(`${API_URL}/events/`);
  if (type) url.searchParams.append('type', type);
  url.searchParams.append('skip', skip.toString());
  url.searchParams.append('limit', limit.toString());

  const response = await fetch(url.toString());
  return response.json();
}

export async function getRecentEvents(limit = 20) {
  const url = new URL(`${API_URL}/events/recent`);
  url.searchParams.append('limit', limit.toString());

  const response = await fetch(url.toString());
  return response.json();
}

// Health check
export async function healthCheck() {
  const response = await fetch(`${API_URL}/health`);
  return response.json();
}

// Auth API
export async function getMe() {
  const response = await fetch(`${API_URL}/auth/me`, {
    credentials: 'include',
  });
  if (!response.ok) return null;
  return response.json();
}

export function getLoginUrl() {
  return `${API_URL}/auth/steam/login`;
}

export async function logout() {
  const response = await fetch(`${API_URL}/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  });
  return response.json();
}

// Portfolio API
export async function getInventory() {
  const response = await fetch(`${API_URL}/portfolio/inventory`, {
    credentials: 'include',
  });
  if (!response.ok) {
    if (response.status === 401) return { error: 'unauthorized' };
    return { error: 'failed' };
  }
  return response.json();
}
