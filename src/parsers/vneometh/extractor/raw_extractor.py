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
MONO_BIN  = "/opt/homebrew/bin/mono"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _find_netstandard(mono_bin):
    mono_root = os.path.dirname(os.path.dirname(mono_bin))
    matches   = glob.glob(os.path.join(mono_root, "**", "netstandard.dll"), recursive=True)
    preferred = [m for m in matches if "4.7.2-api" in m and "Facades" in m]
    found     = preferred[0] if preferred else (matches[0] if matches else None)
    if found is None:
        raise RuntimeError(
            f"Could not find netstandard.dll under {mono_root}.\n"
            "Install Mono via: brew install mono"
        )
    return found


def _ensure_exe(trfp_dir=TRFP_DIR, mono_bin=MONO_BIN):
    exe = os.path.join(trfp_dir, "extract_pressure2.exe")
    src = os.path.join(trfp_dir, "extract_pressure2.cs")
    if os.path.exists(exe) and os.path.getmtime(exe) >= os.path.getmtime(src):
        return exe
    print("Compiling extract_pressure2.cs ...")
    mcs         = os.path.join(os.path.dirname(mono_bin), "mcs")
    netstandard = _find_netstandard(mono_bin)
    r = subprocess.run([
        mcs, src,
        f"-r:{os.path.join(trfp_dir, 'ThermoFisher.CommonCore.Data.dll')}",
        f"-r:{os.path.join(trfp_dir, 'ThermoFisher.CommonCore.RawFileReader.dll')}",
        f"-r:{netstandard}",
        f"-out:{exe}",
    ], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Compilation failed:\n{r.stderr}")
    print(f"Compiled  (netstandard: {netstandard})")
    return exe


def _run(exe, raw_file, trfp_dir, mono_bin, filter_term):
    return subprocess.run(
        [mono_bin, exe, raw_file, filter_term],
        capture_output=True, text=True, cwd=trfp_dir, timeout=120,
    )


def _discover_columns(exe, raw_file, trfp_dir, mono_bin):
    r = _run(exe, raw_file, trfp_dir, mono_bin, "~no_match~")
    return [l.split(":", 1)[1].strip()
            for l in r.stderr.splitlines()
            if "col[" in l and ":" in l]


# ── Public API ────────────────────────────────────────────────────────────────

def extract_raw(raw_file, trfp_dir=TRFP_DIR, mono_bin=MONO_BIN, filter_term="b"):
    """
    Extract status-log columns matching *filter_term* from *raw_file*.

    Returns a DataFrame with a ``time_min`` column plus whatever pressure /
    %B columns matched (e.g. ``AnalyticalPumpPressureInBar``,
    ``PercentBComposition``).

    If *filter_term* matches nothing the function auto-detects a term that
    captures both a pressure column and a %B column.
    """
    exe    = _ensure_exe(trfp_dir, mono_bin)
    result = _run(exe, raw_file, trfp_dir, mono_bin, filter_term)

    if result.returncode != 0:
        raise RuntimeError(f"Extraction failed (exit {result.returncode}):\n{result.stderr}")

    if f"NO_MATCH for '{filter_term}'" in result.stderr:
        all_cols = _discover_columns(exe, raw_file, trfp_dir, mono_bin)
        auto_term = None
        for candidate in ["b", "a", "p", "percent", "pressure"]:
            hits = [c for c in all_cols if candidate.lower() in c.lower()]
            if any("pressure" in h.lower() for h in hits) and any("percent" in h.lower() for h in hits):
                auto_term = candidate
                break
        if auto_term and auto_term != filter_term:
            print(f"[extract_raw] '{filter_term}' matched nothing — retrying with '{auto_term}'")
            result = _run(exe, raw_file, trfp_dir, mono_bin, auto_term)
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


def extract_method(raw_file, trfp_dir=TRFP_DIR, mono_bin=MONO_BIN):
    """
    Extract the programmed gradient method from *raw_file*.

    Returns a DataFrame with columns:
        t_start_min, duration_min, flow_uLmin, flow_nLmin, pctB_end, curve_num

    Returns None if no method data is found.
    """
    exe = _ensure_exe(trfp_dir, mono_bin)
    r   = subprocess.run(
        [mono_bin, exe, raw_file, "~method~"],
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
