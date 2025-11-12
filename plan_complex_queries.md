# Implementation Plan for Complex Queries

**AIM:** Enable fast UI-based composing of complex queries for wastewater viral variant detection

## Objectives
- Add large lists of mutations and deletions into one query filter
- Get proportion, coverage and count - same metrics as other plots
- Visualize mutation proportions over time with lineplot

## Implementation Notes
- **Nucleotide mutations only** for now (simplicity)
- Focus on **proportion visualization** (not heatmap for this prototype)

## API Strategy: Using `/sample/aggregated`

### Key Insight
The `/component/nucleotideMutationsOverTime` endpoint uses `includeMutations` to specify which mutations to track in the response, NOT as filters. To filter by mutations, we need `nucleotideMutations` in the query filters.

### Correct Approach: Two Requests Per Date

For each date/date-range, make **two requests** to `/sample/aggregated`:

1. **Coverage request** (no mutation filters):
   - Get total read count at location for the date range
   - This is the denominator for proportion calculation

2. **Filtered request** (with mutation filters):
   - Add `nucleotideMutations` parameter with user's mutation list
   - Get count of reads matching ALL specified mutations
   - This is the numerator for proportion calculation

**Proportion = Filtered Count / Coverage Count**

### Example API Request

```bash
curl -X 'GET' \
  'https://lapis.wasap.genspectrum.org/sample/aggregated' \
  -H 'accept: application/json' \
  -d '{
    "locationName": "Zürich (ZH)",
    "samplingDateFrom": "2024-10-01",
    "samplingDateTo": "2024-10-31",
    "nucleotideMutations": ["C43T", "G96A", "456-"],
    "fields": ["samplingDate"]
  }'
```

### Implementation Steps

1. **Parse user input**: Comma-separated mutations (validate format)
2. **Generate date list**: Based on interval (daily/weekly/monthly)
3. **For each date**:
   - Request A: `sample/aggregated` with location + date → total coverage
   - Request B: `sample/aggregated` with location + date + `nucleotideMutations` → filtered count
   - Calculate proportion = count / coverage
4. **Build DataFrame**: MultiIndex (mutation_set, samplingDate) with count, coverage, frequency
5. **Visualize**: Lineplot with optional rolling mean smoothing

## API Parameters

### Filters to use:
- `locationName`: Selected location (required)
- `samplingDateFrom` / `samplingDateTo`: Date range
- `nucleotideMutations`: User's mutation list (array of strings)
- `fields`: `["samplingDate"]` to group by date

### Mutation Format
Users can specify mutations in free text form, comma-separated:
- `C43T` - reference C at position 43, mutated to T
- `43T` - equivalent to above (reference optional)
- `43-` - deletion at position 43
- `43N` - unknown base at position 43
- `43.` - reference base (not mutated)
- `43` - any mutation at position 43

See: [CoV-Spectrum mutation format docs](https://cov-spectrum.org/about#faq-search-variants)

## Data Flow

```
User Input (mutations) 
  → Parse & Validate
  → Generate date ranges (daily/weekly/monthly)
  → For each date:
      → Fetch coverage (no filters)
      → Fetch count (with nucleotideMutations filter)
      → Calculate proportion
  → Build DataFrame
  → Apply optional rolling mean
  → Visualize lineplot
```

## Notes
- This differs from existing `mutations_over_time` which tracks individual mutations separately
- Here we track a **mutation set** (all mutations together as AND filter)
- Proportion represents: "what fraction of reads have ALL these mutations?"


