"""Extended Streamlit dashboard for NPEC Ecotrons.

This file is based on the original NPEC Ecotron visualization dashboard and
adds a new insights task for climate prediction.  The new task builds
sinusoidal regression models for humidity and temperature in each room using
historical sensor data.  Users can select a room and a date to obtain
predicted climate conditions, and visualise the modelled annual cycle.  The
idea of modelling seasonal climate variations with sine and cosine functions
is well established in climatology: sinusoidal terms capture the annual
cycle in temperature and humidity【316970089103360†L979-L984】.

The remainder of the dashboard remains unchanged: users can upload data,
downsample it, view time series plots, homogenise moisture levels and detect
sensor issues.  The climate prediction feature automatically identifies
columns containing the words "humidity" and "temperature" to build the
models, so it works with a variety of sensor naming conventions.
"""



import os
import re
import zipfile
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

###############################################################################
# PAGE CONFIG
###############################################################################
st.set_page_config(
    page_title="Visualization Dashboard | NPEC Ecotrons",
    layout="wide",
)

###############################################################################
# UTILITIES / CONSTANTS
###############################################################################
def normalize_name(name: str) -> str:
    """
    Normalize device or camera names so they match keys in the META mapping.

    Normalization rules include trimming whitespace, replacing hyphens and
    underscores with spaces, converting to lowercase and applying a few
    known alias corrections.
    """
    s = name.strip().lower().replace("-", " ").replace("_", " ")
    fixes = {
        "firebug": "fire bug",
        "stag beetle": "stag beetle",
        "stag  beetle": "stag beetle",
        "stag-beetle": "stag beetle",
        "yellowjacket": "yellowjacket",
        "yellow jacket": "yellowjacket",
        "dung beetle": "dung beetle",
        "dung-beetle": "dung beetle",
        "millipedes": "millipede",
        "scorpio": "scorpion",
        "potato beetle": "potato beetle",
        "potato-beetle": "potato beetle",
    }
    return fixes.get(s, s)


def ip_from(url: str) -> str:
    """Extract just the hostname or IP from a full URL. If parsing fails, return the original string."""
    try:
        return url.split("//", 1)[1].split("/", 1)[0]
    except Exception:
        return url


# Sidebar password: NEVER hardcode a real password.
# If empty/missing -> sidebar is unlocked by default.
SIDEBAR_PASS = str(st.secrets.get("SIDEBAR_PASS", os.environ.get("SIDEBAR_PASS", ""))).strip()

###############################################################################
# DEVICE DIRECTORY (SIDEBAR DATA)
###############################################################################
DEVICES: List[Tuple[str, str]] = [
    ("Ulysses", "http://192.168.162.8/visu/#/main"),
    ("Admiral", "http://192.168.162.9/visu/#/main"),
    ("Scarab", "http://192.168.162.10/visu/#/main"),
    ("Ladybug", "http://192.168.162.11/visu/#/main"),
    ("Stag beetle", "http://192.168.162.12/visu/#/main"),
    ("Mosquito", "http://192.168.162.13/visu/#/main"),
    ("Flea", "http://192.168.162.14/visu/#/main"),
    ("Yellowjacket", "http://192.168.162.15/visu/#/main"),
    ("Dragonfly", "http://192.168.162.16/visu/#/main"),
    ("Moth", "http://192.168.162.17/visu/#/main"),
    ("Cockroach", "http://192.168.162.18/visu/#/main"),
    ("Fly", "http://192.168.162.19/visu/#/main"),
    ("Mantis", "http://192.168.162.20/visu/#/main"),
    ("Tick", "http://192.168.162.21/visu/#/main"),
    ("Termite", "http://192.168.162.22/visu/#/main"),
    ("Giraffe", "http://192.168.162.23/visu/#/main"),
    ("Millipede", "http://192.168.162.24/visu/#/main"),
    ("Fire bug", "http://192.168.162.25/visu/#/main"),
    ("Centipede", "http://192.168.162.26/visu/#/main"),
    ("Tarantula", "http://192.168.162.27/visu/#/main"),
    ("Dung beetle", "http://192.168.162.28/visu/#/main"),
    ("Ant", "http://192.168.162.29/visu/#/main"),
    ("Hornet", "http://192.168.162.30/visu/#/main"),
    ("Maybug", "http://192.168.162.31/visu/#/main"),
    ("Bumblebee", "http://192.168.162.32/visu/#/main"),
    ("Honeybee", "http://192.168.162.33/visu/#/main"),
    ("Stink", "http://192.168.162.34/visu/#/main"),
    ("Hercules", "http://192.168.162.35/visu/#/main"),
    ("Strider", "http://192.168.162.36/visu/#/main"),
    ("Stick", "http://192.168.162.37/visu/#/main"),
    ("Longhorn", "http://192.168.162.38/visu/#/main"),
    ("Weaver", "http://192.168.162.39/visu/#/main"),
    ("Scorpion", "http://192.168.162.40/visu/#/main"),
    ("Caterpillar", "http://192.168.162.41/visu/#/main"),
    ("Potato beetle", "http://192.168.162.42/visu/#/main"),
    ("Cricket", "http://192.168.162.43/visu/#/main"),
]

EMOJI: Dict[str, str] = {
    "ulysses": "🦋", "admiral": "🦋", "scarab": "🪲", "ladybug": "🐞",
    "stag beetle": "🪲", "mosquito": "🦟", "flea": "🪳", "yellowjacket": "🐝",
    "dragonfly": "🐉", "moth": "🦋", "cockroach": "🪳", "fly": "🪰",
    "mantis": "🦗", "tick": "🕷️", "termite": "🐜", "giraffe": "🦒",
    "millipede": "🪱", "fire bug": "🔥", "centipede": "🪱", "tarantula": "🕷️",
    "dung beetle": "🪲", "ant": "🐜", "hornet": "🐝", "maybug": "🪲",
    "bumblebee": "🐝", "honeybee": "🐝", "stink": "💨", "hercules": "💪",
    "strider": "🚶", "stick": "🪵", "longhorn": "🐂", "weaver": "🧵",
    "scorpion": "🦂", "caterpillar": "🐛", "potato beetle": "🥔🪲",
    "cricket": "🦗",
}

META: Dict[str, Tuple[str, str]] = {
    "ulysses": ("Ecolab 1", "Advanced"), "admiral": ("Ecolab 1", "Advanced"),
    "scarab": ("Ecolab 1", "Advanced"), "ladybug": ("Ecolab 1", "Advanced"),
    "yellowjacket": ("Ecolab 1", "Advanced"), "flea": ("Ecolab 1", "Advanced"),
    "mosquito": ("Ecolab 1", "Advanced"), "stag beetle": ("Ecolab 1", "Advanced"),
    "dragonfly": ("Ecolab 2", "Basic"), "moth": ("Ecolab 2", "Basic"),
    "cockroach": ("Ecolab 2", "Basic"), "fly": ("Ecolab 2", "Basic"),
    "mantis": ("Ecolab 2", "Basic"), "tick": ("Ecolab 2", "Basic"),
    "termite": ("Ecolab 2", "Basic"), "giraffe": ("Ecolab 2", "Basic"),
    "millipede": ("Ecolab 2", "Basic"), "fire bug": ("Ecolab 2", "Basic"),
    "centipede": ("Ecolab 2", "Basic"), "tarantula": ("Ecolab 2", "Basic"),
    "dung beetle": ("Ecolab 3", "Basic"), "ant": ("Ecolab 3", "Basic"),
    "hornet": ("Ecolab 3", "Basic"), "maybug": ("Ecolab 3", "Basic"),
    "bumblebee": ("Ecolab 3", "Basic"), "honeybee": ("Ecolab 3", "Basic"),
    "stink": ("Ecolab 3", "Basic"), "hercules": ("Ecolab 3", "Basic"),
    "strider": ("Ecolab 3", "Basic"), "stick": ("Ecolab 3", "Basic"),
    "longhorn": ("Ecolab 3", "Basic"), "weaver": ("Ecolab 3", "Basic"),
    "scorpion": ("Ecolab 3", "Basic"), "caterpillar": ("Ecolab 3", "Basic"),
    "potato beetle": ("Ecolab 3", "Basic"), "cricket": ("Ecolab 3", "Basic"),
}


def meta_for(name: str) -> Tuple[str, str]:
    """Return the (room, type) for a device name using the META mapping."""
    return META.get(normalize_name(name), ("Ecolab 3", "Basic"))


RHIZOCAMS = [
    {
        "host": "Cricket",
        "gantry": "http://192.168.162.186:8501/",
        "analysis": "http://192.168.162.186:8502/",
    }
]

IP_CAMERAS = [
    ("Admiral", "192.168.162.45"), ("Ant", "192.168.162.65"),
    ("Bumblebee", "192.168.162.68"), ("Caterpillar", "192.168.162.77"),
    ("Centipede", "192.168.162.62"), ("Cockroach", "192.168.162.54"),
    ("Cricket", "192.168.162.79"), ("Dragonfly", "192.168.162.52"),
    ("Dung beetle", "192.168.162.64"), ("Fire bug", "192.168.162.61"),
    ("Flea", "192.168.162.50"), ("Fly", "192.168.162.55"),
    ("Giraffe", "192.168.162.161"), ("Hercules", "192.168.162.71"),
    ("Honeybee", "192.168.162.69"), ("Hornet", "192.168.162.66"),
    ("Ladybug", "192.168.162.47"), ("Longhorn", "192.168.162.74"),
    ("Mantis", "192.168.162.56"), ("Maybug", "192.168.162.67"),
    ("Millipede", "192.168.162.60"), ("Mosquito", "192.168.162.49"),
    ("Moth", "192.168.162.53"), ("Potato beetle", "192.168.162.78"),
    ("Scarab", "192.168.162.46"), ("Scorpion", "192.168.162.76"),
    ("Stag beetle", "192.168.162.48"), ("Stick", "192.168.162.130"),
    ("Stink", "192.168.162.70"), ("Strider", "192.168.162.72"),
    ("Tarantula", "192.168.162.63"), ("Termite", "192.168.162.58"),
    ("Tick", "192.168.162.57"), ("Ulysses", "192.168.162.44"),
    ("Weaver", "192.168.162.75"), ("Yellowjacket", "192.168.162.140"),
]

###############################################################################
# SIDEBAR WITH OPTIONAL PASSWORD LOCK (LOCKS ONLY SIDEBAR CONTENT)
###############################################################################
if "sidebar_unlocked" not in st.session_state:
    st.session_state.sidebar_unlocked = (SIDEBAR_PASS == "")

with st.sidebar:
    st.title("Devices")

    # If no password configured, ensure unlocked and show note
    if SIDEBAR_PASS == "":
        st.session_state.sidebar_unlocked = True
        st.caption("Sidebar lock disabled (no SIDEBAR_PASS set).")

    # Lock/unlock controls
    cols = st.columns([1, 1, 1.2])
    with cols[2]:
        if SIDEBAR_PASS:
            if st.session_state.sidebar_unlocked:
                if st.button("Lock menu", use_container_width=True):
                    st.session_state.sidebar_unlocked = False
                    st.rerun()
            else:
                with st.popover("Unlock"):
                    pw = st.text_input("Password", type="password", placeholder="••••••")
                    if st.button("Unlock"):
                        if pw == SIDEBAR_PASS:
                            st.session_state.sidebar_unlocked = True
                            st.rerun()
                        else:
                            st.error("Wrong password")

    # If locked: show message ONLY; do NOT stop the app (main content stays visible)
    if SIDEBAR_PASS and not st.session_state.sidebar_unlocked:
        st.info("Menu locked. Click **Unlock** to access device/camera controls.")
    else:
        # Filter inputs for device and camera lists
        q = st.text_input("Filter by name or IP", value="")
        room_filter = st.selectbox("Room", ["All", "Ecolab 1", "Ecolab 2", "Ecolab 3"], index=0)
        rooms_order = ["Ecolab 1", "Ecolab 2", "Ecolab 3"] if room_filter == "All" else [room_filter]

        # List devices grouped by room
        for room_name in rooms_order:
            with st.expander(room_name, expanded=False):
                for name, url in DEVICES:
                    room, typ = meta_for(name)
                    if room != room_name:
                        continue
                    if q and (q.lower() not in name.lower() and q.lower() not in ip_from(url)):
                        continue
                    key = normalize_name(name)
                    emoji = EMOJI.get(key, "🔗")
                    st.markdown(
                        f"**{emoji} {name}**  \n"
                        f"`{ip_from(url)}` • *{typ}*  \n"
                        f"[Open ↗]({url})",
                        help=f"{room} • {typ}",
                    )

        # RhizoCams grouped by room
        st.markdown("---")
        st.subheader("RhizoCam units")
        for room_name in rooms_order:
            items = [rc for rc in RHIZOCAMS if meta_for(rc["host"])[0] == room_name]
            if not items:
                continue
            with st.expander(room_name, expanded=False):
                for rc in items:
                    host = rc["host"]
                    g_ip, a_ip = ip_from(rc["gantry"]), ip_from(rc["analysis"])
                    if q and all(q.lower() not in s.lower() for s in (host, g_ip, a_ip)):
                        continue
                    st.markdown(
                        f"**📷 RhizoCam @ {host}**  \n"
                        f"`Gantry:` `{g_ip}`  \n"
                        f"`Analysis:` `{a_ip}`  \n"
                        f"[Gantry ↗]({rc['gantry']}) &nbsp;|&nbsp; [Analysis ↗]({rc['analysis']})"
                    )

        # IP cameras grouped by room
        st.markdown("---")
        st.subheader("IP cameras")
        cams_by_room = {"Ecolab 1": [], "Ecolab 2": [], "Ecolab 3": []}
        for cam_name, ip in IP_CAMERAS:
            room, _ = meta_for(cam_name)
            cams_by_room[room].append((cam_name, ip))

        for room_name in rooms_order:
            with st.expander(room_name, expanded=False):
                for cam_name, ip in cams_by_room.get(room_name, []):
                    if q and (q.lower() not in cam_name.lower() and q.lower() not in ip.lower()):
                        continue
                    key = normalize_name(cam_name)
                    emoji = EMOJI.get(key, "🎥")
                    url = f"http://{ip}"
                    st.markdown(
                        f"**{emoji} {cam_name}**  \n"
                        f"`{ip}`  \n"
                        f"[Open ↗]({url})"
                    )

        st.caption("Tip: collapse the sidebar with the chevron (>) to give charts more room.")

###############################################################################
# HEADER WITH LOGOS AND TITLE
###############################################################################
st.markdown(
    """
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;">
        <img src="https://raw.githubusercontent.com/vince-npec/ugt/main/Module-1-icon.png"
             alt="Ecotron Module" style="height:189px;width:auto;" />
        <h1 style="text-align:center;color:white;flex-grow:1;margin:0;font-size:2.6rem;font-weight:400;">
            Visualization Dashboard | <b style="font-weight:700;">NPEC Ecotrons</b>
        </h1>
        <img src="https://raw.githubusercontent.com/vince-npec/ugt/main/NPEC-dashboard-logo.png"
             alt="NPEC" style="height:189px;width:auto;" />
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("---")

###############################################################################
# DATA LOADING AND PREPARATION
###############################################################################
room_assignments = {
    "Ulysses": "Room 1", "Admiral": "Room 1", "Scarab": "Room 1",
    "Ladybug": "Room 1", "Yellowjacket": "Room 1", "Flea": "Room 1",
    "Mosquito": "Room 1", "Stag beetle": "Room 1", "Stag_Bettle": "Room 1",
    "Cockroach": "Room 2", "Termite": "Room 2", "Centipede": "Room 2",
    "Fly": "Room 2", "Giraffe": "Room 2", "Tarantula": "Room 2",
    "Fire bug": "Room 2", "Fire_Bug": "Room 2", "Tick": "Room 2",
    "Moth": "Room 2", "Millipede": "Room 2", "Mantis": "Room 2",
    "Dragonfly": "Room 2",
}

MAX_ROWS = 200_000


def _normalize_device_from_filename(prefix: str) -> str:
    if prefix == "Fire":
        return "Fire bug"
    if prefix == "Stag":
        return "Stag beetle"
    return prefix


def load_data(uploaded_files, max_rows: int = MAX_ROWS) -> pd.DataFrame:
    data_frames, total_rows = [], 0
    for uploaded_file in uploaded_files:
        try:
            df = pd.read_csv(uploaded_file, delimiter=";")
            device_prefix = uploaded_file.name.split("_")[0]
            device_name = _normalize_device_from_filename(device_prefix)
            df["device"] = device_name
            df["room"] = room_assignments.get(device_name, "Unknown")

            if not df.empty:
                if max_rows and total_rows + len(df) > max_rows:
                    df = df.iloc[: max_rows - total_rows]
                data_frames.append(df)
                total_rows += len(df)
                if max_rows and total_rows >= max_rows:
                    st.warning(f"Loaded {max_rows} rows (limit reached for performance).")
                    break
        except Exception as e:
            st.error(f"Error reading {uploaded_file.name}: {e}")

    if not data_frames:
        st.error("No data frames were created from the uploaded files.")
        return pd.DataFrame()
    return pd.concat(data_frames, ignore_index=True)


def load_data_from_zip(zip_file, max_rows: int = MAX_ROWS) -> pd.DataFrame:
    data_frames, total_rows = [], 0
    with zipfile.ZipFile(zip_file) as z:
        for filename in z.namelist():
            if not (filename.endswith(".csv") and not filename.startswith("__MACOSX/")):
                continue
            with z.open(filename) as f:
                try:
                    df = pd.read_csv(f, delimiter=";")
                    base = filename.split("/")[-1]
                    device_prefix = base.split("_")[0]
                    device_name = _normalize_device_from_filename(device_prefix)
                    df["device"] = device_name
                    df["room"] = room_assignments.get(device_name, "Unknown")

                    if not df.empty:
                        if max_rows and total_rows + len(df) > max_rows:
                            df = df.iloc[: max_rows - total_rows]
                        data_frames.append(df)
                        total_rows += len(df)
                        if max_rows and total_rows >= max_rows:
                            st.warning(f"Loaded {max_rows} rows (limit reached for performance).")
                            break
                except Exception as e:
                    st.error(f"Error reading {filename}: {e}")

    if not data_frames:
        st.error("No data frames were created from the ZIP file.")
        return pd.DataFrame()
    return pd.concat(data_frames, ignore_index=True)


def resample_data(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    if freq == "10T":
        return df
    if "timestamp" not in df.columns:
        return df

    numeric_cols = df.select_dtypes(include="number").columns
    if len(numeric_cols) == 0:
        return df

    frames = []
    for (device, room), group in df.groupby(["device", "room"], dropna=False):
        group = group.set_index("timestamp").sort_index()
        resampled = group[numeric_cols].resample(freq).mean()
        resampled["device"] = device
        resampled["room"] = room
        frames.append(resampled.reset_index())
    return pd.concat(frames, ignore_index=True) if frames else df


def looks_like_data_point(col) -> bool:
    """Heuristically determine if a column name represents numeric data."""
    try:
        float(str(col))
        return True
    except Exception:
        pass
    if re.match(r"^\d{2}\.\d{2}\.\d{4}", str(col)):
        return True
    if len(str(col)) < 3:
        return True
    return False


def derive_tension_targets(
    data: pd.DataFrame,
    moisture_cols: List[str],
    tension_cols: List[str],
    moisture_targets: Dict[str, float],
) -> Dict[str, float]:
    """Compute target tension for each level based on moisture targets."""
    targets: Dict[str, float] = {}
    for i, m_col in enumerate(sorted(moisture_cols)):
        if i >= len(sorted(tension_cols)):
            break
        t_col = sorted(tension_cols)[i]
        x = pd.to_numeric(data[m_col], errors="coerce")
        y = pd.to_numeric(data[t_col], errors="coerce")
        mask = (~x.isna()) & (~y.isna())
        if mask.sum() > 1:
            slope, intercept = np.polyfit(x[mask], y[mask], 1)
        else:
            slope = -2.0
            med = np.nanmedian(y.values)
            intercept = float(med) if np.isfinite(med) else 0.0

        predicted = intercept + slope * float(moisture_targets.get(m_col, 0.0))
        predicted = float(max(-100.0, min(1500.0, predicted)))
        targets[t_col] = predicted
    return targets


###############################################################################
# CLIMATE MODELLING FUNCTIONS
###############################################################################
def build_seasonal_models(
    df: pd.DataFrame,
    humidity_cols: List[str],
    temperature_cols: List[str],
) -> Dict[str, Dict[str, np.ndarray]]:
    """
    Fit sinusoidal regression models for humidity and temperature for each room.

    y ≈ β1*sin(2π*doy/365) + β2*cos(2π*doy/365) + β0
    """
    df = df.copy()
    df["dayofyear"] = df["timestamp"].dt.dayofyear
    df["sin"] = np.sin(2 * np.pi * df["dayofyear"] / 365.0)
    df["cos"] = np.cos(2 * np.pi * df["dayofyear"] / 365.0)

    models: Dict[str, Dict[str, np.ndarray]] = {}
    for room, g in df.groupby("room"):
        models[room] = {}

        X_base = g[["sin", "cos"]].values
        X_design = np.hstack([X_base, np.ones((len(X_base), 1))])

        if humidity_cols:
            y_h = pd.to_numeric(g[humidity_cols].astype(float).mean(axis=1), errors="coerce").values
            if np.isfinite(y_h).sum() > 5:
                coeffs_h, *_ = np.linalg.lstsq(X_design, y_h, rcond=None)
                models[room]["humidity"] = coeffs_h

        if temperature_cols:
            y_t = pd.to_numeric(g[temperature_cols].astype(float).mean(axis=1), errors="coerce").values
            if np.isfinite(y_t).sum() > 5:
                coeffs_t, *_ = np.linalg.lstsq(X_design, y_t, rcond=None)
                models[room]["temperature"] = coeffs_t

    models = {k: v for k, v in models.items() if v}
    return models


def get_predictions_over_year(
    room: str,
    models: Dict[str, Dict[str, np.ndarray]],
    seasonal_avgs: Dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Return predicted humidity and temperature for each day of the year for the given room."""
    days = np.arange(1, 366)
    preds: Dict[str, List[float]] = {"dayofyear": days.tolist(), "humidity": [], "temperature": []}

    sin_vals = np.sin(2 * np.pi * days / 365.0)
    cos_vals = np.cos(2 * np.pi * days / 365.0)

    for idx, doy in enumerate(days):
        use_avg = room in seasonal_avgs and int(doy) in seasonal_avgs[room].index

        # humidity
        h_val = float("nan")
        if use_avg and "hum_avg" in seasonal_avgs[room].columns:
            h_val = float(seasonal_avgs[room].loc[int(doy), "hum_avg"])
        if np.isnan(h_val) and room in models and "humidity" in models[room]:
            c = models[room]["humidity"]
            h_val = float(c[0] * sin_vals[idx] + c[1] * cos_vals[idx] + c[2])
        preds["humidity"].append(h_val)

        # temperature
        t_val = float("nan")
        if use_avg and "temp_avg" in seasonal_avgs[room].columns:
            t_val = float(seasonal_avgs[room].loc[int(doy), "temp_avg"])
        if np.isnan(t_val) and room in models and "temperature" in models[room]:
            c = models[room]["temperature"]
            t_val = float(c[0] * sin_vals[idx] + c[1] * cos_vals[idx] + c[2])
        preds["temperature"].append(t_val)

    return pd.DataFrame(preds)


###############################################################################
# MAIN APPLICATION
###############################################################################
st.title("Upload CSV or ZIP files")

uploaded_files = st.file_uploader("Upload CSV files", accept_multiple_files=True, type="csv")
uploaded_zip = st.file_uploader("Upload a ZIP file containing CSV files", type="zip")

if uploaded_zip and hasattr(uploaded_zip, "size") and uploaded_zip.size > 50_000_000:
    st.warning("Uploaded ZIP is quite large; this may take a while or could crash the dashboard.")

data = pd.DataFrame()
if uploaded_files:
    data = load_data(uploaded_files)
elif uploaded_zip:
    data = load_data_from_zip(uploaded_zip)
else:
    st.stop()

if data.empty:
    st.stop()

if "timestamp" not in data.columns:
    st.error("Missing required column: 'timestamp'.")
    st.stop()

try:
    data["timestamp"] = pd.to_datetime(data["timestamp"], format="%d.%m.%Y %H:%M:%S", errors="raise")
except Exception as e:
    st.error(f"Error converting timestamp: {e}")
    st.stop()

sampling_options = {
    "Raw (10 min)": "10T",
    "30 min": "30T",
    "Hourly": "1H",
    "Daily": "1D",
}
freq_labels = list(sampling_options.keys())
default_index = freq_labels.index("Hourly") if "Hourly" in freq_labels else 0
selected_freq_label = st.selectbox("Select Data Frequency (downsampling)", freq_labels, index=default_index)
selected_freq = sampling_options[selected_freq_label]

data = resample_data(data, selected_freq)

numeric_cols = data.select_dtypes(include="number").columns
if len(numeric_cols) > 0:
    data[numeric_cols] = data[numeric_cols].interpolate().ffill().bfill()

columns_order = ["device", "room"] + [c for c in data.columns if c not in ["device", "room"]]
data = data[columns_order]

###############################################################################
# PREPARE CLIMATE MODELS AND SEASONAL AVERAGES
###############################################################################
lowercase_cols = {c.lower(): c for c in data.columns}

atmos_humidity_cols = [lowercase_cols[c] for c in lowercase_cols if "humidity" in c and "atmosphere" in c]
atmos_temperature_cols = [lowercase_cols[c] for c in lowercase_cols if "temperature" in c and "atmosphere" in c]

humidity_cols_model = (
    atmos_humidity_cols
    if atmos_humidity_cols
    else [lowercase_cols[c] for c in lowercase_cols if "humidity" in c]
)
temperature_cols_model = (
    atmos_temperature_cols
    if atmos_temperature_cols
    else [lowercase_cols[c] for c in lowercase_cols if "temperature" in c]
)

models: Dict[str, Dict[str, np.ndarray]] = {}
if humidity_cols_model or temperature_cols_model:
    models = build_seasonal_models(data, humidity_cols_model, temperature_cols_model)

seasonal_avgs: Dict[str, pd.DataFrame] = {}
if humidity_cols_model or temperature_cols_model:
    tmp_data = data.copy()
    tmp_data["dayofyear"] = tmp_data["timestamp"].dt.dayofyear

    cols = []
    if humidity_cols_model:
        tmp_data["hum_avg"] = pd.to_numeric(tmp_data[humidity_cols_model].astype(float).mean(axis=1), errors="coerce")
        cols.append("hum_avg")
    if temperature_cols_model:
        tmp_data["temp_avg"] = pd.to_numeric(tmp_data[temperature_cols_model].astype(float).mean(axis=1), errors="coerce")
        cols.append("temp_avg")

    for room, group in tmp_data.groupby("room"):
        daily_stats = group.groupby("dayofyear")[cols].mean().copy()
        full_index = pd.RangeIndex(1, 366)
        daily_stats = daily_stats.reindex(full_index)
        daily_stats = daily_stats.interpolate().ffill().bfill()
        seasonal_avgs[room] = daily_stats

###############################################################################
# FILTER SELECTIONS FOR ROOMS, DEVICES AND PARAMETERS
###############################################################################
devices_list = np.sort(data["device"].dropna().unique())
device_options = ["All"] + devices_list.tolist()

rooms_list = np.sort(data["room"].dropna().unique())
room_options = ["All"] + rooms_list.tolist()

st.title("Sensor Data Dashboard")

selected_rooms = st.multiselect("Select Rooms", room_options, default=["All"])
if "All" in selected_rooms:
    selected_rooms = rooms_list.tolist()

selected_devices = st.multiselect("Select Devices", device_options, default=["All"])
if "All" in selected_devices:
    selected_devices = devices_list.tolist()

all_columns = [
    c
    for c in data.columns
    if c not in ["timestamp", "device", "room"] and not looks_like_data_point(c)
]

standard_parameters = [
    "Atmosphere temperature (°C)", "Atmosphere humidity (% RH)",
    "FRT tension 1 (kPa)", "FRT tension 2 (kPa)", "FRT tension 3 (kPa)",
    "SMT temperature 1 (°C)", "SMT temperature 2 (°C)", "SMT temperature 3 (°C)",
    "SMT water content 1 (%)", "SMT water content 2 (%)", "SMT water content 3 (%)",
]
dcc_parameters = [
    "SMT water content 1 (%)", "SMT water content 2 (%)", "SMT water content 3 (%)",
    "Current Days Irrigation (L)", "Lysimeter weight (Kg)", "LBC tank weight (Kg)",
]

try:
    start_date, end_date = st.date_input(
        "Select Date Range", [data["timestamp"].min(), data["timestamp"].max()]
    )
    if start_date > end_date:
        st.error("Error: End date must be after start date.")
        st.stop()
except Exception as e:
    st.error(f"Error with date input: {e}")
    st.stop()

filtered_data = data[
    (data["room"].isin(selected_rooms))
    & (data["device"].isin(selected_devices))
    & (data["timestamp"] >= pd.to_datetime(start_date))
    & (data["timestamp"] <= pd.to_datetime(end_date))
].copy()

if filtered_data.empty:
    st.write("No data available for the selected parameters and date range.")
    st.stop()

###############################################################################
# TAB SETUP
###############################################################################
tab_visuals, tab_insights, tab_climate = st.tabs(["Visualizations", "Insights", "Climate predictions"])

###############################################################################
# TAB 1: VISUALISATIONS
###############################################################################
with tab_visuals:
    st.subheader("Visualizations")
    parameter_options = (["Standard Parameters", "DCC project"] + all_columns) if all_columns else ["Standard Parameters", "DCC project"]
    selected_parameters = st.multiselect("Select Parameters", parameter_options)

    final_parameters: List[str] = []
    seen = set()

    if "Standard Parameters" in selected_parameters:
        final_parameters += [p for p in standard_parameters if p in data.columns]
    if "DCC project" in selected_parameters:
        final_parameters += [p for p in dcc_parameters if p in data.columns]
    final_parameters += [p for p in selected_parameters if p not in ["Standard Parameters", "DCC project"]]

    final_parameters = [x for x in final_parameters if not (x in seen or seen.add(x))]

    if final_parameters and not filtered_data.empty:
        for parameter in final_parameters:
            fig = px.line()
            for device in selected_devices:
                ddf = filtered_data[filtered_data["device"] == device]
                if parameter in ddf.columns:
                    fig.add_scatter(
                        x=ddf["timestamp"],
                        y=ddf[parameter],
                        mode="lines",
                        name=f"{device} - {parameter}",
                        connectgaps=False,
                    )
            fig.update_layout(
                title=f"Time Series Comparison for {parameter}",
                xaxis_title="Timestamp",
                yaxis_title=parameter,
                height=600,
            )
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Raw Data")
        st.dataframe(filtered_data.head(100))
        if len(filtered_data) > 100:
            st.info(f"Showing first 100 of {len(filtered_data)} rows out of {len(filtered_data)} total.")
    else:
        st.write("No data available for the selected parameters and date range.")

###############################################################################
# TAB 2: INSIGHTS
###############################################################################
with tab_insights:
    st.subheader("Insights")

    insight_task = st.selectbox(
        "Select an insights task",
        ["Homogenize moisture content", "Detect sensor issues"],
    )

    moisture_cols = [col for col in filtered_data.columns if str(col).startswith("SMT water content")]
    tension_cols = [col for col in filtered_data.columns if str(col).startswith("FRT tension")]

    cols_to_summarize = moisture_cols + tension_cols
    summary_df = (
        filtered_data.groupby("device")[cols_to_summarize]
        .mean(numeric_only=True)
        .reset_index()
        if cols_to_summarize
        else pd.DataFrame()
    )

    if insight_task == "Homogenize moisture content":
        st.markdown(
            """
            **Objective:** Bring soil moisture and tension levels across all devices into consistent ranges.
            Specify your desired moisture content for each level below. The dashboard derives tension targets
            automatically (linear fit, clamped to [-100, 1500] kPa) and recommends whether to add or remove water.

            Suggested targets (example): ≈35 % VWC in clay (Level 1), ≈30 % in loam (Level 2), ≈20 % in sand (Level 3).
            """
        )

        if summary_df.empty or not moisture_cols or not tension_cols:
            st.info("No data available for moisture homogenisation (missing moisture/tension columns).")
        else:
            default_targets_moisture = {
                m_col: float(np.round(summary_df[m_col].median(), 2))
                for m_col in sorted(moisture_cols)
            }
            moisture_inputs: Dict[str, float] = {}

            cols_m = st.columns(len(sorted(moisture_cols)))
            for i, m_col in enumerate(sorted(moisture_cols)):
                with cols_m[i]:
                    moisture_inputs[m_col] = float(
                        st.number_input(
                            f"Level {i+1}",
                            min_value=0.0,
                            max_value=100.0,
                            value=float(default_targets_moisture[m_col]),
                            step=0.1,
                            format="%.1f",
                        )
                    )

            target_tension_values = derive_tension_targets(filtered_data, moisture_cols, tension_cols, moisture_inputs)

            st.write("### Derived target tension (kPa)")
            for i, t_col in enumerate(sorted(tension_cols)):
                if t_col in target_tension_values:
                    st.write(f"Level {i+1}: {target_tension_values[t_col]:.1f} kPa")

            st.write("### Average moisture and tension per device")

            moist_melt = summary_df.melt(
                id_vars=["device"],
                value_vars=moisture_cols,
                var_name="Sensor",
                value_name="Moisture (%)",
            )
            fig_moist = px.bar(
                moist_melt,
                x="device",
                y="Moisture (%)",
                color="Sensor",
                barmode="group",
                title="Average soil moisture per device",
            )
            st.plotly_chart(fig_moist, use_container_width=True)

            tension_melt = summary_df.melt(
                id_vars=["device"],
                value_vars=tension_cols,
                var_name="Sensor",
                value_name="Tension (kPa)",
            )
            fig_tension = px.bar(
                tension_melt,
                x="device",
                y="Tension (kPa)",
                color="Sensor",
                barmode="group",
                title="Average soil tension per device",
            )
            st.plotly_chart(fig_tension, use_container_width=True)

            recs = []
            for _, row in summary_df.iterrows():
                device = row["device"]
                device_rec: Dict[str, object] = {"device": device}
                for i, m_col in enumerate(sorted(moisture_cols)):
                    if i >= len(sorted(tension_cols)):
                        continue
                    t_col = sorted(tension_cols)[i]
                    moisture_val = float(row.get(m_col, np.nan))
                    tension_val = float(row.get(t_col, np.nan))

                    moisture_diff = float(moisture_inputs[m_col] - moisture_val) if np.isfinite(moisture_val) else 0.0
                    tension_target = float(target_tension_values.get(t_col, np.nan))
                    tension_diff = float(tension_val - tension_target) if (np.isfinite(tension_val) and np.isfinite(tension_target)) else 0.0

                    dryness_score = moisture_diff + tension_diff / 10.0
                    action = "Add" if dryness_score > 0 else "Remove"

                    water_per_percent = 0.67
                    change_litres = float(np.round(abs(moisture_diff) * water_per_percent, 2))

                    device_rec[f"Level {i+1} action"] = action
                    device_rec[f"Level {i+1} change (L)"] = change_litres

                recs.append(device_rec)

            rec_df = pd.DataFrame(recs)
            st.write("### Irrigation/Suction recommendations")
            st.write(
                "For each device and soil depth, the table shows whether to add or remove water and the "
                "approximate litres needed to reach your target VWC."
            )
            st.dataframe(rec_df)

    elif insight_task == "Detect sensor issues":
        st.markdown(
            """
            **Objective:** Identify probes that may be disconnected or malfunctioning.

            Flags:
            - Moisture sensors reporting 0% (or NaN) across the selected date range
            - Tension readings with |value| > 1500 kPa (outside specified range)
            """
        )

        if summary_df.empty:
            st.info("No data to analyse for sensor issues.")
        else:
            alerts: List[str] = []
            for _, row in summary_df.iterrows():
                device = row["device"]

                for i, m_col in enumerate(moisture_cols):
                    moisture_val = row.get(m_col, np.nan)
                    if pd.isna(moisture_val) or float(moisture_val) == 0.0:
                        alerts.append(f"{device}: Moisture sensor level {i+1} appears disconnected or reporting 0%.")

                for i, t_col in enumerate(tension_cols):
                    tension_val = row.get(t_col, np.nan)
                    if pd.isna(tension_val) or abs(float(tension_val)) > 1500:
                        alerts.append(f"{device}: Tensiometer level {i+1} out of range (|value| > 1500 kPa).")

            if alerts:
                for alert in alerts:
                    st.error(alert)
                st.info("Note: Alert routing/emailing is not implemented in this dashboard build.")
            else:
                st.success("No sensor issues detected in the selected data range.")

###############################################################################
# TAB 3: CLIMATE PREDICTIONS
###############################################################################
with tab_climate:
    st.subheader("Climate predictions")
    st.markdown(
        """
        **Objective:** Use historical data to model and predict atmospheric humidity and temperature.

        The model uses sine/cosine terms of day-of-year for each room (seasonal cycle).
        Select room(s) and an experiment date range to view predicted ranges and curves.
        """
    )

    if not models:
        st.warning(
            "Climate models are unavailable. Ensure your data contains columns with 'humidity' and/or 'temperature'."
        )
    else:
        available_rooms = sorted(models.keys())
        selected_rooms_pred = st.multiselect(
            "Select room(s) for prediction", available_rooms, default=available_rooms
        )

        min_date = data["timestamp"].min().date()
        max_date = data["timestamp"].max().date()

        exp_start_date = st.date_input(
            "Experiment range start date", value=min_date, min_value=min_date, max_value=max_date, key="exp_start_date"
        )
        exp_end_date = st.date_input(
            "Experiment range end date", value=min_date, min_value=min_date, max_value=max_date, key="exp_end_date"
        )

        if exp_start_date > exp_end_date:
            st.error("Experiment start date must be <= end date.")
            st.stop()

        if selected_rooms_pred:
            start_doy = exp_start_date.timetuple().tm_yday
            end_doy = exp_end_date.timetuple().tm_yday

            if start_doy <= end_doy:
                selected_doys = list(range(start_doy, end_doy + 1))
            else:
                selected_doys = list(range(start_doy, 366)) + list(range(1, end_doy + 1))

            range_rows = []
            plot_rows = []

            for room in selected_rooms_pred:
                yearly_preds = get_predictions_over_year(room, models, seasonal_avgs)
                yearly_preds_range = yearly_preds[yearly_preds["dayofyear"].isin(selected_doys)].copy()

                hum_range = None
                temp_range = None

                if not yearly_preds_range.empty and "humidity" in yearly_preds_range.columns:
                    hum_min = float(np.nanmin(yearly_preds_range["humidity"].values))
                    hum_max = float(np.nanmax(yearly_preds_range["humidity"].values))
                    if np.isfinite(hum_min) and np.isfinite(hum_max):
                        hum_range = (hum_min, hum_max)

                if not yearly_preds_range.empty and "temperature" in yearly_preds_range.columns:
                    temp_min = float(np.nanmin(yearly_preds_range["temperature"].values))
                    temp_max = float(np.nanmax(yearly_preds_range["temperature"].values))
                    if np.isfinite(temp_min) and np.isfinite(temp_max):
                        temp_range = (temp_min, temp_max)

                range_rows.append({
                    "Room": room,
                    "Humidity Range (% RH)": f"{hum_range[0]:.2f} – {hum_range[1]:.2f}" if hum_range else "N/A",
                    "Temperature Range (°C)": f"{temp_range[0]:.2f} – {temp_range[1]:.2f}" if temp_range else "N/A",
                })

                if not yearly_preds_range.empty:
                    for var in ["humidity", "temperature"]:
                        if var in yearly_preds_range.columns:
                            df_var = yearly_preds_range[["dayofyear", var]].copy().rename(columns={var: "Value"})
                            df_var["Variable"] = var
                            df_var["Room"] = room
                            plot_rows.append(df_var)

            if range_rows:
                st.subheader("Predicted ranges for selected rooms")
                st.dataframe(pd.DataFrame(range_rows))

            if plot_rows:
                plot_df = pd.concat(plot_rows, ignore_index=True)
                for var in ["humidity", "temperature"]:
                    df_var = plot_df[plot_df["Variable"] == var]
                    if not df_var.empty:
                        fig = px.line(
                            df_var,
                            x="dayofyear",
                            y="Value",
                            color="Room",
                            title=f"Predicted {var} for selected rooms (day {start_doy} to {end_doy})",
                        )
                        fig.update_layout(
                            xaxis_title="Day of Year",
                            yaxis_title=f"Predicted {var}",
                        )
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No predicted values available for the selected range and rooms.")

            st.caption(
                "*Note: Predictions are based on historical conditions and seasonal averaging + sinusoidal fallback. "
                "Use predicted ranges as guidance rather than exact forecasts.*"
            )

###############################################################################
# FOOTER
###############################################################################
st.markdown("<hr style='margin-top:50px; margin-bottom:10px;'>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align: center; color: grey; font-size: 14px;'>"
    "© 2025 NPEC Ecotron Module - Visualization Dashboard by Dr. Vinicius Lube | "
    "Phenomics Engineer Innovation Lead</p>",
    unsafe_allow_html=True,
)
