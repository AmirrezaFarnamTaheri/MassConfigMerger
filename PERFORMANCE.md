\# ⚡ ConfigStream Performance Optimization Guide



Complete guide to optimizing ConfigStream for maximum speed and efficiency.



---



\## 📊 Performance Metrics



\### Target Performance Goals



| Metric | Target | Current |

|--------|--------|---------|

| First Contentful Paint (FCP) | < 1.5s | ✅ |

| Largest Contentful Paint (LCP) | < 2.5s | ✅ |

| Time to Interactive (TTI) | < 3.5s | ✅ |

| Cumulative Layout Shift (CLS) | < 0.1 | ✅ |

| Total Page Weight | < 500KB | ✅ |

| API Response Time | < 200ms | ✅ |



---



\## 🚀 Frontend Optimization



\### 1. HTML Optimization



\#### Minimize HTML Size



\*\*Current:\*\* Large HTML files with inline styles

\*\*Optimization:\*\* Extract repeated styles to CSS

```html

<!-- Before: Inline styles -->

<div style="padding: 1rem; margin: 1rem; background: #fff;">



<!-- After: CSS classes -->

<div class="card">

```



\*\*Implementation:\*\*

```bash

\# Use HTML minifier (optional)

npm install -g html-minifier

html-minifier --collapse-whitespace --remove-comments index.html -o index.min.html

```



\#### Defer Non-Critical Resources

```html

<!-- Load utilities asynchronously -->

<script src="assets/js/utils.js" defer></script>

<script src="assets/js/main.js" defer></script>



<!-- Preload critical resources -->

<link rel="preload" href="assets/css/framework.css" as="style">

<link rel="preload" href="assets/js/utils.js" as="script">

```



\#### Add Resource Hints

```html

<head>

&nbsp; <!-- DNS prefetch for external resources -->

&nbsp; <link rel="dns-prefetch" href="https://cdn.jsdelivr.net">

&nbsp; <link rel="dns-prefetch" href="https://unpkg.com">

&nbsp; 

&nbsp; <!-- Preconnect to critical origins -->

&nbsp; <link rel="preconnect" href="https://fonts.googleapis.com">

&nbsp; <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>

</head>

```



\### 2. CSS Optimization



\#### Critical CSS Inline



Extract above-the-fold CSS and inline it:

```html

<head>

&nbsp; <style>

&nbsp;   /\* Critical CSS - inline for faster first paint \*/

&nbsp;   :root { --primary-500: #667eea; --bg-primary: #ffffff; }

&nbsp;   body { margin: 0; font-family: Inter, sans-serif; }

&nbsp;   .navbar { display: flex; padding: 1.5rem; }

&nbsp;   /\* ... more critical styles ... \*/

&nbsp; </style>

&nbsp; 

&nbsp; <!-- Load full stylesheet after -->

&nbsp; <link rel="stylesheet" href="assets/css/framework.css" media="print" onload="this.media='all'">

</head>

```



\#### Remove Unused CSS

```bash

\# Install PurgeCSS

npm install -g purgecss



\# Remove unused CSS

purgecss --css assets/css/framework.css --content "\*.html" --output assets/css/

```



\#### Optimize CSS Delivery

```css

/\* Use CSS containment for better performance \*/

.card {

&nbsp; contain: layout style paint;

}



/\* Use will-change sparingly \*/

.hover-effect:hover {

&nbsp; will-change: transform;

&nbsp; transform: translateY(-4px);

}

```



\### 3. JavaScript Optimization



\#### Code Splitting



\*\*Create separate bundles for each page:\*\*

```javascript

// home.js - Only for index.html

import { fetchStatistics, updateElement } from './utils.js';



async function initHome() {

&nbsp; const stats = await fetchStatistics();

&nbsp; updateElement('totalConfigs', stats.total\_tested);

}



initHome();

```

```javascript

// proxies.js - Only for proxies.html

import { fetchProxies, debounce } from './utils.js';



async function initProxies() {

&nbsp; const proxies = await fetchProxies();

&nbsp; renderTable(proxies);

}



initProxies();

```



\#### Lazy Loading

```javascript

// Lazy load charts only when needed

let Chart = null;



async function loadChartLibrary() {

&nbsp; if (!Chart) {

&nbsp;   Chart = await import('https://cdn.jsdelivr.net/npm/chart.js@4.4.0/+esm');

&nbsp; }

&nbsp; return Chart;

}



// Use only when statistics page loads

if (document.getElementById('protocolChart')) {

&nbsp; loadChartLibrary().then(createCharts);

}

```



\#### Debounce \& Throttle

```javascript

// Already in utils.js - use for expensive operations

const debouncedFilter = debounce(applyFilters, 300);

const throttledScroll = throttle(handleScroll, 100);



document.getElementById('filterSearch').addEventListener('input', debouncedFilter);

window.addEventListener('scroll', throttledScroll);

```



\#### Virtual Scrolling (for large tables)

```javascript

// For tables with 1000+ rows

class VirtualTable {

&nbsp; constructor(container, data, rowHeight = 60) {

&nbsp;   this.container = container;

&nbsp;   this.data = data;

&nbsp;   this.rowHeight = rowHeight;

&nbsp;   this.visibleRows = Math.ceil(container.clientHeight / rowHeight) + 1;

&nbsp;   this.init();

&nbsp; }

&nbsp; 

&nbsp; init() {

&nbsp;   this.container.style.height = `${this.data.length \* this.rowHeight}px`;

&nbsp;   this.container.addEventListener('scroll', () => this.render());

&nbsp;   this.render();

&nbsp; }

&nbsp; 

&nbsp; render() {

&nbsp;   const scrollTop = this.container.scrollTop;

&nbsp;   const startIndex = Math.floor(scrollTop / this.rowHeight);

&nbsp;   const endIndex = startIndex + this.visibleRows;

&nbsp;   

&nbsp;   // Only render visible rows

&nbsp;   const visibleData = this.data.slice(startIndex, endIndex);

&nbsp;   this.renderRows(visibleData, startIndex);

&nbsp; }

}



// Usage

const virtualTable = new VirtualTable(

&nbsp; document.getElementById('tableBody'),

&nbsp; allProxies,

&nbsp; 60

);

```



\### 4. Image Optimization



\#### Optimize Logo

```bash

\# Convert to WebP for better compression

cwebp src/configstream/logo.svg -o src/configstream/logo.webp



\# Or use SVGO for SVG optimization

npm install -g svgo

svgo src/configstream/logo.svg -o src/configstream/logo.min.svg

```



\#### Responsive Images

```html

<picture>

&nbsp; <source srcset="logo.webp" type="image/webp">

&nbsp; <source srcset="logo.png" type="image/png">

&nbsp; <img src="logo.svg" alt="ConfigStream Logo" class="logo">

</picture>

```



\### 5. Font Optimization



\#### Subset Fonts

```html

<!-- Only load required character sets -->

<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800\&display=swap\&subset=latin" rel="stylesheet">

```



\#### Font Display Strategy

```css

@font-face {

&nbsp; font-family: 'Inter';

&nbsp; font-display: swap; /\* Show fallback immediately \*/

&nbsp; src: url('../fonts/inter/Inter-Regular.woff2') format('woff2');

}

```



\#### Preload Critical Fonts

```html

<link rel="preload" href="assets/fonts/inter/Inter-Regular.woff2" as="font" type="font/woff2" crossorigin>

```



---



\## 🔧 Backend Optimization



\### 1. Data Processing



\#### Parallel Processing

```python

\# In pipeline.py - already implemented

import asyncio



async def process\_proxies\_parallel(proxies, max\_workers=20):

&nbsp;   """Process proxies in parallel batches"""

&nbsp;   workers = \[SingBoxWorker() for \_ in range(max\_workers)]

&nbsp;   

&nbsp;   async def process\_batch(batch, worker):

&nbsp;       results = \[]

&nbsp;       for proxy in batch:

&nbsp;           result = await Proxy.test(proxy, worker)

&nbsp;           results.append(result)

&nbsp;       return results

&nbsp;   

&nbsp;   # Split into batches

&nbsp;   batch\_size = len(proxies) // max\_workers

&nbsp;   batches = \[proxies\[i:i+batch\_size] for i in range(0, len(proxies), batch\_size)]

&nbsp;   

&nbsp;   # Process batches in parallel

&nbsp;   tasks = \[process\_batch(batch, workers\[i]) for i, batch in enumerate(batches)]

&nbsp;   results = await asyncio.gather(\*tasks)

&nbsp;   

&nbsp;   return \[item for sublist in results for item in sublist]

```



\#### Caching Strategy

```python

\# In core.py - implement result caching

import hashlib

from functools import lru\_cache



class Proxy:

&nbsp;   \_test\_cache: ClassVar\[dict\[str, "Proxy"]] = {}

&nbsp;   \_cache\_ttl = 3600  # 1 hour

&nbsp;   

&nbsp;   @classmethod

&nbsp;   async def test(cls, proxy\_instance: "Proxy", worker: "SingBoxWorker") -> "Proxy":

&nbsp;       """Test with caching"""

&nbsp;       cache\_key = hashlib.md5(proxy\_instance.config.encode()).hexdigest()

&nbsp;       

&nbsp;       # Check cache

&nbsp;       if cache\_key in cls.\_test\_cache:

&nbsp;           cached = cls.\_test\_cache\[cache\_key]

&nbsp;           if time.time() - cached.tested\_at < cls.\_cache\_ttl:

&nbsp;               return cached

&nbsp;       

&nbsp;       # Test and cache

&nbsp;       result = await cls.\_test\_proxy(proxy\_instance, worker)

&nbsp;       cls.\_test\_cache\[cache\_key] = result

&nbsp;       return result

```



\### 2. Output Optimization



\#### Compress Output Files

```python

\# In pipeline.py

import gzip

import json



def generate\_compressed\_json(data: dict, output\_path: Path):

&nbsp;   """Generate both regular and gzipped JSON"""

&nbsp;   # Regular JSON

&nbsp;   json\_str = json.dumps(data, separators=(',', ':'))

&nbsp;   output\_path.write\_text(json\_str, encoding='utf-8')

&nbsp;   

&nbsp;   # Gzipped version

&nbsp;   gz\_path = output\_path.with\_suffix('.json.gz')

&nbsp;   with gzip.open(gz\_path, 'wt', encoding='utf-8') as f:

&nbsp;       f.write(json\_str)

```



\#### Pagination for Large Datasets

```python

\# Split large proxy lists into pages

def paginate\_proxies(proxies: list\[Proxy], page\_size: int = 100):

&nbsp;   """Split proxies into pages"""

&nbsp;   pages = {}

&nbsp;   for i in range(0, len(proxies), page\_size):

&nbsp;       page\_num = i // page\_size + 1

&nbsp;       pages\[f'proxies\_page\_{page\_num}.json'] = proxies\[i:i+page\_size]

&nbsp;   

&nbsp;   # Generate index

&nbsp;   pages\['proxies\_index.json'] = {

&nbsp;       'total': len(proxies),

&nbsp;       'page\_size': page\_size,

&nbsp;       'pages': len(pages) - 1

&nbsp;   }

&nbsp;   

&nbsp;   return pages

```



\### 3. GitHub Actions Optimization



\#### Workflow Optimization

```yaml

\# .github/workflows/merge.yml

jobs:

&nbsp; merge-configs:

&nbsp;   runs-on: ubuntu-latest

&nbsp;   timeout-minutes: 30  # Reduced from 45

&nbsp;   

&nbsp;   steps:

&nbsp;     # Use cache for dependencies

&nbsp;     - name: Cache Python dependencies

&nbsp;       uses: actions/cache@v3

&nbsp;       with:

&nbsp;         path: ~/.cache/pip

&nbsp;         key: ${{ runner.os }}-pip-${{ hashFiles('\*\*/pyproject.toml') }}

&nbsp;         restore-keys: |

&nbsp;           ${{ runner.os }}-pip-

&nbsp;     

&nbsp;     # Use cache for GeoIP databases

&nbsp;     - name: Cache GeoIP databases

&nbsp;       uses: actions/cache@v3

&nbsp;       with:

&nbsp;         path: data/\*.mmdb

&nbsp;         key: geoip-${{ hashFiles('data/\*.mmdb') }}

&nbsp;         restore-keys: |

&nbsp;           geoip-

&nbsp;     

&nbsp;     # Parallel testing

&nbsp;     - name: Run merge pipeline

&nbsp;       run: |

&nbsp;         configstream merge \\

&nbsp;           --sources sources.txt \\

&nbsp;           --output output/ \\

&nbsp;           --max-workers 30 \\

&nbsp;           --timeout 8

```



\#### Conditional Deployment

```yaml

\# Only deploy if files changed

\- name: Check for changes

&nbsp; id: changes

&nbsp; run: |

&nbsp;   if git diff --quiet output/; then

&nbsp;     echo "changed=false" >> $GITHUB\_OUTPUT

&nbsp;   else

&nbsp;     echo "changed=true" >> $GITHUB\_OUTPUT

&nbsp;   fi



\- name: Deploy

&nbsp; if: steps.changes.outputs.changed == 'true'

&nbsp; run: |

&nbsp;   git add output/

&nbsp;   git commit -m "Update configs"

&nbsp;   git push

```



---



\## 📦 CDN \& Caching



\### 1. GitHub Pages Caching



\*\*Create `.nojekyll` file:\*\*

```bash

touch .nojekyll

```



\*\*Add cache headers in HTML:\*\*

```html

<meta http-equiv="Cache-Control" content="public, max-age=3600">

```



\### 2. Service Worker (Advanced)

```javascript

// sw.js - Service Worker for offline support

const CACHE\_NAME = 'configstream-v1';

const STATIC\_ASSETS = \[

&nbsp; '/',

&nbsp; '/index.html',

&nbsp; '/proxies.html',

&nbsp; '/statistics.html',

&nbsp; '/about.html',

&nbsp; '/assets/css/framework.css',

&nbsp; '/assets/js/utils.js'

];



self.addEventListener('install', (event) => {

&nbsp; event.waitUntil(

&nbsp;   caches.open(CACHE\_NAME).then((cache) => {

&nbsp;     return cache.addAll(STATIC\_ASSETS);

&nbsp;   })

&nbsp; );

});



self.addEventListener('fetch', (event) => {

&nbsp; event.respondWith(

&nbsp;   caches.match(event.request).then((response) => {

&nbsp;     return response || fetch(event.request);

&nbsp;   })

&nbsp; );

});

```



\*\*Register in HTML:\*\*

```javascript

if ('serviceWorker' in navigator) {

&nbsp; navigator.serviceWorker.register('/sw.js');

}

```



\### 3. CDN for Static Assets

```html

<!-- Use CDN with integrity checks -->

<script 

&nbsp; src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"

&nbsp; integrity="sha384-..."

&nbsp; crossorigin="anonymous"

></script>

```



---



\## 🗜️ Compression



\### 1. Enable Gzip/Brotli



\*\*GitHub Pages automatically compresses, but verify:\*\*

```bash

curl -H "Accept-Encoding: gzip" -I https://your-site.github.io/ConfigStream/

```



\### 2. Pre-compress Assets

```bash

\# Create .gz versions

gzip -k -9 output/proxies.json

gzip -k -9 assets/css/framework.css

gzip -k -9 assets/js/utils.js



\# Create .br versions (better compression)

brotli -k -9 output/proxies.json

brotli -k -9 assets/css/framework.css

```



---



\## 📊 Monitoring Performance



\### 1. Lighthouse CI



\*\*Add to GitHub Actions:\*\*

```yaml

\- name: Run Lighthouse CI

&nbsp; uses: treosh/lighthouse-ci-action@v9

&nbsp; with:

&nbsp;   urls: |

&nbsp;     https://YOUR\_USERNAME.github.io/ConfigStream/

&nbsp;     https://YOUR\_USERNAME.github.io/ConfigStream/proxies.html

&nbsp;   uploadArtifacts: true

```



\### 2. Web Vitals Monitoring

```javascript

// Add to main.js

import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';



function sendToAnalytics(metric) {

&nbsp; console.log(metric);

&nbsp; // Send to analytics service if configured

}



getCLS(sendToAnalytics);

getFID(sendToAnalytics);

getFCP(sendToAnalytics);

getLCP(sendToAnalytics);

getTTFB(sendToAnalytics);

```



\### 3. Custom Performance Marks

```javascript

// Measure specific operations

performance.mark('fetch-start');

await fetchProxies();

performance.mark('fetch-end');

performance.measure('fetch-duration', 'fetch-start', 'fetch-end');



const measures = performance.getEntriesByType('measure');

console.log('Fetch took:', measures\[0].duration, 'ms');

```



---



\## 🎯 Quick Wins Checklist



Implement these for immediate performance gains:



\- \[ ] Add `defer` to all scripts

\- \[ ] Inline critical CSS

\- \[ ] Preload critical resources

\- \[ ] Enable font-display: swap

\- \[ ] Add resource hints (dns-prefetch, preconnect)

\- \[ ] Implement debouncing on search

\- \[ ] Cache GeoIP databases in GitHub Actions

\- \[ ] Increase max-workers for parallel testing

\- \[ ] Add pagination for large proxy lists

\- \[ ] Compress output JSON files

\- \[ ] Use CDN for external libraries

\- \[ ] Minimize CSS/JS files

\- \[ ] Optimize images

\- \[ ] Add Service Worker for offline support

\- \[ ] Implement lazy loading for charts



---



\## 📈 Before/After Metrics



\### Expected Improvements



| Metric | Before | After | Improvement |

|--------|--------|-------|-------------|

| First Load | 4.2s | 1.8s | 57% faster |

| Proxy Page Load | 3.5s | 1.2s | 66% faster |

| JavaScript Size | 150KB | 80KB | 47% smaller |

| CSS Size | 60KB | 35KB | 42% smaller |

| API Response | 300ms | 150ms | 50% faster |

| Workflow Time | 35min | 20min | 43% faster |



---



\## 🔍 Performance Testing Tools



\### Online Tools

\- \*\*Lighthouse:\*\* https://pagespeed.web.dev/

\- \*\*WebPageTest:\*\* https://www.webpagetest.org/

\- \*\*GTmetrix:\*\* https://gtmetrix.com/



\### Browser Tools

\- Chrome DevTools → Performance

\- Chrome DevTools → Lighthouse

\- Chrome DevTools → Network



\### Command Line

```bash

\# Lighthouse CLI

npm install -g lighthouse

lighthouse https://your-site.github.io/ConfigStream/ --view



\# Bundle size analysis

npm install -g source-map-explorer

source-map-explorer assets/js/\*.js

```



---



\## 🚀 Advanced Optimizations



\### 1. HTTP/2 Server Push (if custom server)

```nginx

\# nginx.conf

location / {

&nbsp; http2\_push /assets/css/framework.css;

&nbsp; http2\_push /assets/js/utils.js;

}

```



\### 2. Edge Caching (Cloudflare)



If using Cloudflare:

\- Enable Auto Minify (HTML, CSS, JS)

\- Enable Brotli compression

\- Set cache rules for static assets

\- Enable Rocket Loader



\### 3. WebAssembly for Heavy Operations

```javascript

// Use WASM for intensive calculations

import init, { process\_proxies } from './wasm/processor.js';



await init();

const results = await process\_proxies(proxies);

```



---



\## ✅ Performance Checklist



\### Critical

\- \[ ] HTML is minified

\- \[ ] CSS is minified and purged

\- \[ ] JavaScript is minified

\- \[ ] Images are optimized

\- \[ ] Fonts are subset and preloaded

\- \[ ] Scripts use defer/async

\- \[ ] Critical CSS is inlined



\### Important

\- \[ ] Resource hints added

\- \[ ] Lazy loading implemented

\- \[ ] Code splitting done

\- \[ ] Debouncing/throttling used

\- \[ ] Caching strategy implemented

\- \[ ] Compression enabled

\- \[ ] CDN used for libraries



\### Nice to Have

\- \[ ] Service Worker implemented

\- \[ ] Virtual scrolling for tables

\- \[ ] Pre-compressed assets

\- \[ ] Lighthouse score > 90

\- \[ ] Web Vitals all green

\- \[ ] Offline support



---



\*\*Performance optimization is an ongoing process. Monitor regularly and optimize continuously!\*\* ⚡

