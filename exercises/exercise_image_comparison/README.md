# Exercise: Image Comparison Report Generator

## Overview

In this exercise you will build a Python pipeline that takes two versions of the same image and produces an automated visual comparison report. The pipeline uses only **Pillow** and **NumPy** — no machine learning, no OCR, no heavy dependencies.

**Use case examples:** design revision QA, UI screenshot regression testing, satellite imagery change detection, before/after product photo comparison.

## Prerequisites

```bash
pip install Pillow numpy
```

Optional (for display during development):

```bash
pip install matplotlib
```

## Input

Two images representing the same scene at different points in time or different versions:

- `image_a.png` — the "before" image
- `image_b.png` — the "after" image

## Pipeline Steps

### Step 1: Load & Normalize

Load both images using Pillow. Ensure they are comparable:

- Convert both to the same color mode (RGB)
- If dimensions differ, resize the smaller image to match the larger (or vice versa — pick a strategy and document your choice)
- Convert both to NumPy arrays for numerical processing

**Hints:**
- `Image.open()`, `.convert('RGB')`, `.resize()`
- `np.array(img)` gives you a `(height, width, 3)` array with values 0–255

### Step 2: Pixel Difference Map

Compute the absolute per-pixel difference between the two images:

- Subtract one array from the other
- Take the absolute value
- The result is a "raw diff" array of the same shape, where bright pixels = large differences

**Hints:**
- Watch out for unsigned integer underflow — cast to `int16` or `float` before subtracting
- `np.abs(a.astype(np.int16) - b.astype(np.int16))`

### Step 3: Threshold to Binary Mask

Convert the raw diff into a clean binary mask (changed vs. unchanged):

- Convert the diff to grayscale (average across RGB channels, or use luminance weights)
- Apply a threshold (e.g., pixels with diff > 30 are "changed")
- Output a 2D boolean or uint8 array: 1 = changed, 0 = unchanged

**Hints:**
- `gray_diff = np.mean(diff_array, axis=2)`
- `mask = (gray_diff > threshold).astype(np.uint8)`
- Experiment with the threshold value — too low catches noise, too high misses real changes

### Step 4: Bounding Boxes Around Changed Regions

Identify contiguous changed regions in the binary mask and draw bounding boxes around them on a copy of image B:

- Scan the mask to find connected components (groups of adjacent changed pixels)
- For each component, compute its bounding box (min/max row and column)
- Filter out tiny regions below a minimum area (noise)
- Draw rectangles on a copy of image B using Pillow's `ImageDraw`

**Hints:**
- For connected component labeling without scipy, you can implement a simple flood-fill, or use row/column projection as a simpler approximation
- If you want the easy path: `pip install scipy` and use `scipy.ndimage.label()` for connected components — this is the one optional dependency worth considering
- `ImageDraw.Draw(img).rectangle([x0, y0, x1, y1], outline='red', width=2)`

### Step 5: Compute Metrics

Calculate numerical comparison metrics:

- **Similarity percentage**: `(unchanged_pixels / total_pixels) * 100`
- **Number of changed regions**: count from Step 4
- **Total changed area**: sum of changed pixels (and as percentage of total)
- **Mean change intensity**: average value in the diff array where mask is True
- **Max change intensity**: peak difference value

Collect these into a dictionary.

### Step 6: Composite Output Image

Create a single side-by-side composite image with four panels:

```
| Original A | Original B | Diff Heatmap | Annotated (with boxes) |
```

- The diff heatmap should be colorized for visual clarity (e.g., map grayscale diff values to a red/yellow color gradient, or simply use the raw RGB diff amplified)
- Add a small label or border to each panel so the viewer knows which is which
- Use `Image.new()` to create the canvas and `.paste()` to place each panel

**Hints:**
- Canvas width = 4 × panel_width, canvas height = panel_height
- For a simple heatmap: multiply the grayscale diff by a color, e.g., `heatmap[:,:,0] = gray_diff * 255 / gray_diff.max()` for a red-channel heatmap
- `ImageFont` and `ImageDraw.text()` for labels (the default font works fine)

### Step 7: Save Report

Save two outputs:

1. **The composite image** as `comparison_report.png`
2. **The metrics** as `comparison_metrics.json`

```python
import json

with open('comparison_metrics.json', 'w') as f:
    json.dump(metrics, f, indent=2)
```

## Expected Output

### comparison_metrics.json (example)

```json
{
  "similarity_percent": 87.3,
  "changed_regions": 12,
  "changed_pixels": 48320,
  "changed_area_percent": 12.7,
  "mean_change_intensity": 64.2,
  "max_change_intensity": 221
}
```

### comparison_report.png

A single wide image with four panels showing the original pair, the diff heatmap, and the annotated version with bounding boxes around detected changes.

## Extension Ideas (Optional)

- **Per-channel analysis**: split the diff into R/G/B channels and report which channel changed most
- **Configurable sensitivity**: accept the threshold as a command-line argument
- **Batch mode**: process a folder of image pairs and generate a summary CSV
- **Animated GIF**: alternate between image A and image B with changed regions highlighted
- **Structural Similarity (SSIM)**: implement a windowed SSIM calculation for perceptual comparison (still pure NumPy, no extra libraries)

## Sample Data Sources

For satellite image pairs suitable for this exercise, see the datasets listed in the companion notes.
