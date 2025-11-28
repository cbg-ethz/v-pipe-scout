# Implementation Plan: Advanced Queries Migration

**AIM:** Migrate to LAPIS advanced query syntax for flexible mutation filtering in wastewater viral variant detection

## Background: Advanced Query Syntax

LAPIS now supports advanced query filters via the `advancedQuery` parameter, enabling complex logical operations.

📚 **Official Documentation:** [LAPIS Advanced Query Syntax](https://lapis.cov-spectrum.org/advanced-queries/)

### Example Advanced Query (URL-encoded)
```bash
curl -X 'GET' \
  'https://lapis.wasap.genspectrum.org/sample/aggregated?advancedQuery=%5B3-of%3A%2023149T%2C%2023224T%2C%2023311T%2C%2023403G%2C%2023436G%5D&limit=100&dataFormat=JSON&downloadAsFile=false' \
  -H 'accept: application/json'
```

### Query Syntax Examples

**1. Boolean Logic (AND, OR, NOT)**
```
300G & !400- & (S:123T | S:234A)
```
- Nucleotide mutation 300G 
- WITHOUT deletion at position 400
- EITHER AA change S:123T OR S:234A

**Operator Aliases:**
- `&` or `AND` → logical AND
- `|` or `OR` → logical OR
- `!` or `NOT` → logical NOT
- Parentheses `( )` define operation order

**2. N-of Filtering**
```
[3-of: 123A, 234T, S:345-, ORF1a:456K, ORF7:567-]
```
- At least 3 out of 5 specified mutations (minimum threshold)

**3. Exactly-N-of Filtering**
```
[exactly-2-of: 123A & 234T, !234T, S:345- | S:346-, [2-of: 222T, 333G, 444A, 555C]]
```
- Exactly 2 out of 4 complex conditions must be met (exact match)

### Mutation Format (same as before)
- `300G` or `A300G` - nucleotide mutation
- `400-` - deletion
- `S:123T` - amino acid mutation
- `ORF1a:456K` - gene-specific mutation
- See [CoV-Spectrum documentation](https://cov-spectrum.org/about#faq-search-variants)

---

## Staged Implementation Plan

### **Stage 1: API Migration & Validation** 
**Goal:** Replace `nucleotideMutations` array parameter with `advancedQuery` string parameter, verify identical results

#### Tasks:
1. **Update API layer** (`app/api/wiseloculus.py`):
   - [ ] Replace `nucleotideMutations` parameter with `advancedQuery` in `coocurrences_over_time()` method
   - [ ] Convert mutation list to simple AND query: `123A & 234T & 345-`
   - [ ] Update `/sample/aggregated` POST requests to use `advancedQuery` field
   - [ ] Keep coverage calculation logic unchanged (no advanced query for coverage)

2. **Update tests** (`app/tests/test_wiseloculus.py`):
   - [ ] Add test for advanced query formatting (list → AND string)
   - [ ] Verify results match old `nucleotideMutations` approach
   - [ ] Test edge cases: single mutation, empty list, special characters

3. **Validation**:
   - [ ] Run existing co-occurrences page with same inputs
   - [ ] Compare results before/after migration
   - [ ] Verify URL encoding works correctly
   - [ ] Test with real LAPIS server

#### Expected Changes:
- **From:** `"nucleotideMutations": ["23149T", "23224T", "23311T"]`
- **To:** `"advancedQuery": "23149T & 23224T & 23311T"`

#### Files Modified:
- `app/api/wiseloculus.py` (coocurrences_over_time method)
- `app/tests/test_wiseloculus.py` (add advanced query tests)

---

### **Stage 2: UI Redesign - Heatmap Visualization**
**Goal:** Replace per-location timeseries with single heatmap (locations × dates)

#### Tasks:
1. **Remove per-location lineplots** (`app/subpages/coocurrences.py`):
   - [ ] Remove loop that renders separate plots per location
   - [ ] Consolidate all location data into single DataFrame
   - [ ] Format: MultiIndex rows (locations), columns (dates), values (frequencies)

2. **Create heatmap visualization** (`app/visualize/mutations.py` or new file):
   - [ ] New function: `proportions_heatmap(freq_df, counts_df, coverage_df, title)`
   - [ ] Y-axis: Location names
   - [ ] X-axis: Sampling dates
   - [ ] Color scale: Frequency (0-1 or 0-100%)
   - [ ] Hover info: Count, coverage, frequency
   - [ ] Similar styling to existing heatmaps in codebase

3. **Update UI layout** (`app/subpages/coocurrences.py`):
   - [ ] Keep mutation input, date range, interval selectors
   - [ ] Keep multi-location selector (still use "All locations" option)
   - [ ] Replace multiple lineplots with single heatmap
   - [ ] Add optional "Show raw data" expander with combined DataFrame

4. **Testing**:
   - [ ] Test with single location (should show 1-row heatmap)
   - [ ] Test with multiple locations
   - [ ] Test with "All locations"
   - [ ] Verify hover tooltips show correct data

#### Expected Visualization:
```
              2024-01-01  2024-01-02  2024-01-03  ...
Zürich (ZH)      0.23        0.25        0.22     ...
Basel (BS)       0.15        0.18        0.16     ...
Bern (BE)        0.31        0.29        0.33     ...
```

#### Files Modified:
- `app/subpages/coocurrences.py` (remove loop, add heatmap)
- `app/visualize/mutations.py` (add proportions_heatmap function)
- `app/tests/test_*.py` (update tests for new visualization)

---

### **Stage 3: Advanced Query UI - User Input**
**Goal:** Enable users to write custom advanced queries with full syntax support

#### Tasks:
1. **Add query mode toggle** (`app/subpages/coocurrences.py`):
   - [ ] Radio button: "Simple (comma-separated)" vs "Advanced (query syntax)"
   - [ ] Default to "Simple" for backward compatibility
   - [ ] Save mode selection in URL state

2. **Simple mode (existing behavior)**:
   - [ ] Text area for comma-separated mutations
   - [ ] Convert to AND query: `123A, 234T, 345-` → `123A & 234T & 345-`
   - [ ] Keep validation logic

3. **Advanced mode (new feature)**:
   - [ ] Larger text area for advanced query string
   - [ ] Syntax highlighting/validation (optional, nice-to-have)
   - [ ] Pass query string directly to API (no conversion)
   - [ ] Examples dropdown with pre-built queries

4. **Documentation & Examples** (`app/subpages/coocurrences.py`):
   - [ ] Add expandable "Query Syntax Guide" section with:
     - **Boolean operators:** `&`/`AND` (and), `|`/`OR` (or), `!`/`NOT` (not)
     - **N-of syntax:** `[3-of: mut1, mut2, mut3, mut4, mut5]` (at least N)
     - **Exact-N-of:** `[exactly-2-of: cond1, cond2, cond3]` (exactly N)
     - **Grouping:** Parentheses `(A | B) & C` define operation order
     - **Mutation formats:** nucleotide, amino acid, deletions
     - **Link:** [Advanced Query Docs](https://lapis.cov-spectrum.org/advanced-queries/)
   - [ ] Pre-built example queries:
     - "At least 3 of 5 XBB mutations"
     - "Omicron signature OR Delta signature"
     - "Spike mutation without ORF1a mutation"
     - "Exactly 2 out of 3 deletions"

5. **API Integration**:
   - [ ] Simple mode: convert list → AND query (Stage 1 logic)
   - [ ] Advanced mode: pass query string directly to `advancedQuery` parameter
   - [ ] Add query validation/error handling from API responses

6. **Testing**:
   - [ ] Test simple mode maintains backward compatibility
   - [ ] Test advanced mode with all syntax examples
   - [ ] Test invalid queries show meaningful errors
   - [ ] Test URL state preservation for both modes

#### Example UI Layout:
```
┌─────────────────────────────────────────────────┐
│ Query Mode: ○ Simple   ● Advanced               │
├─────────────────────────────────────────────────┤
│ Advanced Query:                                 │
│ ┌─────────────────────────────────────────────┐ │
│ │ [3-of: 23149T, 23224T, 23311T, 23403G,     │ │
│ │        23436G]                              │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ [▼] Query Syntax Guide                          │
│ [▼] Example Queries                             │
└─────────────────────────────────────────────────┘
```

#### Files Modified:
- `app/subpages/coocurrences.py` (add mode toggle, advanced input, examples)
- `app/api/wiseloculus.py` (handle both simple and advanced queries)
- `app/tests/test_wiseloculus.py` (test both query modes)

---

## Implementation Order

1. **Week 1**: Stage 1 - API Migration
   - Migrate to advancedQuery parameter
   - Validate identical results
   - Update tests

2. **Week 2**: Stage 2 - Heatmap Visualization  
   - Build heatmap visualization function
   - Update UI to use heatmap instead of lineplots
   - Test with multiple locations

3. **Week 3**: Stage 3 - Advanced Query UI
   - Add mode toggle (simple vs advanced)
   - Implement advanced query input
   - Add documentation and examples
   - Final testing and validation

---

## Success Criteria

### Stage 1:
- ✅ All existing co-occurrence queries return identical results
- ✅ All tests pass with advancedQuery parameter
- ✅ URL encoding works correctly

### Stage 2:
- ✅ Heatmap displays all locations in single view
- ✅ Hover info shows count, coverage, frequency
- ✅ Consistent styling with other heatmaps in app

### Stage 3:
- ✅ Users can write 3-of queries
- ✅ Users can write OR/AND/NOT queries  
- ✅ Query syntax errors show helpful messages
- ✅ Example queries work out-of-the-box
- ✅ Documentation is clear and comprehensive

---

## Technical Notes

### URL Encoding
Advanced queries must be URL-encoded when passed as GET parameters:
- Space → `%20`
- `[` → `%5B`, `]` → `%5D`
- `:` → `%3A`
- Use Python's `urllib.parse.quote()` for encoding

### API Request Format
```python
# Simple mode (backward compatible)
mutations = ["23149T", "23224T", "23311T"]
query = " & ".join(mutations)  # "23149T & 23224T & 23311T"

# Advanced mode (user input)
query = "[3-of: 23149T, 23224T, 23311T, 23403G, 23436G]"

# Both use same API parameter
payload = {
    "advancedQuery": query,
    "locationName": location,
    "samplingDateFrom": start_date,
    "samplingDateTo": end_date,
    "fields": ["samplingDate"]
}
```

### Backward Compatibility
- Stage 1: Maintains exact same functionality (AND queries)
- Stage 2: Changes visualization but not query logic
- Stage 3: Adds new capability (advanced queries) while preserving simple mode

---

## Future Enhancements (Post-Stage 3)

- [ ] Query builder UI with drag-and-drop mutation selection
- [ ] Saved query templates per variant (Omicron, Delta, etc.)
- [ ] Query validation with real-time syntax checking
- [ ] Export query results to CSV/JSON
- [ ] Compare multiple queries side-by-side
- [ ] Integration with amino acid mutations (not just nucleotide)


