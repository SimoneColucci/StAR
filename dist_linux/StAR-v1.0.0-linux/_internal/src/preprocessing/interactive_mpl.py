"""
Stand-alone matplotlib interactors for the PreProcessing module.

These provide the interactive calibration / crop / intensity-range operations
using matplotlib pop-up windows, for command-line use (run/preprocess.py).

The Tkinter GUI supplies its own embedded-canvas interactors instead.
"""

import os
import numpy as np


# ---------------------------------------------------------------------------
# Spatial calibration
# ---------------------------------------------------------------------------
def calibrate(image_path):
    import matplotlib.pyplot as plt
    from skimage.io import imread

    img = imread(image_path)
    fig, ax = plt.subplots()
    ax.imshow(img, cmap='gray')
    ax.set_title('Calibration: click the two endpoints of a known distance')
    plt.tight_layout()
    pts = plt.ginput(2, timeout=0)
    if len(pts) < 2:
        plt.close(fig)
        return None
    (x1, y1), (x2, y2) = pts
    ax.plot([x1, x2], [y1, y2], 'y-', linewidth=2)
    fig.canvas.draw()
    dist_px = np.hypot(x2 - x1, y2 - y1)

    units = input('Enter real-world units (micron, mm, m) [micron]: ').strip() \
        or 'micron'
    dstr = input('Enter distance in those units [100]: ').strip() or '100'
    plt.close(fig)
    try:
        dist_units = float(dstr)
    except ValueError:
        return None
    if dist_units <= 0:
        return None

    per_pixel = dist_units / dist_px
    factor = {'micron': 1e-6, 'mm': 1e-3, 'm': 1.0}.get(units.lower())
    if factor is None:
        print('Invalid unit.')
        return None
    return per_pixel * factor


# ---------------------------------------------------------------------------
# Freehand / rectangle crop
# ---------------------------------------------------------------------------
def crop(image_path, save_path, state):
    import matplotlib.pyplot as plt
    from matplotlib.widgets import PolygonSelector, RectangleSelector
    from matplotlib.path import Path as MplPath
    from skimage.io import imread
    from skimage.color import rgb2gray
    from PIL import Image

    img = imread(image_path)
    if img.ndim > 2:
        gray = (rgb2gray(img[:, :, :3]) * 255).astype(np.uint8)
    else:
        gray = img.astype(np.uint8)

    h, w = gray.shape
    method = (input('Crop method (freehand/rectangle) [rectangle]: ').strip()
              or 'rectangle').lower()

    selection = {'verts': None, 'rect': None}
    fig, ax = plt.subplots()
    ax.imshow(gray, cmap='gray')
    ax.set_title('Select area, then close the window')

    if method.startswith('f'):
        def on_poly(verts):
            selection['verts'] = verts
        selector = PolygonSelector(ax, on_poly)
    else:
        def on_rect(eclick, erelease):
            x0, y0 = eclick.xdata, eclick.ydata
            x1, y1 = erelease.xdata, erelease.ydata
            selection['rect'] = (min(x0, x1), min(y0, y1),
                                 abs(x1 - x0), abs(y1 - y0))
        selector = RectangleSelector(ax, on_rect, useblit=True,
                                     interactive=True)
    plt.tight_layout()
    plt.show(block=True)
    del selector

    mask = np.zeros((h, w), dtype=bool)
    if selection['verts']:
        yy, xx = np.mgrid[0:h, 0:w]
        pts = np.column_stack((xx.ravel(), yy.ravel()))
        path = MplPath(selection['verts'])
        mask = path.contains_points(pts).reshape(h, w)
    elif selection['rect']:
        x, y, rw, rh = selection['rect']
        x, y = int(round(x)), int(round(y))
        rw, rh = int(round(rw)), int(round(rh))
        mask[y:y + rh, x:x + rw] = True
    else:
        return 0, state

    area = int(mask.sum())

    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    ymin, ymax = np.where(rows)[0][[0, -1]]
    xmin, xmax = np.where(cols)[0][[0, -1]]

    cropped = gray[ymin:ymax + 1, xmin:xmax + 1].copy()
    mask_c = mask[ymin:ymax + 1, xmin:xmax + 1]
    cropped[~mask_c] = 255

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    base, _ = os.path.splitext(save_path)
    save_path = base + '.jpg'
    Image.fromarray(cropped).save(save_path, quality=100)
    return area, state


# ---------------------------------------------------------------------------
# Intensity range extraction
# ---------------------------------------------------------------------------
def intensity(image_path):
    import matplotlib.pyplot as plt
    from skimage.io import imread
    from skimage.color import rgb2gray
    from skimage.measure import profile_line

    img = imread(image_path)
    if img.ndim > 2:
        gray = (rgb2gray(img[:, :, :3]) * 255).astype(np.uint8)
    else:
        gray = img.astype(np.uint8)

    fig, ax = plt.subplots()
    ax.imshow(gray, cmap='gray')
    ax.set_title('Draw a line: click start and end points')
    plt.tight_layout()
    pts = plt.ginput(2, timeout=0)
    plt.close(fig)
    if len(pts) >= 2:
        (x0, y0), (x1, y1) = pts[0], pts[1]
        prof = profile_line(gray, (y0, x0), (y1, x1))
        fig2, ax2 = plt.subplots()
        ax2.plot(prof, 'k')
        ax2.set_title('Pixel values along the line')
        ax2.set_xlabel('Relative position')
        ax2.set_ylabel('Greyscale value')
        plt.show(block=False)

    imin = input('Enter minimum intensity [0]: ').strip() or '0'
    imax = input('Enter maximum intensity [100]: ').strip() or '100'
    import matplotlib.pyplot as _plt
    _plt.close('all')
    return float(imin), float(imax)


DEFAULT_INTERACTORS = {
    'calibrate': calibrate,
    'crop': crop,
    'intensity': intensity,
}
