# Shelf Intelligence - Feature Requirements

## Menu Type Support (Medical vs Adult Use)

### Differences to Track
- **THC Limits**: Medical menus often allow higher THC concentrations
- **Pricing**: Medical patients may have different pricing structures
- **Product Availability**: Some products may be medical-only or adult-use-only
- **Tax Rates**: Different tax treatment (medical often tax-exempt or reduced)

### Implementation Notes
- Dutchie: Use `pricingType: "rec"` or `pricingType: "med"` parameter
- Jane/Algolia: Filter by menu type in query
- Sweed: Check for separate medical/recreational store IDs

### Data Model
Each menu item should capture:
```
- menu_type: "medical" | "recreational" | "both"
- medical_price: float (if different)
- rec_price: float
- thc_limit_medical: float
- thc_limit_rec: float
```

---

## Dashboard & Analytics Requirements

### State-Level Views
1. **Category Totals** - Pie/bar charts showing:
   - Product count by category (Flower, Vape, Edible, etc.)
   - Revenue/price distribution by category
   - Brand market share by category

2. **Geographic Filters**
   - Filter by county
   - Filter by city/region
   - Map visualization with dispensary markers

3. **Product Category Filters**
   - Flower, Pre-rolls, Vapes, Edibles, Concentrates, Tinctures, Topicals
   - Subcategory drill-down (e.g., Flower → Indica/Sativa/Hybrid)

### Location/Store Views
- Individual store snapshot
- Product mix breakdown
- Brand distribution
- Price point analysis (avg, min, max by category)
- Inventory depth (SKU count)

### Ownership Group Views
- Aggregate view across all stores in group
- Store-by-store comparison within group
- Brand preferences by group
- Pricing strategy analysis
- Category focus areas

---

## Ownership Groups - Maryland

### Multi-Store Operators (MSOs)

| Group | Locations | Store Names |
|-------|-----------|-------------|
| **Curaleaf** | 4 | Reisterstown, Montgomery Village, Columbia, Frederick |
| **Trulieve** | 2+ | Rockville (Harvest), Lutherville |
| **Verano (Zen Leaf)** | 4 | Towson, Elkridge, Pasadena, Germantown |
| **gLeaf** | 2 | Rockville, Frederick |
| **Green Thumb (RISE)** | 4 | Bethesda, Silver Spring, Joppa, Hagerstown |
| **Ascend** | 3 | Ellicott City, Laurel, Crofton |
| **Thrive** | 2 | Upper Marlboro, Annapolis |
| **Health for Life** | 2 | Baltimore, White Marsh |
| **Culta** | 3 | Urbana, + others |

### Single Location Operators
- The Dispensary MD
- Waave (Greenbelt)
- Gold Leaf (Annapolis)
- Bloom (Germantown)
- Revolution Releaf
- Ethos (Catonsville)
- Cookies (Baltimore)
- Green Goods (Baltimore)
- Verilife (Westminster)
- Mana Supply (Edgewater)

---

## Analytics Queries to Support

1. **Brand Analysis**
   - Which brands are carried by most dispensaries?
   - Brand pricing across different retailers
   - Brand category distribution

2. **Price Analysis**
   - Average price by category across state
   - Price variance by ownership group
   - Sale/discount frequency by retailer

3. **Availability Analysis**
   - Out-of-stock rates by category
   - Product turnover indicators
   - New product detection

4. **Image Consistency Report**
   - Flag products using different images across retailers
   - Identify low-quality product images
   - Track image updates over time

---

## Technical Notes

### Scraping Schedule
- Full scrape: Daily (overnight)
- Price monitoring: Every 4-6 hours
- New product detection: Daily diff analysis

### Data Retention
- Keep historical snapshots for trend analysis
- Store price history for sale pattern detection
- Track menu changes over time
