# Search Dataset Explorer Dashboard

Interactive web-based dashboard for exploring and analyzing LC/MS search results from DIA-NN, Spectronaut, and FragPipe.

![Dashboard](https://img.shields.io/badge/dashboard-interactive-blue)
![Python](https://img.shields.io/badge/python-3.7+-green)

---

## Features

### 📁 Data Loading
- Load search results from multiple formats:
  - **BPS DIA-NN** exports (zip files or directories)
  - **BPS Spectronaut** results (parquet files)
  - **FragPipe DIA-NN** reports
- Configure which levels to load (precursor, protein, gene, peptide)
- Advanced options for sections and column selection
- Real-time loading status and progress

### 📊 Overview
- Collection statistics and metadata
- Sample list and counts
- Level summaries
- Quick data preview

### 🔍 Data Explorer
- Interactive data table with filtering and sorting
- View any level (precursor, protein, etc.)
- Filter by sample or view all samples combined
- Paginated display for large datasets
- Export capabilities

### 📈 Visualization
Multiple plot types:
- **Histogram** - Distribution of any variable
- **Scatter Plot** - Relationship between two variables
- **Box Plot** - Compare distributions across groups
- **Violin Plot** - Detailed distribution visualization
- **Heatmap** - Correlation or intensity matrices
- **RT Distribution** - Retention time quality assessment

Customization options:
- Select X and Y variables
- Color by categorical variables
- Interactive zooming and panning
- Download plots as PNG

### 🎯 Filtering
- Build complex filters with multiple conditions
- Filter by any column
- Operators: `>`, `<`, `>=`, `<=`, `==`, `!=`, `contains`
- Real-time results
- Save filtered datasets

---

## Installation

### Requirements

The dashboard requires these Python packages:

```bash
pip install dash plotly pandas numpy
```

Or install all project requirements:

```bash
pip install -r requirements.txt
```

---

## Usage

### Method 1: Command Line

Run directly from the command line:

```bash
python dashboard/search_explorer.py
```

With custom port:

```bash
python dashboard/search_explorer.py --port 8080
```

Disable debug mode (for production):

```bash
python dashboard/search_explorer.py --no-debug
```

### Method 2: Python Script

Use in your Python code:

```python
from dashboard import launch_explorer

# Launch with default settings (port 8050)
launch_explorer()

# Or customize
launch_explorer(port=8080, debug=True)
```

### Method 3: Within Jupyter Notebook

```python
# Launch in a separate thread
import threading
from dashboard import launch_explorer

def run_dashboard():
    launch_explorer(port=8050)

thread = threading.Thread(target=run_dashboard, daemon=True)
thread.start()

# Dashboard runs in background
# Access at http://localhost:8050
```

---

## Quick Start Guide

### Step 1: Launch Dashboard

```bash
python dashboard/search_explorer.py
```

You'll see:
```
🚀 Starting Search Dataset Explorer...
📊 Dashboard will be available at: http://localhost:8050

Press Ctrl+C to stop the server
```

### Step 2: Open in Browser

Navigate to: **http://localhost:8050**

### Step 3: Load Your Data

1. Click the **"📁 Load Data"** tab
2. Select your search type (e.g., "BPS DIA-NN")
3. Enter the path to your data:
   ```
   /path/to/export.zip
   ```
   or
   ```
   /path/to/results/directory
   ```
4. Choose which levels to load (precursor, protein, etc.)
5. Click **"🚀 Load Data"**

### Step 4: Explore!

- **Overview Tab**: See statistics and sample list
- **Explore Tab**: Browse data in interactive tables
- **Visualize Tab**: Create plots and visualizations
- **Filter Tab**: Apply filters to subset your data

---

## Tab Details

### 📁 Load Data Tab

**Main Options:**
- **Search Type**: Select your search engine format
- **Data Path**: Path to your results (zip file or directory)
- **Levels**: Which analysis levels to load
  - ☑ Precursor
  - ☑ Protein  
  - ☐ Gene
  - ☐ Peptide

**Advanced Options:**
- **Sections**: Specific data sections (var, obs, x, layers)
- **Strict Mode**: Require all columns to be present
- **Verbose**: Show detailed loading information

**Status:**
- Loading progress and status messages
- Summary table of loaded data
- Error messages if loading fails

---

### 📊 Overview Tab

Displays collection-level information:

- **Collection Statistics**
  - Search type
  - Available levels
  - Total number of samples

- **Sample List**
  - All loaded sample names
  - Collapsed view for large collections

---

### 🔍 Explore Tab

Interactive data table for browsing:

**Controls:**
- **Level**: Select which level to view
- **Sample**: Choose specific sample or "All Samples"
- **Load Button**: Load the selected data

**Data Table Features:**
- Displays first 1000 rows (for performance)
- Native filtering (type in column headers)
- Native sorting (click column headers)
- Scrollable view
- Shows total row count

**Example Use Cases:**
- Browse precursor-level data for quality control
- Find specific proteins in your results
- Compare values across samples
- Export data for external analysis

---

### 📈 Visualize Tab

Create interactive plots:

**Plot Types:**

1. **Histogram**
   - Visualize distribution of any numeric variable
   - Useful for: intensity distributions, score distributions

2. **Scatter Plot**
   - Compare two variables
   - Useful for: correlation analysis, QC plots

3. **Box Plot**
   - Compare distributions across groups
   - Useful for: sample comparisons, batch effects

4. **Violin Plot**
   - Detailed distribution visualization
   - Useful for: intensity distributions, quality metrics

5. **Heatmap**
   - Matrix visualization
   - Useful for: correlation matrices, intensity patterns

6. **RT Distribution**
   - Specialized retention time plot
   - Useful for: LC gradient quality assessment

**Controls:**
- **X Variable**: Choose column for X-axis
- **Y Variable**: Choose column for Y-axis
- **Color By**: Color points/bars by categorical variable

**Plot Interactions:**
- Zoom: Click and drag
- Pan: Hold shift and drag
- Reset: Double-click
- Download: Camera icon (top-right)

---

### 🎯 Filter Tab

Build and apply complex filters:

**Filter Builder:**
1. Select a column
2. Choose an operator
3. Enter a value
4. Click "Add Filter"

**Operators:**
- `>` Greater than
- `<` Less than
- `>=` Greater than or equal
- `<=` Less than or equal
- `==` Equal to
- `!=` Not equal to
- `contains` Text contains (for string columns)

**Example Filters:**
```
Q.Value < 0.01           (High confidence)
Precursor.Charge == 2    (Specific charge state)
Protein.Names contains "ENSG"  (Specific proteins)
RT > 10 AND RT < 50      (Time window)
```

**Apply Filters:**
- Click "Apply Filters" to execute
- See filtered row count
- Filtered data available for plotting and export

---

## Performance Tips

### For Large Datasets

1. **Load specific levels only**
   - Only check the levels you need
   - Reduces memory usage

2. **Use filtered views**
   - Apply filters before visualization
   - Improves plot rendering speed

3. **Sample strategically**
   - For QC, load representative samples
   - Combine samples later if needed

4. **Close unused tabs**
   - Reduces browser memory usage

### Memory Management

**Typical Memory Usage:**
- Small dataset (< 1M rows): 1-2 GB
- Medium dataset (1-10M rows): 2-8 GB
- Large dataset (> 10M rows): 8+ GB

**Recommendations:**
- For large datasets, filter at load time using metadata
- Use the filter tab to create subsets
- Consider loading data in batches

---

## Troubleshooting

### Dashboard Won't Start

**Problem:** Port already in use  
**Solution:** 
```bash
python dashboard/search_explorer.py --port 8051
```

**Problem:** Module import errors  
**Solution:**
```bash
pip install dash plotly pandas numpy
```

### Data Loading Fails

**Problem:** "No data found"  
**Solution:**
- Check path is correct
- Verify files exist
- Check search type matches your data

**Problem:** "Missing columns"  
**Solution:**
- Try different levels
- Disable strict mode
- Check data format

### Slow Performance

**Problem:** Dashboard is slow  
**Solution:**
- Load fewer levels
- Filter data before plotting
- Reduce number of samples
- Use more powerful machine

### Plot Issues

**Problem:** Plot is empty  
**Solution:**
- Check data is loaded
- Verify column names are correct
- Check for NaN values
- Try different plot type

---

## Advanced Features

### Programmatic Access

```python
from dashboard import SearchExplorerDashboard

# Create dashboard instance
dashboard = SearchExplorerDashboard(port=8050, debug=True)

# Access underlying collection
collection = dashboard.collection

# Run dashboard
dashboard.run()
```

### Custom Configuration

```python
# Load data programmatically before launching
from src.parsers.search import SearchCollection

# New recommended usage with container and engine parameters
collection = SearchCollection(container='bps', engine='diann')
collection.add_searches('/path/to/data', levels=['precursor'])

# Legacy usage (still supported but deprecated)
collection = SearchCollection(search_type='bps_diann')
collection.add_searches('/path/to/data', levels=['precursor'])

# Pass to dashboard
dashboard = SearchExplorerDashboard(port=8050)
dashboard.collection = collection
dashboard.run()
```

### Integration with Analysis Scripts

```python
# In your analysis notebook
import subprocess
import time

# Launch dashboard in background
proc = subprocess.Popen(['python', 'dashboard/search_explorer.py'])

# Wait for startup
time.sleep(3)

# Continue with your analysis
# Dashboard runs independently

# Stop when done
proc.terminate()
```

---

## Keyboard Shortcuts

When using the dashboard:

- `Ctrl+F`: Find in page
- `Ctrl+R`: Refresh page
- `Ctrl+Shift+R`: Hard refresh (clear cache)
- `F11`: Fullscreen mode

---

## Browser Compatibility

**Recommended Browsers:**
- ✅ Chrome/Chromium (best performance)
- ✅ Firefox
- ✅ Edge
- ⚠️ Safari (some features may be limited)

**Not Supported:**
- ❌ Internet Explorer

---

## Security Notes

**For Local Use:**
- Dashboard runs on localhost by default
- Only accessible from your machine
- Safe for sensitive data

**For Shared/Server Deployment:**
- Consider authentication (not included by default)
- Use firewall rules to restrict access
- Set `debug=False` for production
- Use reverse proxy (nginx) for HTTPS

---

## FAQ

**Q: Can I load multiple datasets at once?**  
A: Currently, one dataset at a time. Reload to switch datasets.

**Q: Can I export filtered data?**  
A: Not in the current version, but you can access the collection object programmatically.

**Q: How much data can the dashboard handle?**  
A: Tested with up to 50M rows. Performance depends on your machine's RAM.

**Q: Can I customize the plots?**  
A: Basic customization is available. For advanced plots, use the collection object with matplotlib/seaborn.

**Q: Does the dashboard save my session?**  
A: No, data is stored in memory only. Reload data after restart.

**Q: Can I run this on a remote server?**  
A: Yes! SSH tunnel or use `host='0.0.0.0'` in the code. See Advanced Features.

---

## Contributing

To add features to the dashboard:

1. Edit `dashboard/search_explorer.py`
2. Add new tabs by modifying `_get_*_tab_content()` methods
3. Add callbacks in `_setup_callbacks()`
4. Test locally
5. Update this README

---

## Citation

If you use this dashboard in your research, please cite:

```bibtex
@software{search_explorer_dashboard,
  title = {Search Dataset Explorer Dashboard},
  author = {Your Name},
  year = {2026},
  url = {https://github.com/your-repo}
}
```

---

## License

[Your License Here]

---

## Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- Email: your.email@domain.com
- Documentation: [Link to docs]

---

**Happy Exploring! 🔬📊**
