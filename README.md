# StAR – Statistical Analysis of Rocks

A new user-friendly tool for routine rock characterisation. 
StAR enables users to 
i)  statistically characterise particle (e.g., bubbles, crystals, clasts) size distributions using a robust and well-established fitting procedure; 
ii) determine the fractal index of the distribution
ii) convert 2D data to 3D applying stereological methods; 
iii) visualise particle shape and orientation distributions.

The statistical analysis is based on:
> Proussevitch A.A., Sahagian D.L., Tsentalovich E.P. (2007)
> *Statistical analysis of bubble and crystal size distributions*,
> JVGR, 164(3), 95-111.
> https://doi.org/10.1016/j.jvolgeores.2007.04.006

The stereology is based on:
> van der Jagt, T., Jongbloed, G., & Vittorietti, M. (2023)
> *Existence and Approximation of Densities of Chord Length- and Cross Section Area Distributions*,
> Image Analysis and Stereology, 42(3), 171-184.
> https://doi.org/10.5566/ias.2923.
> van der Jagt, T., Jongbloed, G., & Vittorietti, M. (2024)
> *Stereological determination of particle size distributions for similar convex bodies*
> Electronic Journal of Statistics, 18(1), 742-774.
> DOI: 10.1214/24-EJS2215

## Modules

StAR includes four modules:

    PreProcess  →  Analyze  →  Stereology  →  Properties

Each module can be used **independently** or **in succession** within a single
workflow. StAR enables users to develop an analytical workflow either through a graphical user interface (GUI) or directly via Python scripts. 
When modules are run in succession through the GUI, the fields of the downstream
tabs are filled in automatically (they remain fully editable).

1. **PreProcess** – Spatial calibration of the input image file; cropping a region of the image; calculation of the intensity threshold for image binarisation.
   Define groups of image files here. Particle-size data from images belonging to the same group are pooled during the statistical analysis.
   This is useful for images from the same sample acquired at different magnifications.
   Results are saved in `<output>/preProcessingResults.csv` and the cropped images in `<output>/CropImages`. 
3. **Analyze** –  Threshold-based segmentation of the preprocessed images.
   This module generates `<output>/Measurements/measurementsTable_*.csv` and property
   histograms and orientation rose diagrams in `<output>/Measurements/Figures/`.
5. **Stereology** *(optional)* – Converts the two-dimensional distribution of equivalent diameters, obtained through the segmentation analysis,
   into a three-dimensional distribution, assuming spherical particles.
   Produces `measurementsStereoTable_*.csv` and comparison figures.
8. **Properties** – Statistically characterise particle size distributions.
   Saves best-fitting parameters in `<output>/Statistics/DensityBasedFitting_*.csv` and `<output>/Statistics/ExceedanceBasedFitting_*.csv`
   and calculated properties in `<output>/Statistics/Properties_*.csv`.    
   Optionally computes the fractal index and saves results in `<output>/Statistics/FractalIndex_*.csv`.
   Saves figures with the results of the fitting and the fractal analysis.

## Requirements

- Python ≥ 3.8
- numpy ≥ 1.21
- scipy ≥ 1.7
- matplotlib ≥ 3.5
- pandas ≥ 1.3
- scikit-image ≥ 0.19
- Pillow ≥ 9.0
- pyinstaller ≥ 5.0

```bash
pip install -r requirements.txt
```

The **Stereology** module additionally requires the `pysizeunfolder` package
(from GitHub):

```bash
pip install git+https://github.com/thomasvdj/pysizeunfolder
```
## Installation and usage

## CASE 1: WINDOWS

### Step 1 – Install Python

1. Go to https://www.python.org/downloads/
2. Download **Python 3.8** or higher
3. Run the installer
4. **IMPORTANT**: check the **"Add Python to PATH"** box
5. Click **Install Now**
6. Wait for completion and close

### Step 2 – Download and extract the project

1. Download `StAR.zip`
2. Right-click → **"Extract all..."**
3. Example: `C:\StAR`

### Step 3 – Install dependencies (first time only)

Open the **Command Prompt** (`cmd`):

```
cd C:\StAR
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The **Stereology** module additionally requires:

```
python -m pip install git+https://github.com/thomasvdj/pysizeunfolder
```

### Step 4 – Launch the GUI

```
cd C:\StAR
StAR.bat
```

Or:

```
cd C:\StAR
python star_gui.py
```

### Step 5 – Using the GUI

The window has an **output** folder at the top and 4 tabs, corresponding to the modules described above:

1. **PreProcess** 
2. **Analyze** 
3. **Stereology** 
4. **Properties** 

Modules can be run independently or in succession. After each module, the
downstream tabs are filled in automatically (but remain editable).

### Alternative: command line

```
cd C:\StAR\run
notepad preprocess.py   # edit parameters
python preprocess.py    # PreProcess (interactive windows)
python analyze.py
python stereology.py
python properties.py
```

### Optional: build a distributable .exe

Double-click `build_windows.bat` or from a terminal:

```
cd C:\StAR
build_windows.bat
```

The executable will be created in `dist\StAR\StAR.exe`.

---

## CASE 1: WINDOWS

### Step 1 – Install Python

1. Go to https://www.python.org/downloads/
2. Download **Python 3.11** or higher
3. Run the installer
4. **IMPORTANT**: check the **"Add Python to PATH"** box
5. Click **Install Now**
6. Wait for completion and close

### Step 2 – Download and extract the project

1. Download `StAR.zip`
2. Right-click → **"Extract all..."**
3. Example: `C:\StAR\python`

### Step 3 – Install dependencies (first time only)

Open the **Command Prompt** (`cmd`):

```
cd C:\StAR\python
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The **Stereology** module additionally requires:

```
python -m pip install git+https://github.com/thomasvdj/pysizeunfolder
```

### Step 4 – Launch the GUI

```
cd C:\StAR\python
StAR.bat
```

Or:

```
cd C:\StAR\python
python star_gui.py
```

### Step 5 – Using the GUI

The window has an **output** folder at the top and 4 tabs:

1. **PreProcess** – calibration, cropping and intensity range
2. **Analyze** – segmentation and 2D measurements
3. **Stereology** – stereological conversion (optional)
4. **Properties** – distribution fitting

Modules can be run independently or in succession. After each module, the
downstream tabs are filled in automatically (but remain editable).

### Alternative: command line

```
cd C:\StAR\python\run
notepad preprocess.py   # edit parameters
python preprocess.py    # PreProcess (interactive windows)
python analyze.py
python stereology.py
python properties.py
```

### Optional: build a distributable .exe

Double-click `build_windows.bat` or from a terminal:

```
cd C:\StAR\python
build_windows.bat
```

The executable will be created in `dist\StAR\StAR.exe`.

---
## CASE 2: LINUX / macOS

### Step 1 – Install Python and Tkinter

```bash
# Ubuntu / Debian
sudo apt update
sudo apt install python3 python3-pip python3-tk python3-venv

# Fedora / RHEL
sudo dnf install python3 python3-pip python3-tkinter

# Arch
sudo pacman -S python python-pip tk
```

### Step 2 – Download and extract the project

```bash
cd ~/Downloads
unzip StAR.zip
cd StAR
```

### Step 3 – Install dependencies

```bash
# Method A: globally (if the system allows it)
pip3 install --upgrade pip
pip3 install -r requirements.txt
```

If you get `externally-managed-environment`:

```bash
# Method B: virtual environment (**recommended**)
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

The **Stereology** module also requires:

```bash
pip install git+https://github.com/thomasvdj/pysizeunfolder
```

### Step 4 – Launch the GUI

```bash
cd /path/to/StAR
./StAR.sh
```

> If dependencies are not present, `StAR.sh` automatically creates a local
> virtual environment (`venv/`) and installs everything there. You need the
> `python3-venv` package (see Step 1). `tkinter` must be installed in the
> system Python (`python3-tk`).

Or manually:

```bash
python3 star_gui.py
```
### Step 5 – Using the GUI

The window has an **output** folder at the top and 4 tabs:

1. **PreProcess** – calibration, cropping and intensity range
2. **Analyze** – segmentation and 2D measurements
3. **Stereology** – stereological conversion (optional)
4. **Properties** – distribution fitting

Modules can be run independently or in succession. After each module, the
downstream tabs are filled in automatically (but remain editable).

### Alternative: command line

```bash
cd run
nano preprocess.py    # edit parameters
python3 preprocess.py # PreProcess (interactive windows)
python3 analyze.py
python3 stereology.py
python3 properties.py
```

### Optional: build an executable

```bash
chmod +x build_linux.sh
./build_linux.sh
```

The executable will be created in `dist/StAR/StAR`.

---
## Structure

```
python/
├── star_gui.py                     ← unified tabbed GUI (entry point)
├── run/
│   ├── preprocess.py               ← CLI PreProcess
│   ├── analyze.py                  ← CLI Analyze
│   ├── stereology.py               ← CLI Stereology
│   └── properties.py               ← CLI Properties
├── src/
│   ├── run_preprocessing.py        ← PreProcess pipeline
│   ├── run_analyze.py              ← Analyze pipeline
│   ├── run_stereology.py           ← Stereology pipeline
│   ├── run_bubble_properties.py    ← Properties pipeline
│   ├── preprocessing/
│   │   ├── preprocessing.py        ← logic (calibration/crop/intensity)
│   │   └── interactive_mpl.py      ← matplotlib interactors (CLI)
│   ├── analyze/
│   │   ├── analyze_bubble.py       ← segmentation + regionprops
│   │   └── property_figures.py     ← per-group histograms + rose diagrams
│   ├── stereology/
│   │   ├── stereology.py
│   │   ├── convert_measurement.py
│   │   └── size_estimation_unit_radius.py
│   └── bubble_properties/
│       ├── bubble_properties.py    ← analysis orchestrator
│       ├── check_input.py          ← input validation
│       ├── fractal_index.py        ← fractal index (Otsuki, 1998)
│       └── statistics/             ← distributions, fitting, solver
├── data/                           ← example data (Images, CropImages, Measurements)
├── requirements.txt
├── StAR.spec                       ← PyInstaller configuration
├── build_windows.bat               ← Windows build script
└── build_linux.sh                  ← Linux build script
└── cleanAll.sh                     ← Linux clean script
└── StAR.sh                         ← Linux launch script
└── StAR.bat                         ← Windows launch script
```

## Output

- **PNG** – labelled images,
            best-fitting distribution plots,
            property histograms, orientation rose diagrams
- **JPG** – cropped images 
- **CSV** – pre-processing tables,
            measurement tables,
            stereology tables,
            fitting parameter tables

## Input data format

- **JPG** – Starting Images 
- **CSV** files only for running modules independently (not in succession)
