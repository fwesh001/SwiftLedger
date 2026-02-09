# assets — Static Resources 🎨

This folder holds static assets used by the SwiftLedger application.

## What’s inside
- `styles.qss` — The central QSS stylesheet implementing the high-contrast dark theme for the entire app (buttons, inputs, tables, dialogs, tooltips, etc.).
- (Placeholder) `icons/` — Recommended location for application icons, SVGs, and logos.
- (Placeholder) `images/` — Recommended location for raster assets if needed.

## Guidelines
- Keep all style-related changes in `styles.qss` to ensure consistent theming across the app.
- Store small, single-purpose icons as SVG for scalability.
- Large binary assets should be avoided in the repo; instead, store them in an asset server or LFS when required.
