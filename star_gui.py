#!/usr/bin/env python3
"""
StAR - Statistical Analysis of Rocks
====================================

Unified graphical interface for the whole StAR Python pipeline.

The window is organised in four tabs, from left to right::

    PreProcess  ->  Analyze  ->  Stereology  ->  Properties

The grouping of the measurements into groups is defined once in the
**PreProcess** tab and is shared with (inherited by) the Analyze, Stereology
and Properties tabs. Every tab shows the same group/file tree and edits the
same shared data model, so a group created (or an image added) in one tab is
immediately visible in the others.

Each module (tab) can be used independently or in succession within a single
workflow. When the modules are run in succession the relevant fields of the
downstream tabs are filled in automatically (they remain fully editable):

  * after **PreProcess** the *Analyze* / *Properties* tabs receive the cropped
    images, the calibration ``px2m`` values, the crop area and the intensity
    range;
  * after **Analyze** the *Stereology* / *Properties* tabs receive the
    generated ``measurementsTable_XXX.csv`` files;
  * after **Stereology** the ``measurementsStereoTable_XXX.csv`` files replace
    the Analyze measurement files in the *Properties* tab.

The four modules are Python ports of the corresponding MATLAB modules found in
``matlab/src`` (PreProcessing, AnalyzeBubble, Stereology, BubbleProperties).
"""

import os
import sys
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

# ---- Make the src package importable ---------------------------------------
if getattr(sys, 'frozen', False):
    ROOT_DIR = sys._MEIPASS
else:
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.widgets import RectangleSelector, PolygonSelector
from matplotlib.path import Path as MplPath

# Import the pipeline runners on the main thread at start-up. The Analyze /
# Stereology / Properties modules call ``matplotlib.use('Agg')`` at import
# time; importing them here (main thread) ensures the backend switch happens
# once, before any worker thread runs. The interactive dialogs build their
# figures with FigureCanvasTkAgg explicitly, so they work regardless of the
# global backend.
from src.run_preprocessing import run_preprocessing          # noqa: E402
from src.run_analyze import run_analyze                       # noqa: E402
from src.run_bubble_properties import run_bubble_properties   # noqa: E402
try:
    from src.run_stereology import run_stereology             # noqa: E402
except Exception:  # pysizeunfolder may be missing
    run_stereology = None


IMAGE_TYPES = [('Images', '*.jpg *.jpeg *.png *.tif *.tiff *.bmp'),
               ('All files', '*.*')]
CSV_TYPES = [('CSV', '*.csv'), ('All files', '*.*')]


# =============================================================================
# Log redirector
# =============================================================================
class _LogRedirector:
    """Redirect ``write`` calls to a Tkinter Text widget (thread-safe)."""

    def __init__(self, text_widget):
        self.text = text_widget

    def write(self, msg):
        try:
            self.text.after(0, self._append, msg)
        except Exception:
            pass

    def _append(self, msg):
        self.text.configure(state='normal')
        self.text.insert(tk.END, msg)
        self.text.see(tk.END)
        self.text.configure(state='disabled')

    def flush(self):
        pass


# =============================================================================
# Image helper
# =============================================================================
def _load_gray(image_path):
    from skimage.io import imread
    from skimage.color import rgb2gray
    img = imread(image_path)
    if img.ndim > 2:
        gray = (rgb2gray(img[:, :, :3]) * 255).astype(np.uint8)
    else:
        gray = img.astype(np.uint8)
    return gray


# =============================================================================
# Interactive dialog: spatial calibration
# =============================================================================
class CalibrationDialog(tk.Toplevel):
    """Click two endpoints of a known distance to compute px2m [m/pixel]."""

    def __init__(self, parent, image_path):
        super().__init__(parent)
        self.title(f'Calibration - {os.path.basename(image_path)}')
        self.result = None
        self._points = []
        self._markers = []
        self.grab_set()

        gray = _load_gray(image_path)

        fig = Figure(figsize=(7, 5))
        self._ax = fig.add_subplot(111)
        self._ax.imshow(gray, cmap='gray')
        self._ax.set_title('Click the two endpoints of a known distance')

        self._canvas = FigureCanvasTkAgg(fig, master=self)
        self._canvas.get_tk_widget().pack(fill='both', expand=True)
        NavigationToolbar2Tk(self._canvas, self).update()
        self._canvas.mpl_connect('button_press_event', self._on_click)

        bar = ttk.Frame(self)
        bar.pack(fill='x', padx=8, pady=6)
        ttk.Label(bar, text='Real distance:').pack(side='left')
        self._dist_var = tk.StringVar(value='100')
        ttk.Entry(bar, textvariable=self._dist_var, width=10).pack(
            side='left', padx=4)
        self._unit_var = tk.StringVar(value='micron')
        ttk.Combobox(bar, textvariable=self._unit_var,
                     values=['micron', 'mm', 'm'], state='readonly',
                     width=8).pack(side='left', padx=4)
        ttk.Button(bar, text='Reset', command=self._reset).pack(
            side='left', padx=4)
        ttk.Button(bar, text='OK', command=self._ok).pack(side='right', padx=4)
        ttk.Button(bar, text='Cancel', command=self.destroy).pack(
            side='right')

        self.protocol('WM_DELETE_WINDOW', self.destroy)
        self.geometry('800x640')
        self.wait_window()

    def _on_click(self, event):
        if event.inaxes != self._ax or event.xdata is None:
            return
        if len(self._points) >= 2:
            return
        self._points.append((event.xdata, event.ydata))
        m, = self._ax.plot(event.xdata, event.ydata, 'y+', markersize=12)
        self._markers.append(m)
        if len(self._points) == 2:
            (x0, y0), (x1, y1) = self._points
            line, = self._ax.plot([x0, x1], [y0, y1], 'y-', linewidth=2)
            self._markers.append(line)
        self._canvas.draw()

    def _reset(self):
        for m in self._markers:
            try:
                m.remove()
            except Exception:
                pass
        self._markers = []
        self._points = []
        self._canvas.draw()

    def _ok(self):
        if len(self._points) < 2:
            messagebox.showwarning('Warning', 'Select two points.',
                                   parent=self)
            return
        try:
            dist_units = float(self._dist_var.get())
        except ValueError:
            messagebox.showerror('Error', 'Invalid distance.', parent=self)
            return
        if dist_units <= 0:
            messagebox.showerror('Error', 'Invalid distance.', parent=self)
            return
        (x0, y0), (x1, y1) = self._points
        dist_px = np.hypot(x1 - x0, y1 - y0)
        if dist_px == 0:
            messagebox.showerror('Error', 'The two points coincide.',
                                 parent=self)
            return
        factor = {'micron': 1e-6, 'mm': 1e-3, 'm': 1.0}[self._unit_var.get()]
        self.result = (dist_units / dist_px) * factor
        self.destroy()


# =============================================================================
# Interactive dialog: freehand / rectangle crop
# =============================================================================
class CropDialog(tk.Toplevel):
    """Select a region (freehand or rectangle), crop it and save as JPG."""

    def __init__(self, parent, image_path, save_path, state):
        super().__init__(parent)
        self.title(f'Crop - {os.path.basename(image_path)}')
        self.result = None            # (area, state)
        self._state = state or {}
        self._save_path = save_path
        self._selection = {'verts': None, 'rect': None}
        self._selector = None
        self.grab_set()

        self._gray = _load_gray(image_path)
        self._img_h, self._img_w = self._gray.shape

        top = ttk.Frame(self)
        top.pack(fill='x', padx=8, pady=4)
        self._method = tk.StringVar(value='rectangle')
        ttk.Radiobutton(top, text='Rectangle', variable=self._method,
                        value='rectangle',
                        command=self._make_selector).pack(side='left')
        ttk.Radiobutton(top, text='Freehand (polygon)',
                        variable=self._method, value='freehand',
                        command=self._make_selector).pack(side='left', padx=8)

        self._use_prev = tk.BooleanVar(value=False)
        if self._state.get('mask') is not None:
            ttk.Checkbutton(top, text='Use previous crop',
                            variable=self._use_prev,
                            command=self._toggle_prev).pack(side='left',
                                                            padx=12)

        fig = Figure(figsize=(7, 5))
        self._ax = fig.add_subplot(111)
        self._ax.imshow(self._gray, cmap='gray')
        self._ax.set_title('Select the area to crop')
        self._canvas = FigureCanvasTkAgg(fig, master=self)
        self._canvas.get_tk_widget().pack(fill='both', expand=True)
        NavigationToolbar2Tk(self._canvas, self).update()

        bar = ttk.Frame(self)
        bar.pack(fill='x', padx=8, pady=6)
        ttk.Button(bar, text='OK', command=self._ok).pack(side='right', padx=4)
        ttk.Button(bar, text='Cancel', command=self.destroy).pack(
            side='right')

        self._make_selector()
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        self.geometry('800x680')
        self.wait_window()

    def _toggle_prev(self):
        if self._use_prev.get() and self._selector is not None:
            self._selector.set_active(False)
        elif self._selector is not None:
            self._selector.set_active(True)

    def _make_selector(self):
        if self._selector is not None:
            try:
                self._selector.set_active(False)
                self._selector.disconnect_events()
            except Exception:
                pass
            self._selector = None
        self._selection = {'verts': None, 'rect': None}

        if self._method.get() == 'freehand':
            self._selector = PolygonSelector(self._ax, self._on_poly)
        else:
            self._selector = RectangleSelector(
                self._ax, self._on_rect, useblit=True, interactive=True)
        self._canvas.draw()

    def _on_poly(self, verts):
        self._selection['verts'] = verts

    def _on_rect(self, eclick, erelease):
        x0, y0 = eclick.xdata, eclick.ydata
        x1, y1 = erelease.xdata, erelease.ydata
        self._selection['rect'] = (min(x0, x1), min(y0, y1),
                                   abs(x1 - x0), abs(y1 - y0))

    def _compute_mask(self):
        if self._use_prev.get() and self._state.get('mask') is not None:
            prev = self._state['mask']
            mask = np.zeros((self._img_h, self._img_w), dtype=bool)
            hh = min(self._img_h, prev.shape[0])
            ww = min(self._img_w, prev.shape[1])
            mask[:hh, :ww] = prev[:hh, :ww]
            return mask
        if self._selection['verts']:
            yy, xx = np.mgrid[0:self._img_h, 0:self._img_w]
            pts = np.column_stack((xx.ravel(), yy.ravel()))
            path = MplPath(self._selection['verts'])
            return path.contains_points(pts).reshape(self._img_h, self._img_w)
        if self._selection['rect']:
            x, y, rw, rh = self._selection['rect']
            x, y = int(round(x)), int(round(y))
            rw, rh = int(round(rw)), int(round(rh))
            mask = np.zeros((self._img_h, self._img_w), dtype=bool)
            mask[max(0, y):y + rh, max(0, x):x + rw] = True
            return mask
        return None

    def _ok(self):
        from PIL import Image
        mask = self._compute_mask()
        if mask is None or not mask.any():
            messagebox.showwarning('Warning', 'No area selected.',
                                   parent=self)
            return
        area = int(mask.sum())

        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        ymin, ymax = np.where(rows)[0][[0, -1]]
        xmin, xmax = np.where(cols)[0][[0, -1]]
        cropped = self._gray[ymin:ymax + 1, xmin:xmax + 1].copy()
        mask_c = mask[ymin:ymax + 1, xmin:xmax + 1]
        cropped[~mask_c] = 255

        os.makedirs(os.path.dirname(self._save_path), exist_ok=True)
        base, _ = os.path.splitext(self._save_path)
        save_path = base + '.jpg'
        Image.fromarray(cropped).save(save_path, quality=100)

        self._state = {'mask': mask}
        self.result = (area, self._state)
        self.destroy()


# =============================================================================
# Interactive dialog: intensity range
# =============================================================================
class IntensityDialog(tk.Toplevel):
    """Draw a line, inspect the intensity profile and enter min/max."""

    def __init__(self, parent, image_path):
        super().__init__(parent)
        self.title(f'Intensity - {os.path.basename(image_path)}')
        self.result = None
        self._points = []
        self._markers = []
        self.grab_set()

        self._gray = _load_gray(image_path)

        fig = Figure(figsize=(9, 4.5))
        self._ax = fig.add_subplot(121)
        self._ax.imshow(self._gray, cmap='gray')
        self._ax.set_title('Click the start and end of a line')
        self._axp = fig.add_subplot(122)
        self._axp.set_title('Intensity profile')
        self._axp.set_xlabel('Relative position')
        self._axp.set_ylabel('Greyscale value')

        self._canvas = FigureCanvasTkAgg(fig, master=self)
        self._canvas.get_tk_widget().pack(fill='both', expand=True)
        NavigationToolbar2Tk(self._canvas, self).update()
        self._canvas.mpl_connect('button_press_event', self._on_click)

        bar = ttk.Frame(self)
        bar.pack(fill='x', padx=8, pady=6)
        ttk.Label(bar, text='Min:').pack(side='left')
        self._min_var = tk.StringVar(value='0')
        ttk.Entry(bar, textvariable=self._min_var, width=8).pack(
            side='left', padx=4)
        ttk.Label(bar, text='Max:').pack(side='left')
        self._max_var = tk.StringVar(value='100')
        ttk.Entry(bar, textvariable=self._max_var, width=8).pack(
            side='left', padx=4)
        ttk.Button(bar, text='Reset', command=self._reset).pack(
            side='left', padx=8)
        ttk.Button(bar, text='OK', command=self._ok).pack(side='right', padx=4)
        ttk.Button(bar, text='Cancel', command=self.destroy).pack(
            side='right')

        self.protocol('WM_DELETE_WINDOW', self.destroy)
        self.geometry('980x560')
        self.wait_window()

    def _on_click(self, event):
        if event.inaxes != self._ax or event.xdata is None:
            return
        if len(self._points) >= 2:
            return
        self._points.append((event.xdata, event.ydata))
        m, = self._ax.plot(event.xdata, event.ydata, 'r+', markersize=12)
        self._markers.append(m)
        if len(self._points) == 2:
            from skimage.measure import profile_line
            (x0, y0), (x1, y1) = self._points
            line, = self._ax.plot([x0, x1], [y0, y1], 'r-', linewidth=1.5)
            self._markers.append(line)
            prof = profile_line(self._gray, (y0, x0), (y1, x1))
            self._axp.clear()
            self._axp.plot(prof, 'k')
            self._axp.set_title('Intensity profile')
            self._axp.set_xlabel('Relative position')
            self._axp.set_ylabel('Greyscale value')
        self._canvas.draw()

    def _reset(self):
        for m in self._markers:
            try:
                m.remove()
            except Exception:
                pass
        self._markers = []
        self._points = []
        self._axp.clear()
        self._canvas.draw()

    def _ok(self):
        try:
            imin = float(self._min_var.get())
            imax = float(self._max_var.get())
        except ValueError:
            messagebox.showerror('Error', 'Invalid values.', parent=self)
            return
        self.result = (imin, imax)
        self.destroy()


# =============================================================================
# Shared group model helpers
# =============================================================================
def new_image(path=''):
    """Create an empty image record used by the shared group model."""
    return {
        'path': path,          # original input image (PreProcess input)
        'px2m': None,          # m/pixel
        'crop_area': None,     # pixel^2
        'imin': 0.0,           # intensity range min
        'imax': 100.0,         # intensity range max
        'crop_file': path,     # cropped image (Analyze input)
        'measure_file': None,  # measurementsTable_XXX.csv (Analyze output)
        'stereo_file': None,   # measurementsStereoTable_XXX.csv (Stereology)
        'type': '2D',          # 2D / 3D / 3Dstereo (Properties)
        'D': None,             # depth for 3D measurements
    }


def new_group(name):
    """Create a group record used by the shared group model."""
    return {
        'name': name,
        'images': [],
        'nbins_density': 16,     # bin-edge grid size, density analysis
        'nbins_exceedance': 22,  # bin-edge grid size, exceedance analysis
    }


def _fmt_px2m(v):
    return f'{v:.6e}' if isinstance(v, (int, float)) else ''


def _fmt_area(v):
    return f'{v:.0f}' if isinstance(v, (int, float)) else ''


# =============================================================================
# Base class: a group/file tree shared across the tabs
# =============================================================================
class GroupTreeTab(ttk.Frame):
    """
    Common scaffolding for the four tabs.

    Subclasses must define:
      * ``COLUMNS``      : tuple of (id, heading, width)
      * ``_file_values`` : (self, img) -> tuple of column strings
      * ``_add_file``    : (self, group) -> add one or more images
      * ``_edit_file``   : (self, group, img) -> edit an image (optional)
      * ``_run``         : the module run action
    """

    COLUMNS = ()
    RUN_LABEL = 'Run'
    GROUP_EDIT_LABEL = 'Rename'

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        pad = dict(padx=8, pady=4)

        self._info = ttk.Label(self, wraplength=780, justify='left', text='')
        self._info.pack(fill='x', **pad)

        self._build_options()   # optional extra controls (subclass hook)

        mid = ttk.LabelFrame(self, text='Groups and files')
        mid.pack(fill='both', expand=True, **pad)
        cols = tuple(c[0] for c in self.COLUMNS)
        self._tree = ttk.Treeview(mid, columns=cols, show='tree headings',
                                  height=9)
        self._tree.heading('#0', text='Group / File')
        self._tree.column('#0', width=320)
        for cid, head, width in self.COLUMNS:
            self._tree.heading(cid, text=head)
            self._tree.column(cid, width=width, anchor='center')
        self._tree.pack(side='left', fill='both', expand=True)
        sb = ttk.Scrollbar(mid, orient='vertical', command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        sb.pack(side='left', fill='y')

        bf = ttk.Frame(mid)
        bf.pack(side='left', fill='y', padx=6)
        ttk.Button(bf, text='+ Group', command=self._on_add_group).pack(
            fill='x', pady=2)
        ttk.Button(bf, text=self.GROUP_EDIT_LABEL,
                   command=self._on_edit_group).pack(fill='x', pady=2)
        ttk.Button(bf, text='- Group', command=self._on_remove_group).pack(
            fill='x', pady=2)
        ttk.Separator(bf).pack(fill='x', pady=8)
        ttk.Button(bf, text='+ File', command=self._on_add_file).pack(
            fill='x', pady=2)
        if self._supports_edit():
            ttk.Button(bf, text='Edit File', command=self._on_edit_file).pack(
                fill='x', pady=2)
        ttk.Button(bf, text='- File', command=self._on_remove_file).pack(
            fill='x', pady=2)

        run = ttk.Frame(self)
        run.pack(fill='x', **pad)
        self._run_btn = ttk.Button(run, text=self.RUN_LABEL, command=self._run)
        self._run_btn.pack(side='left')

    # ---- subclass hooks -----------------------------------------------------
    def _build_options(self):
        """Optional extra controls above the tree."""

    def _supports_edit(self):
        return True

    def _file_values(self, img):
        raise NotImplementedError

    def _add_file(self, group):
        raise NotImplementedError

    def _edit_file(self, group, img):
        pass

    def _run(self):
        raise NotImplementedError

    # ---- shared model access ------------------------------------------------
    @property
    def groups(self):
        return self.app.groups

    def _selected(self):
        """Return (group_index, image_index or None) for the selection."""
        sel = self._tree.selection()
        if not sel:
            return None, None
        iid = sel[0]
        if iid.startswith('g') and '_f' not in iid:
            return int(iid[1:]), None
        if '_f' in iid:
            g, f = iid.split('_f')
            return int(g[1:]), int(f)
        return None, None

    # ---- group / file management -------------------------------------------
    def _on_add_group(self):
        name = f'Group {len(self.groups) + 1}'
        self.groups.append(new_group(name))
        self.reload()

    def _on_edit_group(self):
        gi, _ = self._selected()
        if gi is None:
            return
        name = simpledialog.askstring('Rename', 'Group name:',
                                      initialvalue=self.groups[gi]['name'],
                                      parent=self.app)
        if name:
            self.groups[gi]['name'] = name
            self.reload()

    def _on_remove_group(self):
        gi, _ = self._selected()
        if gi is None:
            return
        self.groups.pop(gi)
        self.reload()

    def _current_group(self):
        gi, _ = self._selected()
        if gi is None:
            if not self.groups:
                self.groups.append(new_group('Group 1'))
                return self.groups[0]
            messagebox.showwarning('Warning', 'Select a group first.')
            return None
        return self.groups[gi]

    def _on_add_file(self):
        group = self._current_group()
        if group is None:
            return
        self._add_file(group)
        self.reload()

    def _on_edit_file(self):
        gi, fi = self._selected()
        if gi is None or fi is None:
            return
        self._edit_file(self.groups[gi], self.groups[gi]['images'][fi])
        self.reload()

    def _on_remove_file(self):
        gi, fi = self._selected()
        if gi is None or fi is None:
            return
        self.groups[gi]['images'].pop(fi)
        self.reload()

    # ---- rendering ----------------------------------------------------------
    def _file_label(self, img):
        for key in ('measure_file', 'stereo_file', 'crop_file', 'path'):
            if img.get(key):
                return os.path.basename(img[key])
        return '(empty)'

    def reload(self):
        for it in self._tree.get_children():
            self._tree.delete(it)
        n_cols = len(self.COLUMNS)
        for gi, g in enumerate(self.groups):
            self._tree.insert('', 'end', iid=f'g{gi}', text=g['name'],
                              values=('',) * n_cols, open=True)
            for fi, img in enumerate(g['images']):
                self._tree.insert(f'g{gi}', 'end', iid=f'g{gi}_f{fi}',
                                  text=self._file_label(img),
                                  values=self._file_values(img))

    # ---- run helpers --------------------------------------------------------
    def _flat_images(self):
        """Return (flat list of images, list of group dicts with indices)."""
        flat = []
        groups_idx = []
        for g in self.groups:
            if not g['images']:
                continue
            indices = list(range(len(flat), len(flat) + len(g['images'])))
            flat.extend(g['images'])
            groups_idx.append({'name': g['name'], 'indices': indices})
        return flat, groups_idx


# =============================================================================
# PreProcess tab
# =============================================================================
class PreProcessTab(GroupTreeTab):

    COLUMNS = (('px2m', 'm/pixel', 130),
               ('crop_area', 'cropArea', 120),
               ('imin', 'Int. min', 80),
               ('imax', 'Int. max', 80))
    RUN_LABEL = 'Run PreProcess'

    def _build_options(self):
        self._info.configure(
            text=('Spatial calibration of the image, by measuring the pixel distance corresponding to a known physical length; '
                  'Cropping a region of the image; '
                  'Calculation of the intensity threshold for image binarisation.'))
        opt = ttk.LabelFrame(self, text='Operations')
        opt.pack(fill='x', padx=8, pady=4)
        self._calib = tk.BooleanVar(value=True)
        self._crop = tk.BooleanVar(value=True)
        self._intensity = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt, text='Calibration', variable=self._calib).pack(
            side='left', padx=8, pady=4)
        ttk.Checkbutton(opt, text='Crop', variable=self._crop).pack(
            side='left', padx=8, pady=4)
        ttk.Checkbutton(opt, text='Intensity range',
                        variable=self._intensity).pack(side='left', padx=8,
                                                        pady=4)

    def _supports_edit(self):
        return False

    def _file_values(self, img):
        return (_fmt_px2m(img.get('px2m')), _fmt_area(img.get('crop_area')),
                f'{img.get("imin", 0):g}', f'{img.get("imax", 100):g}')

    def _file_label(self, img):
        return os.path.basename(img.get('path') or '(empty)')

    def _add_file(self, group):
        paths = filedialog.askopenfilenames(title='Select images',
                                            filetypes=IMAGE_TYPES)
        for p in paths:
            group['images'].append(new_image(p))

    def _run(self):
        flat, groups_idx = self._flat_images()
        if not flat:
            messagebox.showwarning('Warning', 'Add at least one image.')
            return
        out_dir = self.app.output_dir()
        if not out_dir:
            messagebox.showwarning('Warning', 'Set the output folder.')
            return

        input_dir = [os.path.dirname(im['path']) for im in flat]
        input_file = [os.path.basename(im['path']) for im in flat]
        img_data = {
            'input_dir': input_dir,
            'input_file': input_file,
            'calibration_input_file': list(input_file),
            'output_dir': out_dir,
        }
        preprocess = {
            'calibration': self._calib.get(),
            'crop': self._crop.get(),
            'intensityRange': self._intensity.get(),
        }

        interactors = {
            'calibrate': lambda path: CalibrationDialog(self.app, path).result,
            'intensity': lambda path: (IntensityDialog(self.app, path).result
                                       or (0.0, 0.0)),
        }

        def crop_interactor(path, save_path, state):
            dlg = CropDialog(self.app, path, save_path, state)
            if dlg.result is None:
                return 0, state
            return dlg.result
        interactors['crop'] = crop_interactor

        # PreProcess is interactive -> run on the main thread.
        self._run_btn.configure(state='disabled')
        self.app.clear_log()
        redirector = _LogRedirector(self.app.log)
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = redirector
        try:
            px2m, crop_area, i_range = run_preprocessing(
                preprocess, img_data, interactors)
        except Exception as exc:
            import traceback
            tb = traceback.format_exc()
            print(tb)
            sys.stdout, sys.stderr = old_out, old_err
            self._run_btn.configure(state='normal')
            messagebox.showerror('Error', f'{type(exc).__name__}: {exc}\n\n{tb}')
            return
        finally:
            sys.stdout, sys.stderr = old_out, old_err
            self._run_btn.configure(state='normal')

        # ---- Store results into the shared model ---------------------------
        crop_dir = os.path.join(out_dir, 'CropImages')
        for k, im in enumerate(flat):
            if preprocess['calibration'] and px2m is not None and k < px2m.size:
                im['px2m'] = float(px2m[k])
            if preprocess['crop'] and crop_area is not None \
                    and k < crop_area.size:
                im['crop_area'] = float(crop_area[k])
            if preprocess['intensityRange'] and i_range is not None:
                im['imin'] = float(i_range[0, k])
                im['imax'] = float(i_range[1, k])
            if preprocess['crop']:
                name = os.path.splitext(os.path.basename(im['path']))[0]
                im['crop_file'] = os.path.join(
                    crop_dir, f'{name}_{k + 1:03d}.jpg')
            else:
                im['crop_file'] = im['path']

        self.app.reload_all()
        messagebox.showinfo(
            'Done', 'PreProcess completed.\nThe Analyze, Stereology and '
            'Properties tabs have been updated.')


# =============================================================================
# Analyze tab
# =============================================================================
class AnalyzeFileDialog(tk.Toplevel):

    def __init__(self, parent, title='File', initial=None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.result = None
        pad = dict(padx=8, pady=4)

        ttk.Label(self, text='File:').grid(row=0, column=0, sticky='e', **pad)
        self._file = tk.StringVar(
            value=initial.get('crop_file', '') if initial else '')
        ttk.Entry(self, textvariable=self._file, width=48).grid(
            row=0, column=1, **pad)
        ttk.Button(self, text='Browse...', command=self._browse).grid(
            row=0, column=2, **pad)

        ttk.Label(self, text='m/pixel:').grid(
            row=1, column=0, sticky='e', **pad)
        self._px2m = tk.StringVar(
            value=str(initial['px2m']) if initial and initial.get('px2m')
            is not None else '')
        ttk.Entry(self, textvariable=self._px2m, width=18).grid(
            row=1, column=1, sticky='w', **pad)

        ttk.Label(self, text='Intensity min:').grid(
            row=2, column=0, sticky='e', **pad)
        self._min = tk.StringVar(
            value=str(initial.get('imin', 0)) if initial else '0')
        ttk.Entry(self, textvariable=self._min, width=18).grid(
            row=2, column=1, sticky='w', **pad)

        ttk.Label(self, text='Intensity max:').grid(
            row=3, column=0, sticky='e', **pad)
        self._max = tk.StringVar(
            value=str(initial.get('imax', 100)) if initial else '100')
        ttk.Entry(self, textvariable=self._max, width=18).grid(
            row=3, column=1, sticky='w', **pad)

        bf = ttk.Frame(self)
        bf.grid(row=4, column=0, columnspan=3, pady=10)
        ttk.Button(bf, text='OK', command=self._ok).pack(side='left', padx=8)
        ttk.Button(bf, text='Cancel', command=self.destroy).pack(
            side='left', padx=8)
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        self.wait_window()

    def _browse(self):
        p = filedialog.askopenfilename(title='Select image',
                                       filetypes=IMAGE_TYPES)
        if p:
            self._file.set(p)

    def _ok(self):
        try:
            px2m = float(self._px2m.get())
            imin = float(self._min.get())
            imax = float(self._max.get())
        except ValueError:
            messagebox.showerror('Error', 'm/pixel and intensity must be '
                                 'numbers.', parent=self)
            return
        if not self._file.get():
            messagebox.showerror('Error', 'Select a file.', parent=self)
            return
        self.result = {'crop_file': self._file.get(), 'px2m': px2m,
                       'imin': imin, 'imax': imax}
        self.destroy()


class AnalyzeTab(GroupTreeTab):

    COLUMNS = (('px2m', 'm/pixel', 130),
               ('imin', 'Int. min', 80),
               ('imax', 'Int. max', 80))
    RUN_LABEL = 'Run Analyze'

    def _build_options(self):
        self._info.configure(
            text=('Threshold-based segmentation of the image and '
                  'measurement of particle geometric properties.'))

    def _file_values(self, img):
        return (_fmt_px2m(img.get('px2m')),
                f'{img.get("imin", 0):g}', f'{img.get("imax", 100):g}')

    def _file_label(self, img):
        return os.path.basename(img.get('crop_file') or img.get('path')
                                or '(empty)')

    def _add_file(self, group):
        dlg = AnalyzeFileDialog(self.app, 'Add image')
        if dlg.result:
            im = new_image(dlg.result['crop_file'])
            im.update(dlg.result)
            group['images'].append(im)

    def _edit_file(self, group, img):
        dlg = AnalyzeFileDialog(self.app, 'Edit image', img)
        if dlg.result:
            img.update(dlg.result)

    def _run(self):
        flat, groups_idx = self._flat_images()
        if not flat:
            messagebox.showwarning('Warning', 'Add at least one image.')
            return
        out_dir = self.app.output_dir()
        crop_files = [im.get('crop_file') or im.get('path') for im in flat]
        if any(not f for f in crop_files):
            messagebox.showwarning('Warning', 'Some images have no file.')
            return
        input_dir = os.path.commonpath([os.path.dirname(f)
                                        for f in crop_files])
        img_data = {
            'input_dir': input_dir,
            'input_file': [os.path.relpath(f, input_dir) for f in crop_files],
            'output_dir': out_dir,
            'px2m': [im.get('px2m') or 0.0 for im in flat],
            'groups': groups_idx,
        }
        technique = {'range': [[im.get('imin', 0), im.get('imax', 100)]
                               for im in flat]}

        def on_done():
            measure_dir = os.path.join(out_dir, 'Measurements')
            for k, im in enumerate(flat):
                im['measure_file'] = os.path.join(
                    measure_dir, f'measurementsTable_{k + 1:03d}.csv')
                im['stereo_file'] = None
            self.app.reload_all()
            messagebox.showinfo(
                'Done', 'Analyze completed.\nThe Stereology and Properties '
                'tabs have been updated.')

        self.app.run_worker(lambda: run_analyze(img_data, technique),
                            self._run_btn, on_done)


# =============================================================================
# Stereology tab
# =============================================================================
class StereologyTab(GroupTreeTab):

    COLUMNS = (('file', 'Measurement file', 260),)
    RUN_LABEL = 'Run Stereology'

    def _build_options(self):
        self._info.configure(
            text=('Stereological conversion of the 2D measures into 3D size distributions, assuming spherical particles.'))

    def _supports_edit(self):
        return False

    def _file_values(self, img):
        return ('',)

    def _file_label(self, img):
        for key in ('measure_file', 'path'):
            if img.get(key):
                return os.path.basename(img[key])
        return '(empty)'

    def _add_file(self, group):
        paths = filedialog.askopenfilenames(
            title='Select measurement tables', filetypes=CSV_TYPES)
        for p in paths:
            im = new_image(p)
            im['measure_file'] = p
            group['images'].append(im)

    def _run(self):
        if run_stereology is None:
            messagebox.showerror(
                'Missing dependency',
                'The Stereology module requires the "pysizeunfolder" '
                'package.\n\nInstall it with:\n'
                'pip install git+https://github.com/thomasvdj/pysizeunfolder')
            return
        flat, groups_idx = self._flat_images()
        measure_files = [im.get('measure_file') for im in flat]
        if not flat or any(not f for f in measure_files):
            messagebox.showwarning('Warning', 'Add at least one measurement '
                                   'file (run Analyze first or add manually).')
            return
        out_dir = self.app.output_dir()
        input_dir = os.path.commonpath([os.path.dirname(f)
                                        for f in measure_files])
        measure_data = {
            'input_dir': input_dir,
            'input_file': [os.path.relpath(f, input_dir)
                           for f in measure_files],
            'output_dir': out_dir,
        }

        def on_done():
            measure_dir = os.path.join(out_dir, 'Measurements')
            for im in flat:
                stem = os.path.splitext(
                    os.path.basename(im['measure_file']))[0]
                suffix = stem[-3:]
                im['stereo_file'] = os.path.join(
                    measure_dir, f'measurementsStereoTable_{suffix}.csv')
                im['type'] = '3Dstereo'
            self.app.reload_all()
            messagebox.showinfo(
                'Done', 'Stereology completed.\nThe Properties tab now uses '
                'the measurementsStereoTable files.')

        self.app.run_worker(lambda: run_stereology(measure_data),
                            self._run_btn, on_done)


# =============================================================================
# Properties tab
# =============================================================================
class PropFileDialog(tk.Toplevel):

    def __init__(self, parent, title='File', initial=None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.result = None
        pad = dict(padx=8, pady=4)
        r = 0

        ttk.Label(self, text='File:').grid(row=r, column=0, sticky='e', **pad)
        init_file = ''
        if initial:
            init_file = initial.get('measure_file') or initial.get('path') or ''
        self._file = tk.StringVar(value=init_file)
        ttk.Entry(self, textvariable=self._file, width=48).grid(
            row=r, column=1, **pad)
        ttk.Button(self, text='Browse...', command=self._browse).grid(
            row=r, column=2, **pad)

        r += 1
        ttk.Label(self, text='Type:').grid(row=r, column=0, sticky='e', **pad)
        self._type = tk.StringVar(value=initial['type'] if initial else '2D')
        ttk.Combobox(self, textvariable=self._type,
                     values=['2D', '3D', '3Dstereo'], state='readonly',
                     width=12).grid(row=r, column=1, sticky='w', **pad)

        r += 1
        ttk.Label(self, text='m/pixel:').grid(
            row=r, column=0, sticky='e', **pad)
        self._px2m = tk.StringVar(
            value=str(initial['px2m']) if initial and initial.get('px2m')
            is not None else '')
        ttk.Entry(self, textvariable=self._px2m, width=18).grid(
            row=r, column=1, sticky='w', **pad)

        r += 1
        ttk.Label(self, text='cropArea [pixel^2]:').grid(
            row=r, column=0, sticky='e', **pad)
        self._area = tk.StringVar(
            value=str(initial['crop_area']) if initial
            and initial.get('crop_area') is not None else '')
        ttk.Entry(self, textvariable=self._area, width=18).grid(
            row=r, column=1, sticky='w', **pad)

        r += 1
        ttk.Label(self, text='Depth D (3D only):').grid(
            row=r, column=0, sticky='e', **pad)
        self._depth = tk.StringVar(
            value=str(initial.get('D')) if initial and initial.get('D')
            is not None else '')
        ttk.Entry(self, textvariable=self._depth, width=18).grid(
            row=r, column=1, sticky='w', **pad)

        r += 1
        bf = ttk.Frame(self)
        bf.grid(row=r, column=0, columnspan=3, pady=10)
        ttk.Button(bf, text='OK', command=self._ok).pack(side='left', padx=8)
        ttk.Button(bf, text='Cancel', command=self.destroy).pack(
            side='left', padx=8)
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        self.wait_window()

    def _browse(self):
        p = filedialog.askopenfilename(title='Select measurement file',
                                       filetypes=CSV_TYPES)
        if p:
            self._file.set(p)

    def _ok(self):
        try:
            px2m = float(self._px2m.get())
            area = float(self._area.get())
        except ValueError:
            messagebox.showerror('Error', 'm/pixel and cropArea must be '
                                 'numbers.', parent=self)
            return
        if not self._file.get():
            messagebox.showerror('Error', 'Select a file.', parent=self)
            return
        self.result = {'measure_file': self._file.get(),
                       'type': self._type.get(),
                       'px2m': px2m, 'crop_area': area}
        d = self._depth.get().strip()
        if d:
            try:
                self.result['D'] = float(d)
            except ValueError:
                messagebox.showerror('Error', 'Depth D must be a number.',
                                     parent=self)
                return
        self.destroy()


# =============================================================================
# Interactive dialog: fractal index (roll-off + cut-off selection)
# =============================================================================
class FractalIndexDialog(tk.Toplevel):
    """Interactive dialog replicating fractal.m + selectPoint.m.

    Step 1: user clicks the roll-off point on the exceedance plot.
    Step 2: user chooses cut-off method (Select point / Automatic search).
    Step 3 (if manual): user clicks the cut-off point.

    Returns a dict with ``rolloff_idx`` and ``Dc``, or ``None`` if cancelled.
    """

    def __init__(self, parent, x, y, group_name):
        super().__init__(parent)
        self.title(f'Fractal Index - {group_name}')
        self.result = None
        self._x = x
        self._y = y
        self._group_name = group_name
        self._phase = 'rolloff'        # 'rolloff' -> 'method' -> 'cutoff'
        self._rolloff_idx = None
        self._markers = []
        self.grab_set()

        fig = Figure(figsize=(7, 5))
        self._ax = fig.add_subplot(111)

        self._canvas = FigureCanvasTkAgg(fig, master=self)
        self._canvas.get_tk_widget().pack(fill='both', expand=True)
        NavigationToolbar2Tk(self._canvas, self).update()
        self._canvas.mpl_connect('button_press_event', self._on_click)

        self._plot_data()
        self._ax.set_title('Select first point from which roll-off starts',
                           fontsize=11, fontweight='bold')
        self._canvas.draw()

        # Button bar (hidden initially, shown in method phase)
        self._bar = ttk.Frame(self)
        self._bar.pack(fill='x', padx=8, pady=6)
        self._status = tk.StringVar(value='')
        ttk.Label(self._bar, textvariable=self._status).pack(side='left')
        self._btn_select = ttk.Button(self._bar, text='Select point',
                                      command=self._choose_manual)
        self._btn_auto = ttk.Button(self._bar, text='Automatic search',
                                    command=self._choose_auto)
        self._btn_cancel = ttk.Button(self._bar, text='Cancel',
                                      command=self.destroy)
        self._btn_cancel.pack(side='right')
        self._btn_auto.pack(side='right', padx=4)
        self._btn_select.pack(side='right', padx=4)
        self._btn_select.pack_forget()
        self._btn_auto.pack_forget()

        self.protocol('WM_DELETE_WINDOW', self.destroy)
        self.geometry('750x600')
        self.wait_window()

    def _plot_data(self):
        self._ax.clear()
        self._ax.plot(np.log10(self._x) + 6, np.log10(self._y),
                      's', color='red', markersize=4, label='Data')
        self._ax.set_xlabel(r'$\log_{10}$ of equivalent diameter ($\mu$m)')
        self._ax.set_ylabel(r'$\log_{10}$ of exceedance')
        self._ax.legend(loc='lower left', fontsize=8)
        self._canvas.draw()

    def _snap_to_data(self, xclick, yclick):
        x_val = 10.0 ** (xclick - 6)
        y_val = 10.0 ** yclick
        dist = (self._x - x_val) ** 2 + (self._y - y_val) ** 2
        idx = int(np.argmin(dist))
        return idx

    def _on_click(self, event):
        if event.inaxes != self._ax or event.xdata is None:
            return
        if self._phase == 'rolloff':
            idx = self._snap_to_data(event.xdata, event.ydata)
            self._rolloff_idx = idx
            m, = self._ax.plot(np.log10(self._x[idx]) + 6,
                               np.log10(self._y[idx]),
                               'o', color='blue', markersize=10,
                               label='Roll-off point')
            self._markers.append(m)
            self._canvas.draw()
            self._phase = 'method'
            self._ax.set_title('')
            self._status.set('Roll-off selected. Choose cut-off method:')
            self._btn_select.pack(side='right', padx=4)
            self._btn_auto.pack(side='right', padx=4)
        elif self._phase == 'cutoff':
            idx = self._snap_to_data(event.xdata, event.ydata)
            Dc = float(self._x[idx])
            m, = self._ax.plot(np.log10(Dc) + 6, np.log10(self._y[idx]),
                               '+', color='red', markersize=12,
                               markeredgewidth=2, label='Cut-off point')
            self._markers.append(m)
            self._canvas.draw()
            self.result = {'rolloff_idx': self._rolloff_idx, 'Dc': Dc}
            self.destroy()

    def _choose_manual(self):
        self._phase = 'cutoff'
        self._btn_select.pack_forget()
        self._btn_auto.pack_forget()
        self._status.set('Select cut-off point on the plot')
        self._ax.set_title('Select cut-off point',
                           fontsize=11, fontweight='bold')
        self._canvas.draw()

    def _choose_auto(self):
        from src.bubble_properties.fractal_index import _auto_cutoff
        x_trunc = self._x[:self._rolloff_idx]
        y_trunc = self._y[:self._rolloff_idx]
        Dc = _auto_cutoff(x_trunc, y_trunc)
        m, = self._ax.plot(np.log10(Dc) + 6,
                           np.log10(self._y[np.argmin(np.abs(self._x - Dc))]),
                           '+', color='red', markersize=12,
                           markeredgewidth=2, label='Cut-off point (auto)')
        self._markers.append(m)
        self._canvas.draw()
        self.result = {'rolloff_idx': self._rolloff_idx, 'Dc': float(Dc)}
        self.destroy()


# =============================================================================
# Dialog: edit group (name + bin counts used by the Properties analysis)
# =============================================================================
class EditGroupDialog(tk.Toplevel):

    def __init__(self, parent, group):
        super().__init__(parent)
        self.title('Edit Group')
        self.resizable(False, False)
        self.grab_set()
        self.result = None
        pad = dict(padx=8, pady=4)

        ttk.Label(self, text='Group name:').grid(
            row=0, column=0, sticky='e', **pad)
        self._name_var = tk.StringVar(value=group.get('name', ''))
        ttk.Entry(self, textvariable=self._name_var, width=30).grid(
            row=0, column=1, **pad)

        ttk.Label(self, text='N bins density:').grid(
            row=1, column=0, sticky='e', **pad)
        self._nbins_d = tk.StringVar(
            value=str(group.get('nbins_density', 16)))
        ttk.Entry(self, textvariable=self._nbins_d, width=18).grid(
            row=1, column=1, sticky='w', **pad)

        ttk.Label(self, text='N bins exceedance:').grid(
            row=2, column=0, sticky='e', **pad)
        self._nbins_e = tk.StringVar(
            value=str(group.get('nbins_exceedance', 22)))
        ttk.Entry(self, textvariable=self._nbins_e, width=18).grid(
            row=2, column=1, sticky='w', **pad)

        bf = ttk.Frame(self)
        bf.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(bf, text='OK', command=self._ok).pack(side='left', padx=8)
        ttk.Button(bf, text='Cancel', command=self.destroy).pack(
            side='left', padx=8)
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        self.wait_window()

    def _ok(self):
        name = self._name_var.get().strip()
        if not name:
            messagebox.showerror('Error', 'Group name cannot be empty.',
                                 parent=self)
            return
        try:
            nbins_d = int(self._nbins_d.get())
            nbins_e = int(self._nbins_e.get())
        except ValueError:
            messagebox.showerror('Error', 'N bins values must be integers.',
                                 parent=self)
            return
        if nbins_d < 3 or nbins_e < 3:
            messagebox.showerror('Error', 'N bins values must be >= 3.',
                                 parent=self)
            return
        self.result = {'name': name, 'nbins_density': nbins_d,
                       'nbins_exceedance': nbins_e}
        self.destroy()


class PropertiesTab(GroupTreeTab):

    COLUMNS = (('type', 'Type', 80),
               ('px2m', 'm/pixel', 130),
               ('crop_area', 'cropArea', 120))
    RUN_LABEL = 'Run Properties'
    GROUP_EDIT_LABEL = 'Edit Group'

    def _build_options(self):
        self._info.configure(
            text=('Statistical analysis of the size distributions.'))
        opt = ttk.Frame(self)
        opt.pack(fill='x', padx=8, pady=4)
        ttk.Label(opt, text='Minimisation method:').pack(side='left')
        self._method = tk.StringVar(value='fmincon')
        ttk.Combobox(opt, textvariable=self._method,
                     values=['fmincon', 'simplex'], state='readonly',
                     width=12).pack(side='left', padx=6)
        self._fractal = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt, text='Fractal index (Otsuki, 1998)',
                        variable=self._fractal).pack(side='left', padx=16)

    def _prop_file(self, img):
        """Prefer the stereology output over the analyze measurement file."""
        return img.get('stereo_file') or img.get('measure_file') or \
            img.get('path')

    def _file_label(self, img):
        f = self._prop_file(img)
        return os.path.basename(f) if f else '(empty)'

    def _file_values(self, img):
        return (img.get('type', '2D'), _fmt_px2m(img.get('px2m')),
                _fmt_area(img.get('crop_area')))

    def _add_file(self, group):
        dlg = PropFileDialog(self.app, 'Add file')
        if dlg.result:
            im = new_image(dlg.result['measure_file'])
            im['measure_file'] = dlg.result['measure_file']
            im['type'] = dlg.result['type']
            im['px2m'] = dlg.result['px2m']
            im['crop_area'] = dlg.result['crop_area']
            if 'D' in dlg.result:
                im['D'] = dlg.result['D']
            group['images'].append(im)

    def _edit_file(self, group, img):
        dlg = PropFileDialog(self.app, 'Edit file', img)
        if dlg.result:
            img['measure_file'] = dlg.result['measure_file']
            img['type'] = dlg.result['type']
            img['px2m'] = dlg.result['px2m']
            img['crop_area'] = dlg.result['crop_area']
            img['D'] = dlg.result.get('D')

    def _on_edit_group(self):
        gi, _ = self._selected()
        if gi is None:
            return
        dlg = EditGroupDialog(self.app, self.groups[gi])
        if dlg.result:
            self.groups[gi].update(dlg.result)
            self.reload()

    def _run(self):
        valid = [g for g in self.groups if g['images']]
        if not valid:
            messagebox.showwarning('Warning', 'Add at least one file.')
            return

        all_files = [self._prop_file(im) for g in valid for im in g['images']]
        if any(not f for f in all_files):
            messagebox.showwarning('Warning', 'Some files are missing '
                                   '(run Analyze or add them manually).')
            return
        input_dir = os.path.commonpath([os.path.dirname(f)
                                        for f in all_files])

        input_file, types, px2m, crop_area, depth = [], [], [], [], []
        group_names = []
        has_depth = False
        for g in valid:
            group_names.append(g['name'])
            gf = g['images']
            input_file.append([os.path.relpath(self._prop_file(im), input_dir)
                               for im in gf])
            types.append([im.get('type', '2D') for im in gf])
            px2m.append([float(im.get('px2m') or 0.0) for im in gf])
            crop_area.append([float(im.get('crop_area') or 0.0) for im in gf])
            depth.append([float(im.get('D') or 0.0) for im in gf])
            if any(im.get('type') == '3D' for im in gf):
                has_depth = True

        measure_data = {'input_dir': input_dir, 'input_file': input_file,
                        'type': types, 'output_dir': self.app.output_dir(),
                        'group_names': group_names,
                        'nbins_density': [int(g.get('nbins_density', 16))
                                          for g in valid],
                        'nbins_exceedance': [int(g.get('nbins_exceedance', 22))
                                             for g in valid]}
        sample = {'px2m': px2m, 'crop_area': crop_area}
        if has_depth:
            sample['D'] = depth
        method = {'minsearch': self._method.get(),
                  'fractal_index': self._fractal.get()}

        if self._fractal.get():
            method['fractal_callback'] = self._make_fractal_callback()

        self.app.run_worker(
            lambda: run_bubble_properties(measure_data, sample, method),
            self._run_btn,
            lambda: messagebox.showinfo(
                'Done', 'Properties completed.\nResults in:\n'
                f'{measure_data["output_dir"]}'))

    def _make_fractal_callback(self):
        """Create a thread-safe callback that shows FractalIndexDialog.

        ``run_worker`` executes the pipeline in a background thread, but
        tkinter widgets must be created on the main thread.  This wrapper
        schedules the dialog on the main thread via ``after`` and blocks
        the worker thread with a ``threading.Event`` until the user closes
        the dialog.
        """
        import threading

        def callback(x, y, group_name):
            result_holder = {}
            done = threading.Event()

            def show_dialog():
                dlg = FractalIndexDialog(self, x, y, group_name)
                result_holder['result'] = dlg.result
                done.set()

            self.app.after(0, show_dialog)
            done.wait()
            return result_holder.get('result')

        return callback


# =============================================================================
# Main application
# =============================================================================
class StARApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title('StAR - Statistical Analysis of Rocks')
        self.geometry('900x780')
        self.minsize(820, 640)
        # Shared group model, defined in PreProcess and inherited everywhere.
        self.groups = []
        self._running = False
        self._build_ui()

    def report_callback_exception(self, exc, val, tb):
        """Show any Tk callback exception (also from dialogs) with traceback."""
        import traceback
        text = ''.join(traceback.format_exception(exc, val, tb))
        try:
            print(text)
        except Exception:
            pass
        messagebox.showerror('Error', f'{exc.__name__}: {val}\n\n{text}')

    def _build_ui(self):
        pad = dict(padx=8, pady=4)

        top = ttk.LabelFrame(self, text='General configuration')
        top.pack(fill='x', **pad)
        ttk.Label(top, text='Output folder:').pack(side='left', padx=6, pady=6)
        if getattr(sys, 'frozen', False):
            default_out = os.path.join(os.path.dirname(sys.executable),
                                       'output')
        else:
            default_out = os.path.join(ROOT_DIR, 'output')
        self._outdir = tk.StringVar(value=default_out)
        ttk.Entry(top, textvariable=self._outdir).pack(
            side='left', fill='x', expand=True, padx=6)
        ttk.Button(top, text='Browse...', command=self._browse_out).pack(
            side='left', padx=6)

        self._nb = ttk.Notebook(self)
        self._nb.pack(fill='both', expand=True, **pad)
        self.preprocess_tab = PreProcessTab(self._nb, self)
        self.analyze_tab = AnalyzeTab(self._nb, self)
        self.stereology_tab = StereologyTab(self._nb, self)
        self.properties_tab = PropertiesTab(self._nb, self)
        self._nb.add(self.preprocess_tab, text='PreProcess')
        self._nb.add(self.analyze_tab, text='Analyze')
        self._nb.add(self.stereology_tab, text='Stereology')
        self._nb.add(self.properties_tab, text='Properties')
        self._nb.bind('<<NotebookTabChanged>>', self._on_tab_changed)

        bottom = ttk.LabelFrame(self, text='Log')
        bottom.pack(fill='both', expand=True, **pad)
        self.log = tk.Text(bottom, height=8, state='disabled', wrap='word',
                           font=('Consolas', 9))
        sb = ttk.Scrollbar(bottom, orient='vertical', command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        self.log.pack(side='left', fill='both', expand=True)
        sb.pack(side='left', fill='y')

        self._progress = ttk.Progressbar(self, mode='indeterminate')
        self._progress.pack(fill='x', padx=8, pady=(0, 6))

    # ---- shared helpers -----------------------------------------------------
    def output_dir(self):
        return self._outdir.get()

    def _browse_out(self):
        d = filedialog.askdirectory(title='Output folder')
        if d:
            self._outdir.set(d)

    def clear_log(self):
        self.log.configure(state='normal')
        self.log.delete('1.0', tk.END)
        self.log.configure(state='disabled')

    def reload_all(self):
        """Rebuild every tab from the shared group model."""
        for tab in (self.preprocess_tab, self.analyze_tab,
                    self.stereology_tab, self.properties_tab):
            tab.reload()

    def _on_tab_changed(self, event):
        widget = self._nb.nametowidget(self._nb.select())
        if hasattr(widget, 'reload'):
            widget.reload()

    def run_worker(self, func, button, on_success):
        """Run ``func`` in a background thread, redirecting stdout to log."""
        import threading
        if self._running:
            return
        self._running = True
        button.configure(state='disabled')
        self.clear_log()
        self._progress.start(12)
        redirector = _LogRedirector(self.log)

        def worker():
            old_out, old_err = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = redirector
            try:
                func()
                self.after(0, on_success)
            except Exception as exc:
                import traceback
                tb = traceback.format_exc()
                print(tb)
                self.after(0, lambda e=exc, t=tb: messagebox.showerror(
                    'Error', f'{type(e).__name__}: {e}\n\n{t}'))
            finally:
                sys.stdout, sys.stderr = old_out, old_err
                self.after(0, self._worker_done, button)

        threading.Thread(target=worker, daemon=True).start()

    def _worker_done(self, button):
        self._running = False
        self._progress.stop()
        button.configure(state='normal')


def main():
    app = StARApp()
    app.mainloop()


if __name__ == '__main__':
    main()
