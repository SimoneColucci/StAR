"""
Bubble/crystal segmentation and region-property measurement.

Python port of matlab/src/AnalyzeBubble/analyzeBubble.m

The image is thresholded on an intensity range, connected components are
labelled (8-connectivity) and a set of region properties (equivalent to the
MATLAB ``regionprops`` call) is measured for each blob.

Intentional difference from the MATLAB version
----------------------------------------------
The MATLAB pipeline (``runAnalyzeBubble.m``) does NOT measure the blobs
directly. It traces the blob outlines with ``bwboundaries`` and rebuilds a
label image from those polygons with ``poly2label`` before calling
``regionprops``. Filling the polygon that runs through the *centres* of the
border pixels drops roughly half a perimeter of pixels from every region, so
the MATLAB areas are systematically smaller (about 7-8% on this dataset;
``EquivDiameter`` about half of that, since diameter scales with the square
root of area).

This Python port measures the connected components directly
(``measure.label`` -> ``regionprops``), i.e. it counts the actual blob pixels.
This is deliberately kept because it is more accurate than the MATLAB
``poly2label`` round-trip, which is an artefact of how MATLAB extracted the
regions from a ``groundTruth`` object. As a consequence the numeric values in
``measurementsTable_*.csv`` differ from the MATLAB output (Area and derived
quantities are the main drivers; perimeter/Feret/orientation also differ
because scikit-image and MATLAB compute them with different algorithms).
"""

import numpy as np
from skimage import measure
from skimage.color import rgb2gray


def _min_feret_diameter(coords):
    """
    Minimum Feret diameter of a set of (row, col) pixel coordinates,
    computed via rotating calipers on the convex hull.

    Returns the minimum width (in pixels) over all hull-edge orientations.
    """
    pts = np.column_stack((coords[:, 1], coords[:, 0])).astype(float)  # (x, y)
    if pts.shape[0] < 3:
        # Degenerate: fall back to bounding extent
        return float(np.hypot(
            np.ptp(pts[:, 0]) if pts.shape[0] else 0.0,
            np.ptp(pts[:, 1]) if pts.shape[0] else 0.0))
    try:
        from scipy.spatial import ConvexHull
        hull = ConvexHull(pts)
        hpts = pts[hull.vertices]
    except Exception:
        hpts = pts

    n = len(hpts)
    min_width = np.inf
    for i in range(n):
        p1 = hpts[i]
        p2 = hpts[(i + 1) % n]
        edge = p2 - p1
        norm = np.hypot(edge[0], edge[1])
        if norm == 0:
            continue
        # unit normal to the edge
        nx, ny = -edge[1] / norm, edge[0] / norm
        proj = (hpts - p1) @ np.array([nx, ny])
        width = proj.max() - proj.min()
        if width < min_width:
            min_width = width
    return float(min_width)


def analyze_bubble(image_path, tec):
    """
    Segment an image and measure region properties (in pixel units).

    Parameters
    ----------
    image_path : str
        Path to the (cropped) image to analyse.
    tec : dict
        ``range`` : sequence [low, high] of intensity thresholds.

    Returns
    -------
    props : list[dict]
        One dict per detected blob with the measured (pixel-unit) properties.
    original : ndarray
        Grayscale image used for segmentation (uint8).
    boundaries : list[ndarray]
        Blob boundaries as (row, col) arrays (for plotting).
    """
    from skimage.io import imread

    original = imread(image_path)
    if original.ndim > 2:
        n_ch = original.shape[2]
        print(f'Original image file has {n_ch} color channels\n'
              f'Conversion to grayscale...')
        gray = (rgb2gray(original[:, :, :3]) * 255).astype(np.uint8)
    else:
        gray = original.astype(np.uint8)

    rng = np.asarray(tec['range'], dtype=float).ravel()
    low_threshold = np.min(rng)
    high_threshold = np.max(rng)

    binary = (gray >= low_threshold) & (gray <= high_threshold)

    # 8-connectivity labelling (connectivity=2 in skimage)
    label_img = measure.label(binary, connectivity=2)
    n_blobs = int(label_img.max())

    boundaries = measure.find_contours(binary.astype(float), 0.5)

    regions = measure.regionprops(label_img)
    props = []
    for r in regions:
        area = float(r.area)
        perim = float(r.perimeter)
        equiv_d = float(r.equivalent_diameter_area)
        major = float(r.axis_major_length)
        minor = float(r.axis_minor_length)
        ecc = float(r.eccentricity)
        orient = float(np.degrees(r.orientation))
        solidity = float(r.solidity)
        circularity = (4.0 * np.pi * area / perim ** 2) if perim > 0 else 0.0
        try:
            max_feret = float(r.feret_diameter_max)
        except Exception:
            max_feret = major
        min_feret = _min_feret_diameter(r.coords)

        props.append({
            'Area': area,
            'MajorAxisLength': major,
            'MinorAxisLength': minor,
            'Eccentricity': ecc,
            'Orientation': orient,
            'Circularity': circularity,
            'EquivDiameter': equiv_d,
            'Solidity': solidity,
            'Perimeter': perim,
            'MaxFeretDiameter': max_feret,
            'MinFeretDiameter': min_feret,
        })

    if not props:
        print(f'Warning: No valid bubbles found in the image: {image_path}')

    return props, gray, boundaries, n_blobs
