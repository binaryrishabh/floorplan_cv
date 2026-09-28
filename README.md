# Floorplan Door Detector v5.2 — generalized vector-first prototype

v5 removes the hardcoded assumptions from v4 and separates **detection**, **sheet understanding**, and **project-level reconciliation**.

## Generalization changes

- **No fixed pages 2–7.** Every page is classified from its extracted title text. Floor plans are processed automatically; elevations/details/schedules are skipped.
- **Scale-aware geometry.** It parses drawing scales such as `1/8" = 1'-0"` and `1/4" = 1'-0"`. Door-size thresholds are expressed in real-world feet and converted to PDF points per sheet.
- Supports **exploded polyline swing arcs** and **true cubic Bézier arcs**.
- Door-leaf lineweight is learned from strong swing detections before fallback detectors run, instead of assuming one universal CAD lineweight.
- Keeps conservative **tag + leaf** recovery and **double-leaf** recovery.
- Low-detail double-leaf matches are treated as **review candidates**, not silently counted. Use `--show-review` to draw them in orange.
- **Overall and enlarged plans can both be processed.** Repeated room/space text and repeated door tags are used to register overlapping views with a similarity transform.
- **Cross-sheet reconciliation** merges duplicate door appearances and reports a project-level count.
- **Source hierarchy:** the most detailed plan scale available for a level is authoritative. Unmatched detections seen only on a lower-detail overall sheet are reported as review items instead of inflating the count.
- Output contains `appearance_count`, `unique_project_doors`, counts by level, registrations, duplicate groups, and review candidates.

## Run

```bash
pip install -r requirements.txt
python run.py floorplan.pdf
```

Optional:

```bash
python run.py floorplan.pdf --out result
python run.py floorplan.pdf --show-review
python run.py floorplan.pdf --include-unknown
python run.py floorplan.pdf --points-per-foot 18
```

`--points-per-foot` is an escape hatch when a plan set has missing/broken scale text. Typical values: 9 for 1/8" = 1'-0", 18 for 1/4" = 1'-0".

## Validation

The detector must be measured, not described as “100%” without ground truth.

Create a ground-truth JSON using PDF coordinates:

```json
{
  "2": [[x, y], [x, y]],
  "3": [[x, y]]
}
```

Then:

```bash
python evaluate.py out/summary.json ground_truth.json --tol 20
```

## Quick self-test

```bash
python self_test.py
```

## Production boundary

This is a generalized **vector-PDF** engine, not a universal guarantee for arbitrary construction documents. Real plan sets may contain raster scans, multiple differently scaled viewports on one sheet, nonstandard door symbols, or PDF exports that destroy semantic/vector structure. A production system should keep this engine as the high-confidence path and add a raster/vision fallback for review candidates and vector-poor pages, with precision/recall measured on a diverse labeled corpus.

## Windows-safe output handling (v5.1)

Annotated PNGs and `summary.json` no longer abort the detector if an older output file is open in Windows Photos, Explorer preview, an editor, or another process. The detector first tries the normal filename (`page_02_doors.png`). If Windows refuses to overwrite it, the run continues and writes a unique sibling such as `page_02_doors_run_20260928_223500_123456.png`. The exact path is stored in `summary.json`.


## Reconciliation accounting (v5.2)

v5.2 makes the project-count arithmetic explicit so review items cannot be confused with duplicate removal. The CLI and `summary.json` now expose three stages:

```text
sheet appearances
- duplicate appearances merged
= reconciled physical-door groups
- secondary-only groups held for review
= auto-counted unique project doors
```

The review queue is also split into **sheet-level ambiguous candidates** and **secondary-only reconciled groups**. Assertions verify these equations on every run; a reporting regression now fails loudly instead of printing contradictory counts.
