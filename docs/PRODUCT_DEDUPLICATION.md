# Product Deduplication Guide

## Overview

Product deduplication is critical for accurate analytics. This guide explains how to identify and handle duplicate products in the CannLinx database.

## Key Principle: Sizes Are Different Products

**Different sizes = Different SKUs = NOT duplicates**

Each unit size represents a distinct product that should be tracked separately.

### Examples

| Product Names | Same Product? | Reason |
|--------------|---------------|--------|
| "Blue Dream" and "Blue Dream 3.5g" | **YES** - Duplicate | Same product, size just in name |
| "Blue Dream 3.5g" and "Blue Dream 7g" | **NO** - Different SKUs | Different sizes |
| "Gelato Cake" and "GELATO CAKE" | **YES** - Duplicate | Same product, different case |
| "Larry Bird 1/8" and "Larry Bird 3.5g" | **YES** - Duplicate | Same size (1/8 = 3.5g) |

## Common Naming Patterns

Products typically appear in these formats:

```
1. Base name only:              "Blue Dream"
2. Brand + Name:                "Curio Blue Dream"
3. Name + Size:                 "Blue Dream 3.5g"
4. Name + Size in brackets:     "Blue Dream [3.5g]"
5. Full format:                 "Curio - Blue Dream - 3.5g"
6. With type suffix:            "Blue Dream - Hybrid"
```

## Size Variations to Normalize

These represent the SAME size and should be grouped:

| Format | Normalized |
|--------|------------|
| 1/8, eighth, 3.5g, 3.5 g | 3.5g |
| 1/4, quarter, 7g, 7 g | 7g |
| 1/2, half, 14g, 14 g | 14g |
| 1oz, ounce, 28g | 28g |

## How Deduplication Works

### Step 1: Extract Size from Name

```python
def extract_size(name):
    # Check for gram patterns: "3.5g", "3.5 g", "3.5G"
    match = re.search(r'(\d+\.?\d*)\s*g\b', name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}g"

    # Check for fractions
    if re.search(r'1/8|eighth', name, re.IGNORECASE):
        return "3.5g"
    if re.search(r'1/4|quarter', name, re.IGNORECASE):
        return "7g"

    # Check for mg (edibles)
    match = re.search(r'(\d+)\s*mg\b', name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}mg"

    return None  # Unknown size
```

### Step 2: Clean Product Name

Remove size, brand prefix, and normalize:

```python
def clean_name(name, brand):
    n = name.lower()

    # Remove brand prefix
    if brand and n.startswith(brand.lower()):
        n = n[len(brand):].strip()

    # Remove size patterns
    n = re.sub(r'\s*[-|]?\s*\d+\.?\d*\s*(g|mg|oz)\b', '', n)
    n = re.sub(r'\s*\[\d+\.?\d*\s*(g|mg)\]', '', n)
    n = re.sub(r'\s*(1/8|1/4|1/2|eighth|quarter|half)\b', '', n)

    # Remove type suffixes
    n = re.sub(r'\s*(indica|sativa|hybrid)\s*$', '', n)

    # Normalize whitespace and punctuation
    n = re.sub(r'[^\w\s]', ' ', n)
    n = re.sub(r'\s+', ' ', n).strip()

    return n
```

### Step 3: Group by Brand + Clean Name + Size

Products are grouped by:
1. **Brand** (case-insensitive)
2. **Cleaned base name** (without size, brand, modifiers)
3. **Size** (normalized)

**Same brand + same clean name + SAME SIZE = Potential duplicate**

## Database Schema

The `canonical_name` table stores approved standard names:

```sql
CREATE TABLE canonical_name (
    id SERIAL PRIMARY KEY,
    brand VARCHAR NOT NULL,
    match_key VARCHAR NOT NULL,  -- cleaned product name
    canonical_name VARCHAR NOT NULL,  -- standard name to use
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(brand, match_key)
);
```

## Using the Naming Review Tool

1. Go to **Brands > Naming Standards** in the app
2. Select a category and brand to filter
3. Review products grouped by base name + size
4. Check the suggested canonical name
5. Click "Approve Suggested" to save

### What Makes a Good Canonical Name

1. **No brand prefix** - Brand is stored separately
2. **No size suffix** - Size is stored separately
3. **Proper case** - Title Case or Sentence case
4. **No modifiers** - No "Pre-Packaged", "Smalls", etc.
5. **Shortest clean version** - Remove redundant words

### Examples of Good Canonical Names

| Raw Names | Canonical Name |
|-----------|----------------|
| "Curio - Blue Dream - 3.5g", "Blue Dream [3.5g]" | Blue Dream |
| "LARRY BIRD MINTS - HYBRID", "Larry Bird Mints" | Larry Bird Mints |
| "Gelato Cake Pre-Packaged (3.5g)" | Gelato Cake |

## Workflow for Brands

1. **Review Naming Standards page weekly**
2. **Approve canonical names** for your products
3. **Contact dispensaries** using incorrect names
4. **Provide standardized product data** to retail partners

## Troubleshooting

### False Positives (Not Actually Duplicates)

- Different formulations (e.g., "Blue Dream" vs "Blue Dream Live Resin")
- Different product types (e.g., flower vs pre-roll)
- Limited edition variants

### Missing from Groups

- Check if brand name is spelled differently
- Check if size format is unusual
- Verify product is in database

## Contact

For questions about product deduplication, contact support@cannlinx.com
