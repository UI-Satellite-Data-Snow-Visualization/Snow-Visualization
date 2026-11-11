import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { getAvailability, getProducts, getWatersheds, runPCA } from './api'
import type { PCAResult, Product, Scaling, Watershed } from './api'
import './App.css'

function Results({ result }: { result: PCAResult }) {
  const [imageFailed, setImageFailed] = useState(false)
  return <section className="card results" aria-labelledby="result-title">
    <div className="section-heading"><div><p className="eyebrow">RESULT</p>
      <h2 id="result-title">Recurring snowmelt pattern</h2></div>
      <a className="button" href={`/api${result.geotiff_url}`} download>Download GeoTIFF</a></div>
    <p>{result.name} · {result.product_label} · {result.years.join(', ')} · NDSI ≥ {result.threshold} · {result.scaling} PCA</p>
    <dl><div><dt>PC1 variance explained</dt><dd>{(result.variance_explained[0] * 100).toFixed(2)}%</dd></div>
      <div><dt>Pixels used / watershed pixels</dt><dd>{result.pixels_used.toLocaleString()} / {result.pixels_in_watershed.toLocaleString()}</dd></div></dl>
    {imageFailed ? <p role="alert">Preview unavailable. Run PCA again if the server restarted.</p> :
      <img src={`/api${result.preview_url}`} alt="PC1 pattern: darker blue indicates earlier relative melt; lighter blue indicates later relative melt."
        onError={() => setImageFailed(true)} />}
    <p className="muted">Darker = earlier melt. Lighter = later melt. Values describe relative timing, not exact dates or snow-water volume. Excluded pixels are transparent.</p>
    <p className="muted">Downloads expire when the API restarts or evicts the result. Run PCA again to regenerate them.</p>
  </section>
}

function AnalysisForm({ watershed, product }: { watershed: string; product: Product }) {
  const [availability, setAvailability] = useState<{ threshold: number; years: number[] }[]>([])
  const [loading, setLoading] = useState(true)
  const [threshold, setThreshold] = useState(10)
  const [years, setYears] = useState<number[]>([])
  const [scaling, setScaling] = useState<Scaling>('covariance')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<PCAResult | null>(null)
  const activeRun = useRef<AbortController | null>(null)
  const availableYears = availability.find(item => item.threshold === threshold)?.years ?? []

  useEffect(() => {
    const controller = new AbortController()
    getAvailability(watershed, product.key, controller.signal).then(items => {
      if (controller.signal.aborted) return
      setAvailability(items)
      setThreshold(items[0]?.threshold ?? 10)
      setYears(items[0]?.years ?? [])
    }).catch(err => {
      if (!controller.signal.aborted) setError(err.message)
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false)
    })
    return () => { controller.abort(); activeRun.current?.abort() }
  }, [watershed, product.key])

  function changeThreshold(value: number) {
    setThreshold(value)
    setYears(availability.find(item => item.threshold === value)?.years ?? [])
    setResult(null)
  }

  function toggleYear(year: number) {
    setYears(current => current.includes(year) ? current.filter(item => item !== year) : [...current, year].sort())
    setResult(null)
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (years.length < 2 || busy) return
    const controller = new AbortController()
    activeRun.current = controller
    setBusy(true); setError(''); setResult(null)
    try {
      const response = await runPCA(watershed, years, threshold, scaling, product.key, controller.signal)
      if (!controller.signal.aborted) setResult(response)
    } catch (err) {
      if (!controller.signal.aborted) setError(err instanceof Error ? err.message : 'PCA failed.')
    } finally {
      if (!controller.signal.aborted) setBusy(false)
    }
  }

  return <>
    <form onSubmit={submit}>
      <fieldset disabled={loading || busy || availability.length === 0}>
        <legend>Analysis settings</legend>
        <div className="settings"><label>NDSI threshold<select value={threshold} onChange={e => changeThreshold(Number(e.target.value))}>
          {availability.map(item => <option key={item.threshold} value={item.threshold}>{item.threshold}</option>)}
        </select></label>
        <label>PCA scaling<select value={scaling} onChange={e => { setScaling(e.target.value as Scaling); setResult(null) }}>
          <option value="covariance">Covariance (default)</option><option value="correlation">Correlation</option>
        </select></label></div>
        <p className="muted">Covariance centers each year; correlation also rescales it. The project's scaling convention remains unresolved.</p>
        <p id="year-help">Select at least two years. Only stored years covering the whole watershed are shown.</p>
        <div className="years" aria-describedby="year-help">{availableYears.map(year =>
          <label key={year}><input type="checkbox" checked={years.includes(year)} onChange={() => toggleYear(year)} />{year}</label>)}</div>
        <button type="submit" disabled={years.length < 2 || busy}>{busy ? 'Running PCA…' : 'Run PCA'}</button>
      </fieldset>
      {loading && <p role="status">Loading available data…</p>}
      {!loading && !error && availability.length === 0 && <p role="status">No stored {product.sensor} years ({product.key}) found at thresholds 10–50. {product.sensor} data starts in {product.first_year}. Precompute it with the API's jobs (e.g. <code>--product {product.key}</code>), restart the API, then refresh this page.</p>}
      {busy && <p role="status">Computing the pattern from stored annual melt dates…</p>}
      {error && <p className="error" role="alert">{error}</p>}
    </form>
    {result && <Results key={result.result_id} result={result} />}
  </>
}

function ProductPicker({ label, products, value, onChange }: {
  label: string; products: Product[]; value: string; onChange: (key: string) => void
}) {
  return <label>{label}<select value={value} onChange={e => onChange(e.target.value)}>
    {products.map(p => <option key={p.key} value={p.key}>{p.label} · from {p.first_year}</option>)}
  </select></label>
}

function Panel({ watershed, product, title }: { watershed: string; product: Product; title?: string }) {
  return <div className="panel">
    {title && <div className="section-heading"><h3>{title}</h3><span className="badge">{product.sensor} · {Math.round(product.pixel_size_m)} m</span></div>}
    <AnalysisForm key={`${watershed}|${product.key}`} watershed={watershed} product={product} />
  </div>
}

export default function App() {
  const [watersheds, setWatersheds] = useState<Watershed[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [selected, setSelected] = useState('')
  const [primary, setPrimary] = useState('')
  const [secondary, setSecondary] = useState('')
  const [compare, setCompare] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [reload, setReload] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    Promise.all([getWatersheds(controller.signal), getProducts(controller.signal)]).then(([sheds, prods]) => {
      if (controller.signal.aborted) return
      setWatersheds(sheds); setSelected(sheds[0]?.id ?? '')
      setProducts(prods)
      const first = prods.find(p => p.default) ?? prods[0]
      setPrimary(first?.key ?? '')
      // Default comparison: the first product from the other sensor (MODIS vs VIIRS, D03).
      setSecondary((prods.find(p => p.sensor !== first?.sensor) ?? prods[1] ?? first)?.key ?? '')
    }).catch(err => { if (!controller.signal.aborted) setError(err.message) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [reload])
  const primaryProduct = products.find(p => p.key === primary)
  const secondaryProduct = products.find(p => p.key === secondary)
  return <main className={compare ? 'wide' : undefined}>
    <header><p className="eyebrow">UNIVERSITY OF IDAHO · PROJECT 51</p><h1>Snow visualization</h1>
      <p>Explore recurring snowmelt patterns from stored satellite observations.</p></header>
    <section className="card" aria-label="Dataset selection"><div className="section-heading"><h2>Choose your data</h2><span className="badge">MODIS · VIIRS</span></div>
      <p className="muted">Uses precomputed gap-filled snow cover (MOD10A1F, VNP10A1F, VJ110A1F). Sensors are processed separately; compare them side by side. Downloading new data from this page is not available yet.</p>
      {loading ? <p role="status">Connecting to the API…</p> : error ? <div role="alert"><p className="error">{error}</p>
        <button onClick={() => { setError(''); setLoading(true); setReload(value => value + 1) }}>Retry connection</button></div> :
        watersheds.length === 0 ? <p>No watershed boundaries are configured in the API.</p> : <>
          <div className="settings">
            <label>Watershed<select value={selected} onChange={e => setSelected(e.target.value)}>
              {watersheds.map(item => <option key={item.id} value={item.id}>{item.name ?? item.id} · {item.huc8}</option>)}
            </select></label>
            <ProductPicker label={compare ? 'Left sensor' : 'Sensor'} products={products} value={primary} onChange={setPrimary} />
          </div>
          <label className="toggle"><input type="checkbox" checked={compare} onChange={e => setCompare(e.target.checked)} />
            Compare two sensors side by side</label>
          {compare && <div className="settings"><span />
            <ProductPicker label="Right sensor" products={products} value={secondary} onChange={setSecondary} /></div>}
          {compare && <p className="muted">Each map is computed from its own sensor's pixels and years; they are shown together for visual comparison, not matched pixel for pixel.</p>}
          {primaryProduct && (compare && secondaryProduct ?
            <div className="compare">
              <Panel watershed={selected} product={primaryProduct} title={primaryProduct.label} />
              <Panel watershed={selected} product={secondaryProduct} title={secondaryProduct.label} />
            </div> :
            <Panel watershed={selected} product={primaryProduct} />)}
        </>}
    </section>
  </main>
}
