"""Render only existing Figure 4; no fitting, prediction or scientific inputs."""
from pathlib import Path
import csv
import hashlib
import importlib.util
import io
import json
import copy

import fitz
from fontTools.ttLib import TTFont
import numpy as np
from PIL import Image

ROOT = Path('/workspace/few-shot-mi-eeg')
HERE = Path(__file__).resolve().parent
STEM = 'Fig4_longitudinal_paired_changes'
ORIGINAL = ROOT / 'manuscript/figures/plos_innovation_20261017'
SOURCE = ROOT / 'research_logs/kumar_frozen_query_comparison_20261015/run01'

def digest(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def font(document, index):
    data = document.extract_font(document[0].get_fonts()[index][0])[3]
    return TTFont(io.BytesIO(data)), data

def main():
    # All restored full font files match the original 20261017 receipt exactly.
    regular_path = HERE / 'restored_fonts/Arial.TTF'
    bold_path = HERE / 'restored_fonts/Arialbd.TTF'
    original_regular_bytes = regular_path.read_bytes()
    spec = importlib.util.spec_from_file_location('original_figure_renderer', ROOT / 'scripts/render_kumar_submission_figures_20261016.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for path in (HERE/'restored_fonts').glob('Arial*.TTF'):
        module.font_manager.fontManager.addfont(str(path))
    module.matplotlib.rcParams.update({
        'font.family': 'Arial', 'font.size': 9, 'axes.labelsize': 9,
        'axes.titlesize': 10, 'xtick.labelsize': 8.5, 'ytick.labelsize': 8.5,
        'legend.fontsize': 8, 'svg.hashsalt': 'kumar-plos-innovation-20261017',
        'pdf.fonttype': 42, 'ps.fonttype': 42, 'figure.facecolor': 'white',
        'axes.facecolor': 'white', 'savefig.facecolor': 'white',
    })
    participants = {(r['subject'], r['method']):r for r in csv.DictReader((SOURCE / 'per_participant_endpoints.csv').open())}
    session_rows = list(csv.DictReader((SOURCE / 'per_subject_session.csv').open()))
    output = HERE / 'exports_verified_fonts_run03'
    output.mkdir(exist_ok=False)
    module.OUT = output
    original_save = module.save_figure
    receipt = {}
    def save(fig, stem):
        fig.canvas.draw()
        # Require the same embedded Arial family, and force the extracted font
        # files in case a system fallback has an unrelated Arial name.
        for artist in fig.findobj(module.matplotlib.text.Text):
            if artist.get_text():
                artist.set_fontproperties(module.font_manager.FontProperties(
                    fname=str(bold_path if artist.get_fontweight() == 'bold' else regular_path),
                    size=artist.get_fontsize()))
        fig.canvas.draw()
        baseline = HERE / 'baseline_reexport_verified_fonts_run03.png'
        fig.savefig(baseline, dpi=600)
        original = np.array(Image.open(ORIGINAL / (STEM + '.png')).convert('RGB'))
        before = np.array(Image.open(baseline).convert('RGB'))
        if original.shape != before.shape or not np.array_equal(original, before):
            mask = np.any(original != before, axis=2)
            ys,xs = np.where(mask)
            raise AssertionError(f'baseline pixel mismatch: {mask.sum()} pixels; bounds {(xs.min(),ys.min(),xs.max(),ys.max())}')
        labels = [a for a in fig.findobj(module.matplotlib.text.Text) if a.get_text() == 'Remaining (n = 12)']
        assert len(labels) == 1
        label = labels[0]
        before_box = label.get_window_extent(fig.canvas.get_renderer()).frozen()
        label.set_text('Primary cohort (n = 12)')
        fig.canvas.draw()
        after_box = label.get_window_extent(fig.canvas.get_renderer()).frozen()
        original_save(fig, stem)
        # Preserve the documented RGB PNG representation of the RGB TIFF.
        with Image.open(output / (STEM + '.tif')) as image:
            buffer = io.BytesIO()
            image.save(buffer, format='PNG', dpi=(600,600))
        (output / (STEM + '.png')).write_bytes(buffer.getvalue())
        after = np.array(Image.open(output / (STEM + '.png')).convert('RGB'))
        changed = np.any(original != after, axis=2)
        ys,xs = np.where(changed)
        height = original.shape[0]
        factor = 600 / fig.dpi
        left = int(min(before_box.x0, after_box.x0)*factor)-4
        right = int(max(before_box.x1, after_box.x1)*factor)+5
        top = height-int(max(before_box.y1, after_box.y1)*factor)-5
        bottom = height-int(min(before_box.y0, after_box.y0)*factor)+5
        permitted = np.zeros(changed.shape, dtype=bool)
        permitted[top:bottom,left:right] = True
        assert not np.any(changed & ~permitted), 'pixels outside the edited label changed'
        receipt.update({'baseline_reexport_pixel_identical': True,
                        'changed_pixel_count': int(changed.sum()),
                        'changed_pixel_bbox_xyxy': [int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())],
                        'permitted_label_bbox_xyxy': [left,top,right,bottom],
                        'all_pixels_outside_label_unchanged': True})
    module.save_figure = save
    module.figure4(session_rows, participants)
    assert (output / (STEM + '_source_data.csv')).read_bytes() == (ORIGINAL / (STEM + '_source_data.csv')).read_bytes()
    receipt.update({'outputs':[digest(p) for p in sorted(output.iterdir())],
                    'sources':[digest(SOURCE / n) for n in ['per_subject_session.csv','per_participant_endpoints.csv']],
                    'font_source': 'Original full Arial font files restored from original frozen archive with exact SHA256 checks',
                    'original_regular_font_sha256': hashlib.sha256(original_regular_bytes).hexdigest(),
                    'geometry': module.GEOMETRY,
                    'new_model_fits':0,'new_predictions':0})
    (HERE/'fig4_label_render_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':'completed','receipt':str(HERE/'fig4_label_render_receipt.json')}))

if __name__ == '__main__':
    main()
