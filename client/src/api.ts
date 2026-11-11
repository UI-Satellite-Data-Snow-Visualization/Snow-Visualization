export interface Watershed { id: string; name: string | null; huc8: string }
export type Scaling = 'covariance' | 'correlation'
export interface Product {
  key: string
  label: string
  sensor: string
  platform: string
  first_year: number
  pixel_size_m: number
  default: boolean
}
export interface PCAResult {
  result_id: string
  name: string | null
  years: number[]
  scaling: Scaling
  threshold: number
  product: string
  product_label: string
  pixel_size_m: number
  pixels_in_watershed: number
  pixels_used: number
  variance_explained: number[]
  preview_url: string
  geotiff_url: string
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, options)
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new Error('Cannot reach the API. Check that FastAPI is running on port 8000.', { cause: error })
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : null
    throw new Error(detail ?? `Request failed (${response.status}). Check the API server and try again.`)
  }
  return response.json()
}

export function getWatersheds(signal: AbortSignal) {
  return request<Watershed[]>('/watersheds', { signal })
}

export function getProducts(signal: AbortSignal) {
  return request<Product[]>('/products', { signal })
}

export async function getAvailability(watershed: string, product: string, signal: AbortSignal) {
  // These are the precompute job's supported default thresholds, not inferred dates.
  const entries = await Promise.all([10, 20, 30, 40, 50].map(async threshold => {
    const result = await request<{ years: number[] }>(
      `/watersheds/${encodeURIComponent(watershed)}/years?threshold=${threshold}&product=${encodeURIComponent(product)}`,
      { signal })
    return { threshold, years: result.years }
  }))
  return entries.filter(entry => entry.years.length > 0)
}

export function runPCA(watershed: string, years: number[], threshold: number, scaling: Scaling,
  product: string, signal: AbortSignal) {
  return request<PCAResult>('/pca', {
    method: 'POST', signal, headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ watershed_id: watershed, years, threshold, scaling, product }),
  })
}
