# DIA-NN Project - Claude Context

## Project Overview
This project focuses on parsing and analyzing mass spectrometry data, specifically working with DIA-NN (Data-Independent Acquisition by Neural Networks) output and associated method files.

**Last Updated**: 2026-01-28

---

## Project Structure

```
diann/
├── SampleData/
│   ├── BPS/                    # BPS data files
│   ├── FP/                     # Feature data
│   │   └── h5ad/              # AnnData format files
│   ├── Sequences/              # Sequence data
│   └── methods/                # Method files
│       ├── LC/                 # Liquid Chromatography methods
│       └── MS/                 # Mass Spectrometry methods
│           └── DIA003.proteoscape.m/
│               ├── microTOFQImpacTemAcquisition.method  # MS instrument parameters
│               ├── DIAParameters.txt
│               ├── diaSettings.diasqlite
│               └── submethods.xml
│
└── code/
    ├── loader.py                      # Data loading utilities
    ├── lc_method_parser.py            # LC method file parser (OLE format)
    ├── lc_method_collection.py        # Collection/batch processing for LC methods
    ├── ms_method_parser.py            # MS method file parser (XML format) ✨ NEW
    ├── dia_settings_parser.py         # DIA settings parser (SQLite) ✨ NEW
    ├── synchro_settings_parser.py     # Synchro settings parser (SQLite) ✨ NEW
    ├── bruker_method.py               # Unified Bruker method parser ✨ NEW
    ├── bps.py                         # BPS-specific utilities
    ├── readzip.py                     # ZIP file utilities
    ├── diann_columns.yaml             # DIA-NN column definitions
    ├── anndiann.ipynb                 # Analysis notebook
    ├── Extract LC Gradient.ipynb      # LC gradient extraction notebook
    └── TODOS.md                       # Task tracking
```

---

## Key Components

### 1. Data Loaders (`loader.py`)
- Loads DIA-NN output files (TSV format)
- Handles various data types (reports, matrices, etc.)
- Integrates with pandas for data manipulation

### 2. LC Method Parser (`lc_method_parser.py`)
**Format**: OLE (Object Linking and Embedding) files from XCalibur/Thermo systems

**Key Features**:
- Parses `.meth` files using `olefile` library
- Extracts gradient tables (time, mobile phase composition)
- Parses instrument setup parameters
- Handles equilibration settings
- Returns structured data as pandas DataFrames

**Usage**:
```python
from lc_method_parser import LCMethod

method = LCMethod("path/to/method.meth")
print(f"Runtime: {method.runtime} min")
print(method.gradient)  # DataFrame with gradient table
print(method.params)    # Instrument setup parameters
print(method.equil)     # Equilibration settings
```

### 3. MS Method Parser (`ms_method_parser.py`) ✨ NEW
**Format**: XML files from Bruker TimsTOF systems

**Key Features**:
- Parses `microTOFQImpacTemAcquisition.method` files (XML format)
- Extracts file info and general metadata
- Handles typed parameters (int, double, string, vectors)
- Organizes polarity-dependent configurations (positive/negative)
- Supports multiple ion sources (ESI, APCI, nanoflow, etc.)
- Provides convenient accessors for calibration, collision cell, and TOF parameters

**Parameter Types**:
- `para_int`: Integer parameters
- `para_double`: Floating-point parameters
- `para_string`: String parameters
- `para_vec_double`: Vector of doubles (e.g., calibration masses)
- `para_vec_string`: Vector of strings (e.g., reference mass names)

**Structure**:
```
Root
├── fileinfo (metadata)
├── generalinfo (author, hostname, etc.)
└── instrument
    └── qtofimpactemacq
        ├── Global parameters (collision, digitizer, IMS, TOF, etc.)
        └── dependent (polarity/source-specific)
            ├── polarity="negative" [default, esi, apci, ...]
            └── polarity="positive" [default, esi, apci, ...]
```

**Usage**:
```python
from ms_method_parser import MSMethod

# Can pass either the .method file or the parent .m directory
method = MSMethod("path/to/DIA003.proteoscape.m/microTOFQImpacTemAcquisition.method")
# OR
method = MSMethod("path/to/DIA003.proteoscape.m")

print(method.summary())

# Get global parameter
collision_gas = method.get_param('Collision_GasSupply_Set')

# Get polarity-specific parameter
collision_bias = method.get_param('Collision_Bias_Set', polarity='negative')

# Get calibration info
cal_info = method.get_calibration_info('negative')

# Get collision cell parameters
collision_params = method.get_collision_cell_params('negative')

# Get TOF parameters
tof_params = method.get_tof_params('negative')

# Export all data
all_data = method.to_dict()
```

**Note**: MSMethod focuses on instrument parameters only. For DIA acquisition windows, use DIASettings or the unified BrukerMethod class.

### 4. DIA Settings Parser (`dia_settings_parser.py`) ✨ NEW
**Format**: SQLite database from Bruker TimsTOF systems

**Key Features**:
- Parses `diaSettings.diasqlite` database files
- Extracts DIA/diaPASEF acquisition window specifications
- Reads 2D window definitions (m/z × ion mobility)
- Provides global method parameters (1/K0 limits, schema version)
- Organizes windows by cycle ID
- Returns structured data as pandas DataFrames
- **Built-in visualization**: `plot_windows()` method with flexible styling
  - Color by cycle ID (default) or uniform color
  - Customizable transparency (`alpha` parameter, default 0.6)
  - Customizable edge color (`edge_color` parameter, default 'white')
  - Method name in legend (`method_name` parameter)
    - Useful for comparing multiple methods on same axis
    - With `color_by_cycle=True`: adds method name prefix to cycle labels
    - With `color_by_cycle=False`: creates legend entry for method
  - Supports external axes for multi-panel figures
  - Automatic legend (when coloring by cycle or method_name provided) and labels
  - Full control over visual appearance

**Window Specifications**:
- Window ID and type (MS1 vs MS2/DIA)
- Cycle ID for multi-cycle acquisitions
- Ion mobility range (1/K0 start/end)
- m/z isolation center and width
- Collision energy (eV)
- Calculated m/z ranges (start/end)

**Usage**:
```python
from dia_settings_parser import DIASettings

# Can pass either the .m directory or .diasqlite file
settings = DIASettings("path/to/DIA003.proteoscape.m")
# OR
settings = DIASettings("path/to/diaSettings.diasqlite")

print(settings.summary())

# Get DIA windows only
dia_windows = settings.get_dia_windows()

# Get windows for a specific cycle
cycle_1_windows = settings.get_windows_by_cycle(1)

# Get all unique cycle IDs
cycle_ids = settings.get_cycle_ids()

# Access raw data
all_windows = settings.windows  # DataFrame
global_params = settings.global_info  # Dict

# Plot DIA windows (colored by cycle ID - default)
settings.plot_windows()  # Creates new figure
plt.show()

# Uniform color instead of cycle colors
settings.plot_windows(color_by_cycle=False, uniform_color='steelblue')
plt.show()

# Customize transparency and edge color
settings.plot_windows(alpha=0.8, edge_color='black')
plt.show()

# Full customization
settings.plot_windows(color_by_cycle=False, uniform_color='coral',
                     alpha=0.5, edge_color='white', show_labels=True)
plt.show()

# Add method name to legend
settings.plot_windows(method_name='DIA003', color_by_cycle=True)
plt.show()

# Use with external axis for multi-panel plots
fig, ax = plt.subplots()
settings.plot_windows(ax=ax, show_labels=True, color_by_cycle=True)
plt.show()

# Export all data
all_data = settings.to_dict()
```

**Convenience function** (backward compatible):
```python
from dia_settings_parser import parse_dia_settings

data = parse_dia_settings("path/to/method.m")
# Returns dict with 'global_info', 'windows', 'polygon_points'
```

### 5. Synchro Settings Parser (`synchro_settings_parser.py`) ✨ NEW
**Format**: SQLite database from Bruker TimsTOF systems

**Key Features**:
- Parses `synchroSettings.syncsqlite` database files
- Handles empty databases gracefully (common when no synchronization is configured)
- Dynamically discovers tables and schema
- Provides flexible SQL query interface
- Returns structured data as pandas DataFrames

**Note**: In many cases, this database is empty (initialized but unused). This is normal when no instrument synchronization is configured. The parser handles both empty and populated databases.

**Usage**:
```python
from synchro_settings_parser import SynchroSettings

# Can pass either the .m directory or .syncsqlite file
settings = SynchroSettings("path/to/DIA003.proteoscape.m")
# OR
settings = SynchroSettings("path/to/synchroSettings.syncsqlite")

print(settings.summary())

# Check if database is empty
if settings.is_empty:
    print("No synchronization configured")
else:
    # Get list of tables
    tables = settings.get_table_names()

    # Get a specific table
    data = settings.get_table('TableName')

    # Execute custom SQL query
    results = settings.query("SELECT * FROM TableName WHERE ...")

    # Get schema information
    schema = settings.get_schema()
```

**Convenience function** (backward compatible):
```python
from synchro_settings_parser import parse_synchro_settings

data = parse_synchro_settings("path/to/method.m")
# Returns dict with 'tables', 'is_empty', 'data'
```

### 6. Unified Bruker Method Parser (`bruker_method.py`) ✨ NEW
**Recommended for most use cases** - combines MS parameters and DIA settings into one object.

**Key Features**:
- Unified interface to Bruker TimsTOF method files
- Composes MSMethod (instrument parameters) and DIASettings (acquisition windows)
- Optionally parses SynchroSettings
- Provides convenience methods that delegate to sub-parsers
- Direct access to sub-parsers when needed (`.ms`, `.dia`, `.synchro`)
- Clean separation of concerns with consistent API
- **Built-in visualization**: `plot_windows()` method delegates to DIASettings

**Design Philosophy**:
- **Option 1 (Implemented)**: Separate parsers with unified wrapper
  - ✓ Separation of concerns
  - ✓ Each parser is independently reusable
  - ✓ Easy to maintain and extend
  - ✓ Clear responsibility boundaries
- **Option 2 (Rejected)**: Monolithic single class
  - ✗ Violates single responsibility principle
  - ✗ Harder to test and maintain

**Usage**:
```python
from bruker_method import BrukerMethod

# Parse complete method (instrument + DIA settings)
method = BrukerMethod("/path/to/DIA003.proteoscape.m")

# Optional: also parse synchronization settings
method = BrukerMethod("/path/to/DIA003.proteoscape.m", parse_synchro=True)

# Print comprehensive summary
print(method.summary())

# ========================================================================
# Convenience methods (delegate to sub-parsers)
# ========================================================================

# MS parameters
collision_gas = method.get_param('Collision_GasSupply_Set')
cap_voltage = method.get_param('Source_CapillarySetValue', polarity='negative', source='esi')
calibration = method.get_calibration_info('negative')
collision_params = method.get_collision_cell_params('negative')
tof_params = method.get_tof_params('negative')

# DIA windows
dia_windows = method.get_dia_windows()  # Returns DataFrame
ms1_windows = method.get_ms1_windows()
cycle_ids = method.get_cycle_ids()
cycle_1_windows = method.get_windows_by_cycle(1)

# Plot DIA windows
method.plot_windows()  # Color by cycle (default)
method.plot_windows(color_by_cycle=False, uniform_color='tomato')  # Uniform color
plt.show()

# ========================================================================
# Direct access to sub-parsers (when you need more control)
# ========================================================================

method.ms     # MSMethod object - full access to instrument params
method.dia    # DIASettings object - full access to DIA windows
method.synchro  # SynchroSettings object (if parse_synchro=True)

# Example: Use sub-parser methods directly
print(method.ms.summary())          # MS-specific summary
print(method.dia.summary())         # DIA-specific summary
all_windows = method.dia.windows    # Direct DataFrame access

# Export everything
all_data = method.to_dict()
```

**When to use**:
- ✓ **BrukerMethod**: When you need both instrument parameters AND DIA settings (most common)
- ✓ **MSMethod directly**: When you only need instrument parameters
- ✓ **DIASettings directly**: When you only need acquisition windows
- ✓ **SynchroSettings directly**: When you only need synchronization settings

### 7. LC Method Collection (`lc_method_collection.py`)
- Batch processing for multiple LC method files
- Organizes methods by sample
- Enables comparison across methods

---

## Current Git Status

**Branch**: `main`

**Modified Files**:
- `.DS_Store`
- `SampleData/.DS_Store`
- `code/Extract LC Gradient.ipynb`
- `code/lc_method_collection.py`
- `code/lc_method_parser.py`
- `code/loader.py`

**New/Untracked Files**:
- `SampleData/BPS/`
- `SampleData/FP/h5ad/`
- `SampleData/Sequences/`
- `SampleData/methods/`
- `code/TODOS.md`
- `code/bps.py`
- `code/readzip.py`
- `code/ms_method_parser.py` ✨ NEW (created 2026-01-28)
- `code/dia_settings_parser.py` ✨ NEW (created 2026-01-28)
- `code/synchro_settings_parser.py` ✨ NEW (created 2026-01-28)
- `code/bruker_method.py` ✨ NEW (created 2026-01-28)
- `CLAUDE_CONTEXT.md` ✨ NEW (created 2026-01-28)

**Recent Commits**:
1. `d9520c3` - LCmethod collection initilize?
2. `3355e2c` - LC method parse working very well
3. `5a73560` - working method parser fr
4. `24988a6` - working LC method text parse
5. `1fa8ac3` - start LC method parser

---

## Technical Details

### MS Method File Format (microTOFQImpacTemAcquisition.method)

**Instrument**: Bruker TimsTOF Ultra (TIMS: Trapped Ion Mobility Spectrometry)

**Key Sections**:

1. **Fileinfo**:
   - Application: Bruker timsControl
   - Version: 6.1.0.3
   - Type: ImpacTEM Pro Method

2. **General Info**:
   - Organization: Bruker Daltonics GmbH & Co. KG
   - OS: Windows 10 Enterprise LTSC 2019
   - Instrument: timsTOF_Ultra
   - Author and timestamps

3. **Global Instrument Parameters**:
   - Collision cell settings (gas supply, entrance, quench times)
   - Digitizer settings (sample interval, noise suppression, full scale)
   - IMS (Ion Mobility) cycle parameters
   - PASEF (Parallel Accumulation-Serial Fragmentation) settings
   - TOF detector voltages and calibration dates
   - Vacuum and temperature settings

4. **Polarity-Dependent Configurations**:
   - **Polarities**: Negative, Positive
   - **Ion Sources**: Default, ESI, APCI, APPI, CaptiveSpray, NanoflowESI, ultraSpray, etc.
   - Each polarity/source combination has:
     - Calibration data (reference masses, measured masses, errors, intensities)
     - Focus lens voltages
     - Collision cell voltages
     - TOF parameters (flight tube, reflector, detector voltages)
     - Digitizer settings

5. **Calibration Data** (example for negative mode):
   - Reference masses: Tuning Mix ES-TOF calibrants
   - Mass range: ~600-2800 m/z
   - Calibration coefficients (Tof2Cal C0, C1, C2, C3)
   - Regression mode and quality metrics (Score, StdDev, PPM error)
   - Last calibration date: 2025-03-04

6. **DIA Settings Database** (from diaSettings.diasqlite):
   - SQLite database with detailed 2D acquisition windows
   - **Global Parameters**:
     - `OneOverK0LowerLimit` / `OneOverK0UpperLimit`: Ion mobility range (typically 0.64-1.37)
     - `SchemaType`: DIA
     - `SchemaVersionMajor` / `SchemaVersionMinor`: Database schema version
   - **Window Specifications** (17 windows typical):
     - `Type`: 0 = MS1, 1 = MS2/DIA
     - `CycleId`: Acquisition cycle number (0-8 typical)
     - `OneOverK0Start` / `OneOverK0End`: Ion mobility window (1/K0)
     - `IsolationMz`: Center m/z of isolation window
     - `IsolationWidth`: Width in m/z units
     - `CollisionEnergy`: Collision energy in eV
   - Example: 16 DIA windows + 1 MS1 window covering 319-1440 m/z and 0.7-1.3 1/K0
   - **Key difference from DIAParameters.txt**: Includes full 2D window specifications (m/z × ion mobility)
   - Parsed by DIASettings class

---

## Data Types

### DIA-NN Output Files
- TSV format with specific column definitions
- Contains peptide/protein identification and quantification
- Column definitions stored in `diann_columns.yaml`

### LC Methods (`.meth`)
- OLE format (Microsoft compound file)
- Contains gradient table and instrument settings
- Text stream accessible via `olefile`

### MS Methods (`.method`)
- XML format (ISO-8859-1 encoding)
- Comprehensive instrument parameter storage
- Hierarchical structure with typed parameters
- Large files (~192KB, 52k+ tokens when parsed)

### DIA Settings (`diaSettings.diasqlite`)
- SQLite 3.x database format
- Stores DIA/diaPASEF acquisition window specifications
- **Tables**:
  - `DiaGlobalMethodInfo`: Key-value pairs for global settings
  - `DiaWindowsSpecification`: Window definitions (17 rows typical)
  - `DiaParametersPolyonSpecification`: Polygon points (if used)
- Compact size (~24KB)
- Direct SQL access for efficient queries

### Synchro Settings (`synchroSettings.syncsqlite`)
- SQLite 3.x database format
- Stores instrument synchronization settings
- **Often empty**: Database is typically initialized but contains no tables when synchronization is not used
- When populated, may contain:
  - Timing synchronization parameters
  - Multi-instrument coordination settings
  - Trigger and delay configurations
- Very small size (~4KB when empty)
- Parser dynamically discovers schema and handles empty databases

---

## Dependencies

### Python Packages
- `pandas`: Data manipulation and analysis
- `olefile`: Reading OLE files for LC methods
- `xml.etree.ElementTree`: XML parsing for MS methods (standard library)
- `sqlite3`: SQLite database access for DIA settings (standard library)
- `pathlib`: Path handling (standard library)
- `re`: Regular expressions (standard library)
- `typing`: Type hints (standard library)

---

## Common Tasks

### Parse Complete Bruker Method (Recommended)
```python
from bruker_method import BrukerMethod

# Parse everything (MS + DIA + optionally Synchro)
method = BrukerMethod("/path/to/DIA003.proteoscape.m", parse_synchro=True)
print(method.summary())

# Access via convenience methods
collision_gas = method.get_param('Collision_GasSupply_Set')
dia_windows = method.get_dia_windows()

# Or access sub-parsers directly when needed
print(method.ms.summary())       # MS-specific
print(method.dia.summary())      # DIA-specific
all_windows = method.dia.windows # Direct DataFrame access
```

### Parse an LC Method
```python
from lc_method_parser import LCMethod

method = LCMethod("/path/to/method.meth")
print(f"Runtime: {method.runtime} min")
print(method.gradient)
```

### Parse an MS Method
```python
from ms_method_parser import MSMethod

method = MSMethod("/path/to/microTOFQImpacTemAcquisition.method")
print(method.summary())

# Access specific parameters
collision_energy = method.get_param('Collision_Energy_Set', polarity='negative')
```

### Parse DIA Settings
```python
from dia_settings_parser import DIASettings

settings = DIASettings("/path/to/DIA003.proteoscape.m")
print(settings.summary())

# Get DIA windows
dia_windows = settings.get_dia_windows()
print(f"Total DIA windows: {len(dia_windows)}")

# Get windows by cycle
cycle_1 = settings.get_windows_by_cycle(1)
```

### Parse Synchro Settings
```python
from synchro_settings_parser import SynchroSettings

settings = SynchroSettings("/path/to/DIA003.proteoscape.m")
print(settings.summary())

# Check if database has data
if not settings.is_empty:
    # List available tables
    tables = settings.get_table_names()

    # Query specific table
    data = settings.get_table('TableName')
```

### Visualize DIA Windows
```python
from dia_settings_parser import DIASettings
import matplotlib.pyplot as plt

settings = DIASettings("/path/to/DIA003.proteoscape.m")

# Simple standalone plot (windows colored by cycle - default)
settings.plot_windows()
plt.show()

# Uniform color option
settings.plot_windows(color_by_cycle=False, uniform_color='steelblue')
plt.show()

# Customize appearance
settings.plot_windows(alpha=0.8, edge_color='black')  # More opaque, black outlines
settings.plot_windows(alpha=0.3, edge_color='white')  # More transparent, white outlines
plt.show()

# Use with external axis for multi-panel figures
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
settings.plot_windows(ax=axes[0], show_labels=True, color_by_cycle=True, alpha=0.7)
settings.plot_windows(ax=axes[1], show_labels=True, color_by_cycle=False,
                     uniform_color='coral', alpha=0.5, edge_color='black')
plt.show()

# Compare multiple methods on same axis
fig, ax = plt.subplots(figsize=(14, 8))
method1 = DIASettings("/path/to/method1.m")
method2 = DIASettings("/path/to/method2.m")

method1.plot_windows(ax=ax, method_name='Method A', color_by_cycle=False,
                    uniform_color='steelblue', alpha=0.5, show_labels=False)
method2.plot_windows(ax=ax, method_name='Method B', color_by_cycle=False,
                    uniform_color='coral', alpha=0.5, show_labels=False)
plt.show()

# Or use BrukerMethod for convenience
from bruker_method import BrukerMethod
method = BrukerMethod("/path/to/DIA003.proteoscape.m")
method.plot_windows(method_name='DIA003')
plt.show()
```

### Batch Process Methods
```python
from lc_method_collection import LCMethodCollection

collection = LCMethodCollection("/path/to/methods/directory")
# Process multiple methods
```

---

## Next Steps / TODOs

See [code/TODOS.md](code/TODOS.md) for detailed task list.

**High-level goals**:
1. ✅ Complete LC method parser
2. ✅ Create MS method parser
3. Integrate method data with DIA-NN output
4. Build analysis pipelines
5. Create visualization tools
6. Document workflow

---

## Notes for Claude

### Working with Method Files
- LC methods use OLE format - requires `olefile` library
- MS methods use XML format - standard library XML parser sufficient
- DIA settings use SQLite format - standard library sqlite3 module sufficient
- Synchro settings use SQLite format - standard library sqlite3 module sufficient
- Method files can be large - use streaming or chunked reading for very large files
- All parsers follow similar design patterns for consistency (class-based with helper methods)
- **Unified parser available**: Use `BrukerMethod` for most use cases - it combines MS + DIA + Synchro
  - Provides convenience methods that delegate to sub-parsers
  - Direct access to sub-parsers (`.ms`, `.dia`, `.synchro`) when needed
  - Clean separation of concerns with composition pattern
- **DIA acquisition windows**:
  - Source: `diaSettings.diasqlite` database (17 windows typical: 1 MS1 + 16 DIA)
  - Contains 2D window specifications (m/z × ion mobility)
  - Parsed by DIASettings or accessed via BrukerMethod
- **Synchro settings**:
  - Often empty (no synchronization configured)
  - Parser handles both empty and populated databases dynamically
  - Use for multi-instrument or timed acquisition coordination

### Code Style
- Type hints used throughout
- Docstrings in NumPy/Google style
- Return pandas DataFrames where tabular data is appropriate
- Use pathlib for path handling
- Parse once, query many times (store parsed data)

### Testing
- Use sample data in `SampleData/methods/` for testing
- Verify parser output against known method parameters
- Test edge cases (missing parameters, different polarities, etc.)

### Git Workflow
- Currently on `main` branch
- No remote tracking configured yet
- Use descriptive commit messages
- Consider creating feature branches for major changes

---

## Contact / References

- **DIA-NN**: https://github.com/vdemichev/DiaNN
- **LC Method Parser**: Adapted from https://github.com/nickdelgrosso/XCaliburMethodReader
- **Bruker TimsTOF**: Bruker Daltonics documentation

---

## Glossary

- **DIA**: Data-Independent Acquisition
- **PASEF**: Parallel Accumulation-Serial Fragmentation
- **TOF**: Time of Flight (mass analyzer)
- **TIMS**: Trapped Ion Mobility Spectrometry
- **LC**: Liquid Chromatography
- **MS**: Mass Spectrometry
- **ESI**: Electrospray Ionization
- **APCI**: Atmospheric Pressure Chemical Ionization
- **m/z**: mass-to-charge ratio
- **PPM**: Parts Per Million (mass accuracy unit)
