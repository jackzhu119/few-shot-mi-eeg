# Reproduce the JNE files

Scientific results are frozen at `e5969e6ee6294206954b5a83c5258fdb2e143eda`; the prior execution plan is `13dd7646c4ce37db40504154388e76b4c6ca6595`. Journal formatting adds no model fit, inference or statistical search.

From the repository root, using the recorded document/plot dependencies:

```bash
python scripts/render_paper2_jne_figures_20261104.py
python scripts/render_paper2_jne_supplementary_figures_20261104.py
python scripts/build_paper2_jne_20261104.py
```

The renderers read existing tables; the supplement renderer reads the already computed figure CSVs. They do not regenerate bootstrap intervals. Main and supplementary source CSVs are preserved byte for byte. PDF/SVG contain vector graphics and editable text; TIFFs use RGB8, LZW and 600 dpi. Figure display labels change to lowercase parenthesized letters; original data panel IDs remain unchanged.

The builder uses Pandoc, XeLaTeX, DejaVu fonts, xurl/seqsplit and python-docx. It exports 12 pt review documents, embeds all five main figures and two editable tables, and retains four editable main equations. It checks scientific-source equivalence, abstract headings, citations, actual supplement sizes and archive preservation. Supplement short titles and descriptions are inserted into export sources without changing its numerical results. Exact wording clarifications are recorded by SHA256 in `research_logs/paper2_jne_20261104/narrative_cleanup_20261104.json`. `SUPPLEMENT_TABLE_INDEX.json` records the 27 captions, old/new reference mapping and each unchanged table-block SHA256. The builder reverses only those recorded presentation changes when checking the frozen scientific source.

To reconstruct scientific tables from saved outputs without EEG, checkpoints or new fits, run the existing source command with an unused output directory:

```bash
python scripts/reproduce_paper2_alignment_saved_results_20261104.py --output /tmp/paper2-jne-table-reproduction-new
```

That command was already validated for all 17 CSV tables and independent numerical replay in the frozen scientific version. See `manuscript/bmt_alignment_integrated_20261104/PUBLIC_ARCHIVE_REPRODUCTION.json` and `research_logs/paper2_alignment_integrated_20261104/independent_checks/` for the actual evidence. This format revision does not claim to have rerun science checks or all original experiments.

The JNE data/code ZIP preserves all 1,392 historical scientific entries byte for byte, including historical BMT source paths, and adds current JNE sources, figure CSVs, policy records and format code. The old scientific ZIP SHA256 is `d16aac10c7adbc467cfaa9ba83e08933e91456e8cad8df569d8293315835d94b`. Code and original derived content follow LICENSE/LICENSING.md; the third-party CSL retains CC BY-SA 3.0. No raw EEG, model weights or credentials are packaged.
