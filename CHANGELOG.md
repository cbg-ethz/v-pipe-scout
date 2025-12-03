# Changelog

All notable changes to this project will be documented in this file.

## [0.5.0-beta] - 2025-12-03

### Added
- **Advanced Query Support**: Enabled custom advanced queries with Boolean logic (`AND`, `OR`, `NOT`) and N-of filtering (`[3-of: ...]`) in the Co-occurrence page.
- **Multi-location Heatmap**: Replaced line plots with a heatmap visualization for better comparison of mutation frequencies across multiple locations over time.
- **Region Explorer Improvements**: Added filtering for wildtype/no-data mutations and defaults to skipping empty dates.
- **Auto-restart**: Enabled auto-restart policy for containers in `docker-compose.yml`.

### Changed
- **Co-occurrence Page**: Renamed URL state key from `complex` to `coocurrences` (with backward compatibility).
- **Coverage Definition**: Refactored coverage logic to use intersection-based coverage (non-N at all specified positions) for more accurate representation.
