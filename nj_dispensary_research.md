# New Jersey Dispensary Research

## Market Overview
- **326 licensed dispensaries** in NJ (as of 2025)
  - 220 recreational-only
  - 56 medical-only
  - 50 hybrid (both)
  - 60 offer delivery

## Provider Distribution (Based on Research)

### Dutchie
Major MSOs using Dutchie for online ordering:
- **Curaleaf NJ** (3 locations)
  - Bordentown: dutchie.com/dispensary/curaleaf-nj-bordentown
  - Bellmawr
  - Edgewater Park
- **Ascend NJ** (3 locations)
  - Fort Lee: dutchie.com/dispensary/fort-lee-new-jersey
  - Rochelle Park
  - Wharton

### Sweed (Our existing provider!)
- **Zen Leaf NJ** (4 locations) - Uses SweedPOS
  - Neptune: zenleafdispensaries.com/locations/neptune/menu/recreational
  - Lawrence Township
  - Elizabeth
  - Mount Holly

### Jane/iHeartJane
- **The Botanist** (3 locations)
  - Egg Harbor Township
  - Collingswood
  - Williamstown
- **RISE Dispensaries** (3+ locations)
  - Bloomfield
  - Paterson
  - Paramus

### Unknown/Custom Backend
- **Breakwater** - Uses Squarespace with custom ordering system

## Recommended Approach for NJ Scraping

### Phase 1: Sweed Stores (Immediate - we already have the provider)
Zen Leaf NJ locations can be scraped using our existing Sweed provider:
1. Run discovery on Zen Leaf NJ URLs to get store IDs
2. Use sweed_api.py to scrape products

### Phase 2: Dutchie Stores
Curaleaf and Ascend use Dutchie:
1. Run discovery on their menu URLs
2. Use dutchie_provider.py to scrape via GraphQL

### Phase 3: Jane Stores
The Botanist and RISE use iHeartJane:
1. Run discovery to get Jane store IDs
2. Use jane_provider.py to scrape products

## NJ Discovery URLs to Test

```
# Sweed (Zen Leaf)
https://zenleafdispensaries.com/locations/neptune/menu/recreational
https://zenleafdispensaries.com/locations/lawrence/menu/recreational
https://zenleafdispensaries.com/locations/elizabeth/menu/recreational
https://zenleafdispensaries.com/locations/mt-holly/menu

# Dutchie (Curaleaf)
https://curaleaf.com/shop/new-jersey/curaleaf-nj-bordentown/menu
https://curaleaf.com/shop/new-jersey/curaleaf-nj-bellmawr/menu
https://curaleaf.com/shop/new-jersey/curaleaf-nj-edgewater-park/menu

# Dutchie (Ascend)
https://letsascend.com/menu/nj-fort-lee-menu/
https://letsascend.com/menu/nj-rochelle-park-menu/
https://letsascend.com/menu/nj-wharton-menu/

# Jane (The Botanist)
https://shopbotanist.com/locations/egg-harbor-township-dispensary/shop-adult-use/
https://shopbotanist.com/locations/collingswood-dispensary/
https://shopbotanist.com/locations/williamstown-dispensary/shop-adult-use/

# Jane (RISE)
https://risecannabis.com/dispensaries/new-jersey/paterson/
https://risecannabis.com/dispensaries/new-jersey/bloomfield/
```

## Data Sources
- Official NJ CRC: nj.gov/cannabis/dispensaries/find/
- NJ Open Data: data.nj.gov/Reference-Data/New-Jersey-Cannabis-Dispensary-Locations/uyq5-2c2g
- Leafly: leafly.com/dispensaries/new-jersey
- Weedmaps: weedmaps.com/dispensaries/in/united-states/new-jersey

## Next Steps
1. Create nj_discovery_urls.txt with URLs above
2. Run discover_sweed.py on Zen Leaf URLs first (fastest path)
3. Add discovered stores to dispensary table with state='NJ'
4. Run scraper on new stores
