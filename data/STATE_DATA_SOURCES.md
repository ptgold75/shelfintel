# State Cannabis License Data Sources

This document tracks the official regulatory data sources used for each state's dispensary and license data.

Last Updated: 2026-01-14

---

## California (CA)

### Regulatory Body
- **Department of Cannabis Control (DCC)**
- Website: https://www.cannabis.ca.gov/

### Data Sources
| Source | URL | Data Type | Update Frequency |
|--------|-----|-----------|------------------|
| License Search Tool | https://search.cannabis.ca.gov/ | All license types | Daily |
| License Summary Report | https://www.cannabis.ca.gov/resources/data-dashboard/license-report/ | Tableau dashboard | Weekly |
| Data Dashboard | https://www.cannabis.ca.gov/resources/data-dashboard/ | Sales, harvest, license stats | Weekly |

### Export Instructions
1. Go to https://search.cannabis.ca.gov/
2. Click "Advanced Search"
3. Filter by license type (Retailer, Cultivator, Manufacturer, etc.)
4. Click "Export" → "All Data"
5. Save CSV

### License Types
- Retailers: ~1,450 (Type 10 storefront, Type 9 delivery)
- Cultivation: ~4,700 (19 different types)
- Manufacturing: ~560 (Types 6, 7, N, P, S)
- Distribution: ~930
- Microbusiness: ~365

---

## New York (NY)

### Regulatory Body
- **Office of Cannabis Management (OCM)**
- Website: https://cannabis.ny.gov/

### Data Sources
| Source | URL | Data Type | Update Frequency |
|--------|-----|-----------|------------------|
| Dispensary Verification | https://cannabis.ny.gov/dispensary-location-verification | Licensed dispensaries | Daily |
| Open Data Portal | https://data.ny.gov/Economic-Development/Current-OCM-Licenses/jskf-tt3q | All OCM licenses | Weekly |
| Buy Legal Map | https://cannabis.ny.gov/system/files/documents/2024/08/buylegalnymapsearch.pdf | Dispensary map | Updated as needed |

### Export Instructions
1. Go to https://data.ny.gov/Economic-Development/Current-OCM-Licenses/jskf-tt3q
2. Click "Export" button
3. Select CSV format
4. Download

### License Types
- Adult-Use Retail Dispensary License: ~574
- Adult-Use Conditional Retail Dispensary License: ~325
- Conditional Adult-Use Retail Dispensary License: ~113
- Adult-Use Registered Organization Dispensary License: ~14
- Medical Dispensary (RO): ~34
- Cultivation, Processing, Distribution licenses also available

### Notes
- All provisional CAURD licenses extended through December 31, 2026
- As of January 2026: 790 active retail dispensary licenses
- Total OCM licenses: 2,675

---

## New Jersey (NJ)

### Regulatory Body
- **Cannabis Regulatory Commission (CRC)**
- Website: https://www.nj.gov/cannabis/

### Data Sources
| Source | URL | Data Type | Update Frequency |
|--------|-----|-----------|------------------|
| Dispensary Finder | https://www.nj.gov/cannabis/dispensaries/find/ | Licensed dispensaries | Daily |
| Dispensary Roll-up | https://www.nj.gov/cannabis/dispensaries/roll-up/ | Summary view | Daily |
| Open Data Portal | https://data.nj.gov/ | Various datasets | Varies |

### License Classes
- Class 1: Cultivator
- Class 2: Manufacturer
- Class 3: Wholesaler
- Class 4: Distributor
- Class 5: Retailer (~60)
- Class 6: Delivery Service

### Alternative Treatment Centers (ATCs)
- 12 original medical ATCs (vertically integrated)
- Can serve both medical and recreational

---

## Maryland (MD)

### Regulatory Body
- **Maryland Cannabis Administration (MCA)**
- Website: https://mmcc.maryland.gov/

### Data Sources
| Source | URL | Data Type | Update Frequency |
|--------|-----|-----------|------------------|
| Licensed Dispensaries | https://mmcc.maryland.gov/Pages/dispensaries.aspx | Dispensary list | Weekly |
| CannaLinx Database | Internal | Menu data, prices | Daily scrapes |

### License Types
- Dispensaries: ~100+
- Growers: ~20+
- Processors: ~20+

---

## Illinois (IL)

### Regulatory Body
- **Illinois Department of Financial and Professional Regulation (IDFPR)**
- Website: https://idfpr.illinois.gov/profs/adultusecan.asp

### Data Sources
| Source | URL | Data Type | Update Frequency |
|--------|-----|-----------|------------------|
| Licensed Dispensaries | https://idfpr.illinois.gov/LicenseLookup/AdultUseCannabis.aspx | License lookup | Daily |

---

## Pennsylvania (PA)

### Regulatory Body
- **Pennsylvania Department of Health (DOH)**
- Website: https://www.health.pa.gov/topics/programs/Medical%20Marijuana/

### Data Sources
| Source | URL | Data Type | Update Frequency |
|--------|-----|-----------|------------------|
| Dispensary List | https://www.health.pa.gov/topics/Documents/Programs/Medical%20Marijuana/DOH%20Approved%20Active%20Dispensary%20List.pdf | PDF list | Monthly |

### Notes
- Medical only (no recreational)
- Largest medical market on East Coast

---

## Massachusetts (MA)

### Regulatory Body
- **Cannabis Control Commission (CCC)**
- Website: https://masscannabiscontrol.com/

### Data Sources
| Source | URL | Data Type | Update Frequency |
|--------|-----|-----------|------------------|
| Licensing Tracker | https://masscannabiscontrol.com/licensing-tracker/ | All license types | Weekly |
| Open Data Portal | https://opendata.mass-cannabis-control.com/ | Retail sales, licenses | Monthly |
| License Documents | Per-license document downloads | Contact info, conditions | As updated |

### Export Instructions
1. Go to https://masscannabiscontrol.com/licensing-tracker/
2. Filter by license type (Marijuana Retailer, Cultivator, etc.)
3. Click on individual licenses for detailed documents
4. Documents contain email addresses and license conditions

### License Types
- Marijuana Retailer: ~300+
- Marijuana Cultivator: ~200+
- Marijuana Product Manufacturer: ~150+
- Microbusiness: ~50+

### Priority Categories
- MTC Priority: Medical Treatment Centers (first to convert to adult-use)
- Social Equity: Social equity program participants
- EEA Priority: Economic Empowerment Applicants
- General: Standard applicants

---

## Scripts

| Script | Purpose | States |
|--------|---------|--------|
| `scripts/scrape_california_licenses.py` | Import CA DCC exports | CA |
| `scripts/scrape_nj_dispensaries.py` | Import NJ dispensaries | NJ |
| `scripts/import_ny_dispensaries.py` | Import NY OCM license data | NY |
| `scripts/verify_ny_dispensaries.py` | Verify NY against OCM | NY |
| `scripts/verify_ny_smoke_shops.py` | Mark unlicensed NY as smoke shops | NY |
| `scripts/scrape_ma_licenses.py` | Import MA CCC license data | MA |
| `scripts/lookup_ca_menu_urls.py` | Find CA menu URLs | CA |
| `scripts/validate_ca_urls.py` | Validate Weedmaps URLs | CA |

---

## Database Tables

| Table | Content |
|-------|---------|
| `california_license` | CA DCC license data (7,170+ records) |
| `massachusetts_license` | MA CCC license data (74+ retailers) |
| `dispensary` | All states dispensary records |

---

## Third-Party Data Sources

| Source | URL | States | Data Type |
|--------|-----|--------|-----------|
| Weedmaps | https://weedmaps.com/dispensaries | All | Menu URLs, addresses |
| Leafly | https://www.leafly.com/dispensaries | All | Menu URLs, addresses |
| Headset | https://www.headset.io/ | Select states | Market data (paid) |
| BDSA | https://bdsa.com/ | All legal states | Market data (paid) |
