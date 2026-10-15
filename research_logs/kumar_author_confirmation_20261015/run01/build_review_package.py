"""Render existing manuscript text/figures; no scientific model or data access."""

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path("/workspace/few-shot-mi-eeg")
OUT = ROOT / "manuscript/review_package_author_confirmed_20261015"
LOG = ROOT / "research_logs/kumar_author_confirmation_20261015/run01"
BIB = ROOT / "manuscript/kumar_references_20261015.bib"
BASE = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_source(source, pdf):
    text = source.read_text()
    title, text = text.split("\n", 1)
    title = title.lstrip("# ").strip()

    def image_link(match):
        alt, target, attrs = match.groups()
        path = (source.parent / target).resolve()
        if not path.is_file():
            raise ValueError(f"Missing figure: {path}")
        return f"![{alt}]({path}){attrs or ''}"

    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)(\{[^}]+\})?", image_link, text)

    def evidence_link(match):
        label, target = match.groups()
        if target.startswith(("https://", "http://", "#", "mailto:")):
            return match.group()
        relative = (source.parent / target.split("#")[0]).resolve().relative_to(ROOT)
        if not (ROOT / relative).exists():
            raise ValueError(f"Broken evidence link: {target}")
        tracked = (
            subprocess.run(
                ["git", "cat-file", "-e", f"{BASE}:{relative}"],
                cwd=ROOT,
                capture_output=True,
                check=False,
            ).returncode
            == 0
        )
        revision = BASE if tracked else "research/learning-preserving-bci"
        url = (
            f"https://github.com/jackzhu119/few-shot-mi-eeg/blob/{revision}/{quote(str(relative))}"
        )
        return f"[{label}]({url})"

    text = re.sub(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)", evidence_link, text)
    if pdf:
        text = re.sub(
            r"`([a-f0-9]{40}|[a-f0-9]{64})`",
            lambda m: r"\texttt{\seqsplit{" + m[1] + "}}",
            text,
        )
    if pdf:
        text = text.replace("朱子元", r"\textcjk{朱子元}")
    return title, text


def main():
    OUT.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc)
    env = dict(os.environ)
    env["SOURCE_DATE_EPOCH"] = str(int(stamp.timestamp()))
    header = OUT / "review_typesetting.tex"
    header.write_text(
        "\\usepackage{seqsplit}\n"
        "\\newfontfamily\\cjknamefont{Noto Serif CJK SC}\n"
        "\\newcommand{\\textcjk}[1]{{\\cjknamefont #1}}\n"
        "\\emergencystretch=3em\n\\AtBeginDocument{\\Urlmuskip=0mu plus 2mu}\n"
    )
    sources = [
        ("manuscript", ROOT / "manuscript/kumar_longitudinal_decoding_working_draft_20261015.md"),
        ("supplement", ROOT / "manuscript/kumar_supplementary_methods_20261015.md"),
        ("author_checklist", ROOT / "manuscript/kumar_author_review_checklist_20261015.md"),
    ]
    commands = []
    inputs = {str(BIB.relative_to(ROOT)): sha(BIB)}
    for name, source in sources:
        inputs[str(source.relative_to(ROOT))] = sha(source)
        for kind in ("pdf", "docx"):
            title, body = export_source(source, kind == "pdf")
            render = OUT / f"{name}_{kind}_source.md"
            render.write_text(body)
            target = OUT / f"{name}.{kind}"
            if target.exists():
                raise FileExistsError(target)
            command = [
                "pandoc",
                str(render),
                "--from=markdown",
                "--standalone",
                "--shift-heading-level-by=-1",
                "--citeproc",
                f"--bibliography={BIB}",
                f"--csl={OUT / 'plos.csl'}",
                "--metadata",
                f"title={title}",
                "--metadata",
                "lang=en-US",
                "--metadata",
                "link-citations=true",
                "--output",
                str(target),
            ]
            if kind == "pdf":
                command.extend(
                    [
                        "--pdf-engine=xelatex",
                        f"--include-in-header={header}",
                        "-V",
                        "papersize=a4",
                        "-V",
                        "geometry:margin=20mm",
                        "-V",
                        "mainfont=DejaVu Serif",
                        "-V",
                        "sansfont=DejaVu Sans",
                        "-V",
                        "monofont=DejaVu Sans Mono",
                        "-V",
                        "fontsize=10pt",
                        "-V",
                        "linestretch=1.05",
                        "-V",
                        "colorlinks=true",
                    ]
                )
            started = datetime.now(timezone.utc).isoformat()
            result = subprocess.run(
                command, cwd=ROOT, env=env, capture_output=True, text=True, check=False
            )
            (LOG / f"build_{name}_{kind}.stdout").write_text(result.stdout)
            (LOG / f"build_{name}_{kind}.stderr").write_text(result.stderr)
            item = {
                "command": command,
                "started_at_utc": started,
                "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                "returncode": result.returncode,
                "stdout_path": str((LOG / f"build_{name}_{kind}.stdout").relative_to(ROOT)),
                "stderr_path": str((LOG / f"build_{name}_{kind}.stderr").relative_to(ROOT)),
            }
            commands.append(item)
            (LOG / "build_commands.json").write_text(json.dumps(commands, indent=2) + "\n")
            if result.returncode:
                raise RuntimeError(f"Typesetting failed: {name}.{kind}; original log retained")
            if not target.is_file() or not target.stat().st_size:
                raise ValueError(f"Empty output: {target}")
    assert all(sha(ROOT / path) == value for path, value in inputs.items())
    report = {
        "status": "rendered_from_saved_text_and_figures_pending_visual_QA",
        "started_at_utc": stamp.isoformat(),
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_commit": BASE,
        "worktree_authored_material_not_in_base_commit": True,
        "SOURCE_DATE_EPOCH": env["SOURCE_DATE_EPOCH"],
        "pandoc_version": subprocess.check_output(["pandoc", "--version"], text=True).splitlines()[
            0
        ],
        "script_sha256": sha(Path(__file__)),
        "inputs": inputs,
        "source_text_unchanged": True,
        "fits_forwards_or_raw_EEG_decodes": 0,
        "local_evidence_links_in_exports": "existing base files use fixed base Git commit; newly authored files use research branch until final publication commit",
        "outputs": [
            {"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": sha(p)}
            for p in sorted(OUT.iterdir())
            if p.is_file()
        ],
    }
    (LOG / "render_build_receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "exported_outputs": len(report["outputs"])}))


if __name__ == "__main__":
    main()
