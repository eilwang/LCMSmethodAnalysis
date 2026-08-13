"""
raw_extractor.py
----------------
Extracts pressure and %B traces, datetime info, and the programmed gradient method from
Thermo .raw LC files using the bundled C# extractor + .NET.

Quick start
-----------
    from raw_extractor_dotnet import extract_raw, extract_method, extract_statuslog, extract_datetime, extract_run_events

    df = extract_raw("/path/to/file.raw")
    # df columns: time_min, AnalyticalPumpPressureInBar, PercentBComposition, ...

    df_method = extract_method("/path/to/file.raw")
    # df_method columns: t_start_min, duration_min, flow_nLmin, pctB_end, curve_num
    
    df_statuslog = extract_statuslog("/path/to/file.raw")
    # df_statuslog columns: timestamp, retention_time_min, SystemStatus, Flow.Nominal, %B.Value, etc.
    
    # Find specific event datetime
    pickup_time = extract_datetime("/path/to/file.raw", "Message", "Injecting from vial position")
    
    # Get all key run events
    events = extract_run_events("/path/to/file.raw")
    # events = {'start_file': '...', 'end_file': '...', 'sample_pickup': '...', etc.}

Configuration
-------------
Pass explicit paths if the defaults don't apply:

    df = extract_raw(raw_file, trfp_dir="/path/to/thermo_dlls", mono_bin="/usr/bin/mono")
"""

import csv
import glob
import io
import os
import subprocess

import pandas as pd

# ── Defaults ──────────────────────────────────────────────────────────────────
_HERE     = os.path.dirname(os.path.abspath(__file__))
TRFP_DIR  = os.path.join(_HERE, "thermo_dlls")
DOTNET_BIN = "/usr/bin/dotnet"
DOTNET_EXE = os.path.join(TRFP_DIR, "extract_pressure_dotnet", "bin", "Debug", "net6.0", "extract_pressure_dotnet.dll")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _find_netstandard(dotnet_bin):
    # For .NET Core, we don't need to find netstandard.dll separately
    return None


def _ensure_exe(trfp_dir=TRFP_DIR, dotnet_bin=DOTNET_BIN):
    exe = DOTNET_EXE
    src = os.path.join(trfp_dir, "extract_pressure_dotnet", "Program.cs")
    if os.path.exists(exe) and os.path.getmtime(exe) >= os.path.getmtime(src):
        return exe
    print("Building extract_pressure_dotnet with dotnet ...")
    project_dir = os.path.join(trfp_dir, "extract_pressure_dotnet")
    r = subprocess.run([
        dotnet_bin, "build", project_dir
    ], capture_output=True, text=True, cwd=project_dir)
    if r.returncode != 0:
        raise RuntimeError(f"Compilation failed:\n{r.stderr}")
    print(f"Built .NET Core extractor")
    return exe


def _run(exe, raw_file, trfp_dir, dotnet_bin, filter_term):
    return subprocess.run(
        [dotnet_bin, exe, raw_file, filter_term],
        capture_output=True, text=True, cwd=trfp_dir, timeout=120,
    )


def _discover_columns(exe, raw_file, trfp_dir, dotnet_bin):
    r = _run(exe, raw_file, trfp_dir, dotnet_bin, "~no_match~")
    return [l.split(":", 1)[1].strip()
            for l in r.stderr.splitlines()
            if "col[" in l and ":" in l]


# ── Public API ────────────────────────────────────────────────────────────────

def extract_raw(raw_file, trfp_dir=TRFP_DIR, dotnet_bin=DOTNET_BIN, filter_term="b"):
    """
    Extract status-log columns matching *filter_term* from *raw_file*.

    Returns a DataFrame with a ``time_min`` column plus whatever pressure /
    %B columns matched (e.g. ``AnalyticalPumpPressureInBar``,
    ``PercentBComposition``).

    If *filter_term* matches nothing the function auto-detects a term that
    captures both a pressure column and a %B column.
    """
    exe    = _ensure_exe(trfp_dir, dotnet_bin)
    result = _run(exe, raw_file, trfp_dir, dotnet_bin, filter_term)

    if result.returncode != 0:
        raise RuntimeError(f"Extraction failed (exit {result.returncode}):\n{result.stderr}")

    if f"NO_MATCH for '{filter_term}'" in result.stderr:
        all_cols = _discover_columns(exe, raw_file, trfp_dir, dotnet_bin)
        auto_term = None
        for candidate in ["b", "a", "p", "percent", "pressure"]:
            hits = [c for c in all_cols if candidate.lower() in c.lower()]
            if any("pressure" in h.lower() for h in hits) and any("percent" in h.lower() for h in hits):
                auto_term = candidate
                break
        if auto_term and auto_term != filter_term:
            print(f"[extract_raw] '{filter_term}' matched nothing — retrying with '{auto_term}'")
            result = _run(exe, raw_file, trfp_dir, dotnet_bin, auto_term)
        if auto_term is None or f"NO_MATCH for '{auto_term}'" in result.stderr:
            pressure_cols = [c for c in all_cols if "pressure" in c.lower()]
            pctb_cols     = [c for c in all_cols if "percent"  in c.lower()]
            raise RuntimeError(
                f"Could not find pressure + %B columns with filter '{filter_term}'.\n"
                f"Pressure candidates : {pressure_cols}\n"
                f"%B candidates       : {pctb_cols}\n"
                f"All columns         :\n  " + "\n  ".join(all_cols)
            )

    lines = result.stdout.strip().splitlines()
    if len(lines) < 2:
        raise RuntimeError(
            f"Extractor returned no data rows ({len(lines)} line(s)).\n"
            f"STDERR:\n{result.stderr}"
        )
    df = pd.DataFrame(list(csv.DictReader(lines))).apply(pd.to_numeric, errors="coerce")
    df.rename(columns={"time_minutes": "time_min"}, inplace=True)
    return df


def extract_statuslog(raw_file, trfp_dir=TRFP_DIR, dotnet_bin=DOTNET_BIN):
    """
    Extract detailed status log entries with timestamps from *raw_file*.

    Returns a DataFrame with columns:
        timestamp: datetime of the log entry (creation_date + retention_time)
        retention_time_min: retention time in minutes
        ... plus all status log columns (varies by instrument)

    Common status log columns include:
        - SystemStatus
        - Flow.Nominal
        - %B.Value
        - Curve
        - StartColumnWash, StartColumnEquilibration
        - Module-specific parameters

    Returns None if no status log data is found.
    """
    exe = _ensure_exe(trfp_dir, dotnet_bin)
    r = subprocess.run(
        [dotnet_bin, exe, raw_file, "~statuslog~"],
        capture_output=True, text=True, cwd=trfp_dir, timeout=120,
    )
    
    if r.returncode != 0:
        raise RuntimeError(f"Status log extraction failed (exit {r.returncode}):\n{r.stderr}")
    
    lines = r.stdout.strip().splitlines()
    if len(lines) < 2:
        return None
    
    # Parse CSV
    df = pd.read_csv(io.StringIO(r.stdout))
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    return df


def extract_datetime(raw_file, column_name, search_value, trfp_dir=TRFP_DIR, dotnet_bin=DOTNET_BIN):
    """
    Extract datetime from status log based on a column search.
    
    Finds the first row where *column_name* contains *search_value* and returns
    the timestamp from the 'Time' column.
    
    Parameters
    ----------
    raw_file : str
        Path to the .raw file
    column_name : str
        Column name to search in (e.g., 'Message', 'Text')
    search_value : str
        Value to search for in the column (substring match)
    trfp_dir : str, optional
        Path to thermo_dlls directory
    dotnet_bin : str, optional
        Path to dotnet executable
    
    Returns
    -------
    str or None
        Datetime string in format 'YYYY-MM-DD HH:MM:SS' or None if not found
    
    Examples
    --------
    >>> dt = extract_datetime(raw_file, 'Message', 'Injecting from vial position')
    >>> print(dt)
    '2026-04-27 20:31:15'
    """
    status_log = extract_statuslog(raw_file, trfp_dir, dotnet_bin)
    
    if status_log is None or column_name not in status_log.columns:
        return None
    
    # Search for matching rows
    mask = status_log[column_name].astype(str).str.contains(search_value, case=False, na=False)
    matching_rows = status_log[mask]
    
    if len(matching_rows) == 0:
        return None
    
    # Return the Time value from the first matching row
    if 'Time' in matching_rows.columns:
        time_value = matching_rows.iloc[0]['Time']
        if pd.notna(time_value):
            time_str = str(time_value)
            # Strip timezone offset (e.g., " -07:00" or " +05:30")
            import re
            time_str = re.sub(r'\s+[+-]\d{2}:\d{2}$', '', time_str)
            return time_str
        return None
    
    # Fallback to timestamp if Time column doesn't exist
    return matching_rows.iloc[0]['timestamp'].strftime('%Y-%m-%d %H:%M:%S')


def extract_run_events(raw_file, trfp_dir=TRFP_DIR, dotnet_bin=DOTNET_BIN):
    """
    Extract key datetime events from a raw file run.
    
    Returns a dictionary with datetime strings for important run events:
        - start_file: First non-zero retention time
        - end_file: Last non-zero retention time
        - sample_pickup: When sample injection started
        - pickup_end: When waiting for inject response
        - start_sample_load: When sample loading began
        - start_gradient: When gradient run started
        - end_gradient: When gradient run stopped
        - end_lc: When column equilibration completed
    
    Parameters
    ----------
    raw_file : str
        Path to the .raw file
    trfp_dir : str, optional
        Path to thermo_dlls directory
    dotnet_bin : str, optional
        Path to dotnet executable
    
    Returns
    -------
    dict
        Dictionary mapping event names to datetime strings (or None if not found)
    
    Examples
    --------
    >>> events = extract_run_events(raw_file)
    >>> print(events['start_gradient'])
    '2026-04-27 20:31:25'
    """
    status_log = extract_statuslog(raw_file, trfp_dir, dotnet_bin)
    
    if status_log is None:
        return {}
    
    events = {}
    
    # Start and end file: first and last non-NaN datetime values
    time_col = 'Time' if 'Time' in status_log.columns else 'timestamp'
    valid_times = status_log[pd.notna(status_log[time_col])]
    
    if len(valid_times) > 0:
        import re
        start_time = str(valid_times.iloc[0][time_col])
        end_time = str(valid_times.iloc[-1][time_col])
        # Strip timezone offset (e.g., " -07:00" or " +05:30")
        events['start_file'] = re.sub(r'\s+[+-]\d{2}:\d{2}$', '', start_time)
        events['end_file'] = re.sub(r'\s+[+-]\d{2}:\d{2}$', '', end_time)
    
    # Define search patterns for Message column
    message_searches = {
        'sample_pickup': 'Injecting from vial position',
        'pickup_end': 'Waiting for inject response on Sampler.',
        'start_sample_load': 'Log SystemStatus: Running - Sample Loading',
        'start_gradient': 'Entered stage "Start Run"',
        'end_gradient': 'Entered stage "Stop Run"',
        'end_lc': 'Column equilibration completed.'
    }
    
    # Search for each event in Message column
    if 'Message' in status_log.columns:
        for event_name, search_text in message_searches.items():
            mask = status_log['Message'].astype(str).str.contains(search_text, case=False, na=False)
            matching_rows = status_log[mask]
            
            if len(matching_rows) > 0:
                time_col = 'Time' if 'Time' in matching_rows.columns else 'timestamp'
                time_value = matching_rows.iloc[0][time_col]
                if pd.notna(time_value):
                    time_str = str(time_value)
                    # Strip timezone offset (e.g., " -07:00" or " +05:30")
                    import re
                    events[event_name] = re.sub(r'\s+[+-]\d{2}:\d{2}$', '', time_str)
                else:
                    events[event_name] = None
    
    return events


def extract_method(raw_file, trfp_dir=TRFP_DIR, dotnet_bin=DOTNET_BIN):
    """
    Extract the programmed gradient method from *raw_file*.

    Returns a DataFrame with columns:
        t_start_min, duration_min, flow_uLmin, flow_nLmin, pctB_end, curve_num

    Returns None if no method data is found.
    """
    exe = _ensure_exe(trfp_dir, dotnet_bin)
    r   = subprocess.run(
        [dotnet_bin, exe, raw_file, "~method~"],
        capture_output=True, text=True, cwd=trfp_dir, timeout=120,
    )
    if "NO_METHOD_DATA" in r.stderr or not r.stdout.strip():
        return None

    rows  = list(csv.DictReader(io.StringIO(r.stdout)))
    PROPS = {"Flow.Nominal", "%B.Value", "Curve"}
    steps = {}
    for row in rows:
        pn = (row.get("Property name") or "").strip()
        gd = (row.get("Gradient duration") or "").strip()
        gv = (row.get("Gradient end value") or "").strip()
        rt = (row.get("Retention time") or "").strip()
        if pn not in PROPS or not gv:
            continue
        try:
            dur = float(gd)
            val = float(gv)
            t   = float(rt) if rt else 0.0
        except ValueError:
            continue
        key = round(t, 8)
        if key not in steps:
            steps[key] = {"t_start_min": t}
        if pn == "Flow.Nominal":
            steps[key]["flow_uLmin"]   = val
            steps[key]["flow_nLmin"]   = val * 1000.0
            steps[key]["duration_min"] = dur
        elif pn == "%B.Value":
            steps[key]["pctB_end"]     = val
            steps[key]["duration_min"] = dur
        elif pn == "Curve":
            steps[key]["curve_num"]    = int(val)

    if not steps:
        return None

    col_order = ["t_start_min", "duration_min", "flow_uLmin", "flow_nLmin", "pctB_end", "curve_num"]
    df = pd.DataFrame(sorted(steps.values(), key=lambda x: x["t_start_min"]))
    return df[[c for c in col_order if c in df.columns]]
