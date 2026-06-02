# Auto Mode Algorithm

`auto` mode should minimize expensive OCR.

1. Validate input extension.
2. For PDFs, inspect each selected page with PyMuPDF:
   - Character count.
   - Word count.
   - Image blocks.
   - Page area and image coverage.
3. Mark a page as native when extracted text is long enough and not mostly
   whitespace.
4. Mark a page as OCR-needed when it has no text, very short text, or appears
   image-heavy.
5. Select DPI:
   - 180 for `scan-fast`.
   - 220 for `auto`/`balanced`.
   - 300 for `quality`/`markdown`.
   - Respect explicit `--dpi`.
6. Select OCR engine from installed engines and requested mode.
7. Check cache before rendering/OCR.
8. OCR only the pages that need it.
9. Validate each page. Retry weak OCR pages with a stronger profile when
   available.
10. Join pages with the requested separator and write output.
