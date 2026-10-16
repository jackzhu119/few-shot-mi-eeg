# Independent revision figure validation

Status: **PASS**, 1324 checks; no failures.

The renderer differs from the preserved 2026-10-15 version only in its two new output paths and the Fig1 legend wording `Participant (method color)`. Colors are assigned per method column, so the wording describes the actual encoding.

All four source-data CSVs are byte-identical to the old exports. All sixteen PNG/TIFF/SVG/PDF exports were checked. Fig2–4 are byte-identical in all four formats; Fig1 image changes are confined to the bottom legend region. Actual PDF text differs only by the intended legend phrase. Fig4 remains RdBu_r with shared ±60 pp limits; its maximum absolute saved change remains 55.00000000000001 pp.

Saved Fig1 participant/summary values, Fig2 paired changes and original interval, Fig3 half margins and sign patterns, and all 180 Fig4 cells were independently matched to saved sources. Geometry is unchanged. TIFFs are single-frame RGB, 600 dpi, LZW, below 10 MB, and exactly match PNG RGB pixels. PNGs are opaque at 600 dpi; actual PDF dimensions and embedded Liberation Sans fonts and SVG dimensions and 8–12 pt glyph sizes pass. Strict Arial/Times compliance is not claimed.

All 55 protected pre-revision files retained their recorded byte lengths and SHA-256 hashes. This validation reads saved tables and exported images only; it performs no training, query inference, bootstrap, test, Pod operation, installation, or new environment work.

Full checks and exact changed-pixel boxes are recorded in independent_revision_validation.json. Validator was copied from the old independent validator and extended in this new log directory.
