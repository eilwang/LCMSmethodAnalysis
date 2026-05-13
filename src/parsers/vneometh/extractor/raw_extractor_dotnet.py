"""
raw_extractor.py
----------------
Extracts pressure and %B traces (and the programmed gradient method) from
Thermo .raw LC files using the bundled C# extractor + Mono.

Quick start
-----------
    from raw_extractor import extract_raw, extract_method

    df = extract_raw("/path/to/file.raw")
    # df columns: time_min, AnalyticalPumpPressureInBar, PercentBComposition, ...

    df_method = extract_method("/path/to/file.raw")
    # df_method columns: t_start_min, duration_min, flow_nLmin, pctB_end, curve_num

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
