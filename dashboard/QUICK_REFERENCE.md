# 🔬 Search Dataset Explorer - Quick Reference

**Version:** 1.0 | **Date:** 2026-07-02

---

## 🚀 Starting the Dashboard

### Option 1: Quick Launch
```bash
./launch_dashboard.py
```

### Option 2: Custom Port
```bash
./launch_dashboard.py --port 8080
```

### Option 3: From Python
```python
from dashboard import launch_explorer
launch_explorer(port=8050)
```

**Access:** Open browser to `http://localhost:8050`

---

## 📋 Main Features

| Tab | Icon | Purpose |
|-----|------|---------|
| Load Data | 📁 | Import search results |
| Overview | 📊 | Collection statistics |
| Explore | 🔍 | Browse data tables |
| Visualize | 📈 | Create plots |
| Filter | 🎯 | Subset data |

---

## 🔧 Loading Data

**3 Simple Steps:**

1. **Select Type:** BPS DIA-NN, BPS Spectronaut, or FragPipe
2. **Enter Path:** `/path/to/results.zip` or `/path/to/directory`
3. **Choose Levels:** ☑ Precursor, ☑ Protein, ☐ Gene, ☐ Peptide
4. **Click:** 🚀 Load Data

**Status:** Green ✅ = Success | Red ❌ = Error

---

## 📊 Plot Types

| Type | Best For | Variables Needed |
|------|----------|------------------|
| Histogram | Distributions | X only |
| Scatter | Correlations | X + Y |
| Box Plot | Group comparison | X (categorical) + Y |
| Violin Plot | Detailed distributions | X (categorical) + Y |
| Heatmap | Matrices | X + Y + Color |
| RT Distribution | LC quality | Sample only |

---

## 🎯 Filter Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `>` | Greater than | `Q.Value > 0.01` |
| `<` | Less than | `RT < 30` |
| `>=` | Greater or equal | `Charge >= 2` |
| `<=` | Less or equal | `Score <= 100` |
| `==` | Equal to | `Charge == 2` |
| `!=` | Not equal | `Type != 'decoy'` |
| `contains` | Text search | `Name contains 'ENSG'` |

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl + F` | Find in page |
| `Ctrl + R` | Refresh |
| `Ctrl + Shift + R` | Hard refresh |
| `F11` | Fullscreen |

---

## 🐛 Common Issues

### Dashboard won't start
**Error:** "Address already in use"  
**Fix:** `./launch_dashboard.py --port 8051`

### Missing dependencies
**Error:** "ModuleNotFoundError"  
**Fix:** `pip install dash plotly pandas numpy`

### Data won't load
**Error:** "No results found"  
**Fix:** Check path, verify search type, try verbose mode

### Slow performance
**Issue:** Dashboard is laggy  
**Fix:** Load fewer levels, filter data, close unused tabs

---

## 💡 Tips & Tricks

### Performance
- ✅ Load only needed levels
- ✅ Filter before plotting
- ✅ Use sample subsets for QC
- ❌ Don't load all levels at once (if not needed)

### Data Exploration
- Use native table filtering (type in column header)
- Sort by clicking column names
- Export plots with camera icon
- Color scatter plots by sample or condition

### Advanced Usage
- Access collection object programmatically
- Integrate with Jupyter notebooks
- Run on remote server with SSH tunnel
- Automate with Python scripts

---

## 📊 Data Table Features

**Built-in Capabilities:**
- ✓ Native column filtering
- ✓ Multi-column sorting
- ✓ Pagination (50 rows per page)
- ✓ Scrollable view
- ✓ Shows row counts

**How to Use:**
1. Type in column header to filter
2. Click column name to sort
3. Use pagination controls at bottom

---

## 🔗 Quick Links

- **Full Documentation:** `dashboard/README.md`
- **API Docs:** `docs/PARSERS_API.md`
- **Source Code:** `dashboard/search_explorer.py`
- **Troubleshooting:** See README.md

---

## 📞 Getting Help

**Check First:**
1. Is data path correct?
2. Is search type matching your data?
3. Are dependencies installed?
4. Is port available?

**Still Stuck?**
- Read full docs: `dashboard/README.md`
- Check error messages in terminal
- Try verbose mode for details
- Verify data format

---

## 🎓 Example Workflow

### Quality Control
```
1. Load Data → precursor level only
2. Overview → Check sample count
3. Visualize → Histogram of Q.Value
4. Filter → Q.Value < 0.01
5. Visualize → RT distribution plot
```

### Protein Analysis
```
1. Load Data → protein level
2. Explore → Browse protein table
3. Filter → Specific protein group
4. Visualize → Box plot across samples
5. Export → Download plot
```

### Method Comparison
```
1. Load Data → Multiple samples
2. Overview → Verify all loaded
3. Visualize → Scatter plot
4. Color By → Sample name
5. Compare → Identify differences
```

---

## 📦 System Requirements

**Minimum:**
- Python 3.7+
- 4 GB RAM
- Modern web browser

**Recommended:**
- Python 3.9+
- 8+ GB RAM (for large datasets)
- Chrome or Firefox browser
- SSD storage

---

## 🆘 Emergency Commands

```bash
# Kill dashboard if stuck
pkill -f search_explorer

# Check if port is in use
lsof -i :8050

# Force kill port
kill -9 $(lsof -t -i:8050)

# Reinstall dependencies
pip install --force-reinstall dash plotly
```

---

## ✨ New Features (Coming Soon)

- [ ] Multi-dataset comparison
- [ ] Custom plot templates
- [ ] Data export to CSV/Excel
- [ ] Batch processing
- [ ] Automated QC reports
- [ ] Integration with other tools

---

**Pro Tip:** Bookmark this page and `dashboard/README.md` for quick reference!

---

*Last Updated: 2026-07-02 | Version 1.0*
