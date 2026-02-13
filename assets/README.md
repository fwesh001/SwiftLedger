```markdown
# assets — Static Resources

This folder holds static resources used by SwiftLedger: styles, icons, and optional branding images.

Contents
- `styles.qss` — central QSS stylesheet used by the app. Modify here for app-wide theme changes.
- `icons/` (recommended) — store SVG icons used by UI elements.
- `images/` (recommended) — place raster images or organization logos here if required.

PDF fonts & Unicode
- When generating PDFs, the default built-in PDF fonts are limited to Latin-1. For Unicode (e.g., currency symbols or non-Latin text) install a Unicode TTF such as DejaVu Sans and register it with fpdf2 if you want those characters in generated PDFs.

Guidelines
- Keep icons as SVG for scalability.
- Avoid committing very large binary files; prefer external storage or Git LFS for large logos.
- Keep style customizations centralized in `styles.qss` for consistent theming.

```
