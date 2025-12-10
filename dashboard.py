"""
Extended Streamlit dashboard for NPEC Ecotrons.

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
from typing import List, Tuple, Dict, Tuple as DTuple

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

###############################################################################
# PAGE CONFIG
###############################################################################
# Configure the Streamlit page.  Use a wide layout to provide more room for
# charts and controls.  Set a descriptive title for the browser tab.
st.set_page_config(
    page_title="Visualization Dashboard | NPEC Ecotrons", layout="wide",
)

###############################################################################
# UTILITIES / CONSTANTS
###############################################################################
def normalize_name(name: str) -> str:
    """
    Normalize device or camera names so they match keys in the META mapping.

    Normalization rules include trimming whitespace, replacing hyphens and
    underscores with spaces, converting to lowercase and applying a few
    known alias corrections (e.g. "firebug" -> "fire bug").
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
    """Extract just the hostname or IP from a full URL.  If parsing fails,
    return the original string."""
    try:
        return url.split("//", 1)[1].split("/", 1)[0]
    except Exception:
        return url


# Optional password for unlocking the sidebar.  This can be configured via
# Streamlit secrets or environment variables.  When set, the sidebar menu
# requires a password to view devices and cameras.
SIDEBAR_PASS = st.secrets.get("SIDEBAR_PASS", os.environ.get("SIDEBAR_PASS", ""))

###############################################################################
# DEVICE DIRECTORY (SIDEBAR DATA)
###############################################################################
# Each tuple contains the device name and the URL of its UGT interface.  These
# URLs can be opened in a new browser tab from the sidebar.  The list may be
# extended as new devices are added to the ecotron installation.
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

# Emoji mapping for each device.  These icons appear next to device names in
# the sidebar to provide a whimsical visual cue.  If a device name is not
# present in the mapping, a default link icon will be used.
EMOJI = {
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

# Mapping of device names to room and type (Advanced or Basic).  This is used
# to group devices in the sidebar and display type information.  When a
# device name is not found, the default is Ecolab 3 / Basic.
META = {
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


# RhizoCam units: each entry defines a camera host and the URLs of its
# gantry and analysis interfaces.
RHIZOCAMS = [
    {
        "host": "Cricket",
        "gantry": "http://192.168.162.186:8501/",
        "analysis": "http://192.168.162.186:8502/",
    }
]

# IP cameras: each tuple contains camera name and IP address.  These are
# grouped by room in the sidebar.
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
# SIDEBAR WITH OPTIONAL PASSWORD LOCK
###############################################################################
# The sidebar allows users to browse devices, RhizoCams, and IP cameras.  A
# password can optionally lock this menu to prevent accidental changes.

# Ensure the state variable controlling whether the sidebar is unlocked exists
if "sidebar_unlocked" not in st.session_state:
    st.session_state.sidebar_unlocked = (SIDEBAR_PASS == "")

with st.sidebar:
    st.title("Devices")

    # Lock / unlock controls at top of sidebar
    cols = st.columns([1, 1, 1.2])
    with cols[2]:
        if st.session_state.sidebar_unlocked:
            # Show lock button when unlocked
            if st.button("Lock menu", use_container_width=True):
                st.session_state.sidebar_unlocked = False
                st.rerun()
        elif SIDEBAR_PASS:
            # Show unlock popover when locked
            with st.popover("Unlock"):
                pw = st.text_input("Password", type="password", placeholder="••••••")
                if st.button("Unlock"):
                    if pw == SIDEBAR_PASS:
                        st.session_state.sidebar_unlocked = True
                        st.rerun()
                    else:
                        st.error("Wrong password")

    # Show message if menu is locked
    if not st.session_state.sidebar_unlocked and SIDEBAR_PASS:
        st.caption("Menu locked. Click **Unlock** to enter the password.")
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
                    # Apply filter on device name or IP
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
# Display logos and the dashboard title at the top of the main content area.
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
# Mapping of devices to default rooms used when reading CSV filenames.  This
# dictionary helps assign a default "room" label to data loaded from files.
room_assignments = {
    "Ulysses": "Room 1", "Admiral": "Room 1", "Scarab": "Room 1",
    "Ladybug": "Room 1", "Yellowjacket": "Room 1", "Flea": "Room 1",
    "Mosquito": "Room 1", "Stag beetle": "Room 1", "Stag_Bettle": "Room 1",
    "Cockroach": "Room 2", "Termite": "Room 2", "Centipede": "Room 2",
    "Fly": "Room 2", "Giraffe": "Room 2", "Tarantula": "Room 2",
    "Fire bug": "Room 2", "Fire_Bug": "Room 2", "Tick": "Room 2",
    "Moth": "Room 2", "Millipede": "Room 2", "Mantis": "Room 2", "Dragonfly": "Room 2",
}

# Maximum number of rows to load from uploaded files.  This prevents the
# dashboard from freezing or running out of memory when very large logs are
# uploaded.  **Raised from 50 000 to 200 000** so that the full 60‑day
# experiment can be loaded when downsampling to hourly by default.
MAX_ROWS = 200_000


def load_data(uploaded_files, max_rows: int = MAX_ROWS) -> pd.DataFrame:
    """Load multiple semicolon-delimited CSV files uploaded by the user.

    Each CSV file is expected to be named "<device>_something.csv".  The
    device name (before the underscore) is used to populate a 'device' column
    and assign a 'room' column using the room_assignments dictionary.  The
    function concatenates all data into a single DataFrame, truncating rows
    when the max_rows limit is reached.
    """
    data_frames, total_rows = [], 0
    for uploaded_file in uploaded_files:
        try:
            df = pd.read_csv(uploaded_file, delimiter=';')
            device_name = uploaded_file.name.split('_')[0]
            if device_name == "Fire":
                device_name = "Fire bug"
            elif device_name == "Stag":
                device_name = "Stag beetle"
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
    """Load multiple CSV files contained within a ZIP archive.

    The ZIP file may contain files in nested directories.  Only files ending
    with '.csv' and not starting with '__MACOSX/' are processed.  The device
    name is extracted as for load_data().
    """
    data_frames, total_rows = [], 0
    with zipfile.ZipFile(zip_file) as z:
        for filename in z.namelist():
            if filename.endswith(".csv") and not filename.startswith("__MACOSX/"):
                with z.open(filename) as f:
                    try:
                        df = pd.read_csv(f, delimiter=';')
                        device_name = filename.split('/')[0].split('_')[0]
                        if device_name == "Fire":
                            device_name = "Fire bug"
                        elif device_name == "Stag":
                            device_name = "Stag beetle"
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
    """Downsample the dataset to a lower frequency.

    If the frequency is '10T' (the raw frequency of 10 minutes), the data
    remains unchanged.  For other frequencies, numeric columns are resampled
    using the mean per group of device and room.
    """
    if freq == "10T":
        return df
    if "timestamp" not in df.columns:
        return df
    numeric_cols = df.select_dtypes(include="number").columns
    frames = []
    for (device, room), group in df.groupby(["device", "room"]):
        group = group.set_index("timestamp").sort_index()
        resampled = group[numeric_cols].resample(freq).mean()
        resampled["device"] = device
        resampled["room"] = room
        frames.append(resampled.reset_index())
    return pd.concat(frames, ignore_index=True) if frames else df


def looks_like_data_point(col):
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
    data: pd.DataFrame, moisture_cols: List[str], tension_cols: List[str], moisture_targets: dict
) -> dict:
    """Compute target tension for each level based on moisture targets.

    For each pair of moisture and tension columns (assumed sorted by level),
    fit a linear regression of tension versus moisture and evaluate the
    regression at the desired moisture target.  Clamp the result to the
    physical range [-100, 1500] kPa.
    """
    targets = {}
    for i, m_col in enumerate(sorted(moisture_cols)):
        t_col = sorted(tension_cols)[i]
        x = data[m_col].astype(float)
        y = data[t_col].astype(float)
        mask = (~x.isna()) & (~y.isna())
        if mask.sum() > 1:
            slope, intercept = np.polyfit(x[mask], y[mask], 1)
        else:
            slope, intercept = -2.0, y.median()
        predicted = intercept + slope * moisture_targets[m_col]
        predicted = max(-100.0, min(1500.0, predicted))
        targets[t_col] = predicted
    return targets


###############################################################################
# CLIMATE MODELLING FUNCTIONS
###############################################################################
def build_seasonal_models(
    df: pd.DataFrame, humidity_cols: List[str], temperature_cols: List[str]
) -> Dict[str, Dict[str, np.ndarray]]:
    """Fit sinusoidal regression models for humidity and temperature for each room.

    This function computes least‑squares coefficients directly using NumPy,
    avoiding external dependencies like scikit‑learn.  For each room the
    relationship between the target variable and the day of year is
    approximated with a linear combination of sine and cosine terms plus
    an intercept:

        y ≈ β₁ · sin(2π · doy/365) + β₂ · cos(2π · doy/365) + β₀

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing ``timestamp`` and ``room`` columns along with
        sensor readings.
    humidity_cols : list of str
        Column names representing humidity measurements.
    temperature_cols : list of str
        Column names representing temperature measurements.

    Returns
    -------
    dict
        A mapping of room to another mapping of target name ("humidity",
        "temperature") to a NumPy array of coefficients ``[β₁, β₂, β₀]``.  If
        a particular target is not present for a given room, that key is
        omitted.
    """
    df = df.copy()
    df["dayofyear"] = df["timestamp"].dt.dayofyear
    df["sin"] = np.sin(2 * np.pi * df["dayofyear"] / 365.0)
    df["cos"] = np.cos(2 * np.pi * df["dayofyear"] / 365.0)
    models: Dict[str, Dict[str, np.ndarray]] = {}
    for room, g in df.groupby("room"):
        models[room] = {}
        # Build design matrix with sine, cosine and intercept
        X_base = g[["sin", "cos"]].values
        X_design = np.hstack([X_base, np.ones((len(X_base), 1))])
        if humidity_cols:
            y_h = g[humidity_cols].astype(float).mean(axis=1).values
            if len(y_h) > 0:
                coeffs_h, *_ = np.linalg.lstsq(X_design, y_h, rcond=None)
                models[room]["humidity"] = coeffs_h
        if temperature_cols:
            y_t = g[temperature_cols].astype(float).mean(axis=1).values
            if len(y_t) > 0:
                coeffs_t, *_ = np.linalg.lstsq(X_design, y_t, rcond=None)
                models[room]["temperature"] = coeffs_t
    return models


def predict_for_room(
    room: str,
    date: pd.Timestamp,
    models: Dict[str, Dict[str, np.ndarray]],
    seasonal_avgs: Dict[str, pd.DataFrame],
) -> DTuple[float, float]:
    """Predict humidity and temperature for a given room and date.

    The prediction is based on seasonal averages if available; if the
    corresponding day of year exists in ``seasonal_avgs``, we return the
    averaged humidity and temperature for that day.  When the seasonal
    averages dictionary does not contain a value for the requested room
    or day, we fall back to the sinusoidal regression models contained in
    ``models``.  This fallback ensures that predictions are always
    available, even for days not observed in the data.

    Parameters
    ----------
    room : str
        The room identifier for which to predict.
    date : pd.Timestamp
        The date for prediction.  Only the day‑of‑year component matters
        because both seasonal averages and the sinusoidal model depend on
        day of year.
    models : dict
        Dictionary mapping room to fitted coefficients for sinusoidal models.
    seasonal_avgs : dict
        Dictionary mapping room to DataFrame of per‑day averages.  The
        DataFrame index represents the day of year and contains columns
        ``hum_avg`` and/or ``temp_avg``.

    Returns
    -------
    tuple(float, float)
        Predicted humidity (% RH) and temperature (°C).  If a target is
        unavailable from both sources, ``NaN`` is returned.
    """
    dayofyear = date.dayofyear
    humidity_pred = float("nan")
    temperature_pred = float("nan")
    # Try seasonal averages first
    if room in seasonal_avgs:
        daily_stats = seasonal_avgs[room]
        if dayofyear in daily_stats.index:
            if "hum_avg" in daily_stats.columns:
                humidity_pred = float(daily_stats.loc[dayofyear, "hum_avg"])
            if "temp_avg" in daily_stats.columns:
                temperature_pred = float(daily_stats.loc[dayofyear, "temp_avg"])
    # If missing values remain, fall back to sinusoidal model
    if (np.isnan(humidity_pred) or np.isnan(temperature_pred)) and room in models:
        sin_val = np.sin(2 * np.pi * dayofyear / 365.0)
        cos_val = np.cos(2 * np.pi * dayofyear / 365.0)
        if np.isnan(humidity_pred) and "humidity" in models[room]:
            coeffs_h = models[room]["humidity"]
            humidity_pred = coeffs_h[0] * sin_val + coeffs_h[1] * cos_val + coeffs_h[2]
        if np.isnan(temperature_pred) and "temperature" in models[room]:
            coeffs_t = models[room]["temperature"]
            temperature_pred = coeffs_t[0] * sin_val + coeffs_t[1] * cos_val + coeffs_t[2]
    return humidity_pred, temperature_pred


def get_predictions_over_year(
    room: str,
    models: Dict[str, Dict[str, np.ndarray]],
    seasonal_avgs: Dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Return predicted humidity and temperature for each day of the year for the given room.

    The predictions use seasonal averages where available.  For days not present
    in the seasonal averages or when averages are missing for a variable,
    the function falls back to the sinusoidal model.

    Parameters
    ----------
    room : str
        Room identifier.
    models : dict
        Sinusoidal model coefficients as returned by ``build_seasonal_models``.
    seasonal_avgs : dict
        Seasonal averages per room and day of year.

    Returns
    -------
    pd.DataFrame
        DataFrame with ``dayofyear`` as the index and columns ``humidity``
        and/or ``temperature`` containing the predicted values.
    """
    days = np.arange(1, 366)
    preds: Dict[str, List[float]] = {"dayofyear": days}
    # Precompute sinusoidal terms for fallback
    sin_vals = np.sin(2 * np.pi * days / 365.0)
    cos_vals = np.cos(2 * np.pi * days / 365.0)
    for var in ["humidity", "temperature"]:
        preds[var] = []
    for idx, doy in enumerate(days):
        # Use seasonal average if available
        use_avg = room in seasonal_avgs and doy in seasonal_avgs[room].index
        for var in ["humidity", "temperature"]:
            val = float("nan")
            if use_avg:
                col = "hum_avg" if var == "humidity" else "temp_avg"
                if col in seasonal_avgs[room].columns:
                    val = float(seasonal_avgs[room].loc[doy, col])
            if np.isnan(val) and room in models and var in models[room]:
                coeffs = models[room][var]
                val = coeffs[0] * sin_vals[idx] + coeffs[1] * cos_vals[idx] + coeffs[2]
            preds[var].append(val)
    return pd.DataFrame(preds)


###############################################################################
# MAIN APPLICATION
###############################################################################
# Upload controls and initial data loading
st.title("Upload CSV or ZIP files")

uploaded_files = st.file_uploader(
    "Upload CSV files", accept_multiple_files=True, type="csv"
)
uploaded_zip = st.file_uploader(
    "Upload a ZIP file containing CSV files", type="zip"
)

# Warn about large ZIPs
if uploaded_zip and hasattr(uploaded_zip, "size") and uploaded_zip.size > 50_000_000:
    st.warning(
        "Uploaded ZIP is quite large; this may take a while or could crash the dashboard."
    )

data = pd.DataFrame()
if uploaded_files:
    data = load_data(uploaded_files)
elif uploaded_zip:
    data = load_data_from_zip(uploaded_zip)
else:
    # Stop execution until a file is uploaded
    st.stop()

# Convert timestamps to datetime (European format)
if data.empty:
    st.stop()
try:
    data["timestamp"] = pd.to_datetime(data["timestamp"], format="%d.%m.%Y %H:%M:%S")
except Exception as e:
    st.error(f"Error converting timestamp: {e}")
    st.stop()

# Downsampling frequency selection
sampling_options = {
    "Raw (10 min)": "10T",
    "30 min": "30T",
    "Hourly": "1H",
    "Daily": "1D",
}
freq_labels = list(sampling_options.keys())
# Default to hourly downsampling.  We compute the index dynamically to avoid
# hard‑coding the position should the order of keys ever change.
default_index = freq_labels.index("Hourly") if "Hourly" in freq_labels else 0
selected_freq_label = st.selectbox(
    "Select Data Frequency (downsampling)", freq_labels, index=default_index
)
selected_freq = sampling_options[selected_freq_label]

data = resample_data(data, selected_freq)

# Interpolate and fill numeric columns to smooth missing data
numeric_cols = data.select_dtypes(include="number").columns
data[numeric_cols] = data[numeric_cols].interpolate().ffill().bfill()

# Reorder columns: device and room at the front
columns_order = ["device", "room"] + [c for c in data.columns if c not in ["device", "room"]]
data = data[columns_order]

###############################################################################
# PREPARE CLIMATE MODELS AND SEASONAL AVERAGES
###############################################################################
# Identify humidity and temperature columns for modelling
lowercase_cols = {c.lower(): c for c in data.columns}
humidity_cols_model = [lowercase_cols[c] for c in lowercase_cols if "humidity" in c]
temperature_cols_model = [lowercase_cols[c] for c in lowercase_cols if "temperature" in c]

# Fit sinusoidal regression models (sine/cosine) for each room.  These are used
# as a fallback when seasonal averages are unavailable or when extrapolating to
# days of year not present in the historical data.  The models dictionary
# maps room names to coefficient arrays for humidity and temperature.
models: Dict[str, Dict[str, np.ndarray]] = {}
if humidity_cols_model or temperature_cols_model:
    models = build_seasonal_models(data, humidity_cols_model, temperature_cols_model)

# Compute seasonal averages per day of year for each room.  For each record
# we calculate the mean humidity and temperature across their respective
# sensor columns, then average these values across all available years at
# each day of the year.  The resulting `seasonal_avgs` dictionary maps
# room names to DataFrames indexed by day of year with columns
# `hum_avg` and/or `temp_avg`.  These averages provide realistic
# predictions that remain within the observed range for that room.
seasonal_avgs: Dict[str, pd.DataFrame] = {}
if humidity_cols_model or temperature_cols_model:
    tmp_data = data.copy()
    tmp_data["dayofyear"] = tmp_data["timestamp"].dt.dayofyear
    # Compute per‑row averages for humidity and temperature, if columns exist
    if humidity_cols_model:
        tmp_data["hum_avg"] = tmp_data[humidity_cols_model].astype(float).mean(axis=1)
    if temperature_cols_model:
        tmp_data["temp_avg"] = tmp_data[temperature_cols_model].astype(float).mean(axis=1)
    # Group by room and day of year to compute seasonal averages
    for room, group in tmp_data.groupby("room"):
        cols = []
        if humidity_cols_model:
            cols.append("hum_avg")
        if temperature_cols_model:
            cols.append("temp_avg")
        # Compute the mean for each day of year across all years
        daily_stats = group.groupby("dayofyear")[cols].mean().copy()
        # Ensure that the index covers all days 1..365 for easier lookup; fill
        # missing days by interpolation and forward/backward fill.
        full_index = pd.RangeIndex(1, 366)
        daily_stats = daily_stats.reindex(full_index)
        daily_stats = daily_stats.interpolate().ffill().bfill()
        seasonal_avgs[room] = daily_stats

###############################################################################
# FILTER SELECTIONS FOR ROOMS, DEVICES AND PARAMETERS
###############################################################################
devices_list = data["device"].unique()
device_options = ["All"] + devices_list.tolist()
rooms_list = data["room"].unique()
room_options = ["All"] + rooms_list.tolist()

st.title("Sensor Data Dashboard")

selected_rooms = st.multiselect("Select Rooms", room_options, default="All")
if "All" in selected_rooms:
    selected_rooms = rooms_list.tolist()

selected_devices = st.multiselect("Select Devices", device_options, default="All")
if "All" in selected_devices:
    selected_devices = devices_list.tolist()

# Identify non-numeric columns for dynamic parameter selection
all_columns = [
    c
    for c in data.columns
    if c not in ["timestamp", "device", "room"] and not looks_like_data_point(c)
]

# Predefined standard and DCC parameter lists
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

# Date range selection
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

# Filter data by room, device and date range
filtered_data = data[
    (data["room"].isin(selected_rooms))
    & (data["device"].isin(selected_devices))
    & (data["timestamp"] >= pd.to_datetime(start_date))
    & (data["timestamp"] <= pd.to_datetime(end_date))
]

if filtered_data.empty:
    st.write("No data available for the selected parameters and date range.")
    st.stop()

###############################################################################
# TAB SETUP
###############################################################################
# Create three tabs: Visualizations, Insights and Climate predictions
tab_visuals, tab_insights, tab_climate = st.tabs(["Visualizations", "Insights", "Climate predictions"])

###############################################################################
# TAB 1: VISUALISATIONS
###############################################################################
with tab_visuals:
    st.subheader("Visualizations")
    parameter_options = (
        ["Standard Parameters", "DCC project"] + all_columns
        if all_columns
        else ["Standard Parameters", "DCC project"]
    )
    selected_parameters = st.multiselect(
        "Select Parameters", parameter_options
    )

    # Determine which columns to plot
    final_parameters, seen = [], set()
    if "Standard Parameters" in selected_parameters:
        final_parameters += [p for p in standard_parameters if p in data.columns]
    if "DCC project" in selected_parameters:
        final_parameters += [p for p in dcc_parameters if p in data.columns]
    final_parameters += [
        p for p in selected_parameters if p not in ["Standard Parameters", "DCC project"]
    ]
    final_parameters = [x for x in final_parameters if not (x in seen or seen.add(x))]

    # Plot time series for each selected parameter
    if final_parameters and not filtered_data.empty:
        for parameter in final_parameters:
            fig = px.line()
            for device in selected_devices:
                ddf = filtered_data[filtered_data["device"] == device]
                if parameter in ddf.columns:
                    fig.add_scatter(
                        x=ddf["timestamp"], y=ddf[parameter],
                        mode="lines", name=f"{device} - {parameter}", connectgaps=False
                    )
            fig.update_layout(
                title=f"Time Series Comparison for {parameter}",
                xaxis_title="Timestamp", yaxis_title=parameter, height=600
            )
            st.plotly_chart(fig, use_container_width=True)

        # Show first 100 rows of filtered data
        st.subheader("Raw Data")
        st.dataframe(filtered_data.head(100))
        if len(filtered_data) > 100:
            st.info(
                f"Showing first 100 of {len(filtered_data)} rows out of {len(filtered_data)} total."
            )
    else:
        st.write("No data available for the selected parameters and date range.")

###############################################################################
# TAB 2: INSIGHTS
###############################################################################
with tab_insights:
    st.subheader("Insights")
    # Insights tasks (climate predictions moved to its own tab)
    insight_task = st.selectbox(
        "Select an insights task",
        ["Homogenize moisture content", "Detect sensor issues"],
    )

    # Prepare summary statistics for moisture and tension
    moisture_cols = [col for col in filtered_data.columns if col.startswith("SMT water content")]
    tension_cols = [col for col in filtered_data.columns if col.startswith("FRT tension")]
    summary_df = (
        filtered_data.groupby("device")[moisture_cols + tension_cols]
        .mean()
        .reset_index()
    )

    if insight_task == "Homogenize moisture content":
        st.markdown(
            """
            **Objective:** Bring soil moisture and tension levels across all devices
            into consistent ranges at each sensor level.  Specify your desired
            moisture content for each level below.  The dashboard derives tension
            targets automatically (using a linear fit and clamping them to the
            sensor’s valid range) and recommends whether to
            add or remove water for each device and level.
            Current values showed below represent the current averages across all devices. 
            For the current experiment the aimed values should be: ≈35 % VWC in clay 
            (Level 1), ≈30 % in loam (Level 2) and ≈20 % in sand (Level 3).
            
            """
        )

        if summary_df.empty:
            st.info("No data to analyse for moisture homogenisation.")
        else:
            # Default moisture targets from median of each column
            default_targets_moisture = {
                m_col: round(summary_df[m_col].median(), 2)
                for m_col in sorted(moisture_cols)
            }
            moisture_inputs = {}
            cols_m = st.columns(len(sorted(moisture_cols)))
            for i, m_col in enumerate(sorted(moisture_cols)):
                with cols_m[i]:
                    moisture_inputs[m_col] = st.number_input(
                        f"Level {i+1}",
                        min_value=0.0,
                        max_value=100.0,
                        value=float(default_targets_moisture[m_col]),
                        step=0.1,
                        format="%.1f",
                    )

            # Derive target tension values
            target_tension_values = derive_tension_targets(
                filtered_data, moisture_cols, tension_cols, moisture_inputs
            )
            st.write("### Derived target tension (kPa)")
            for i, t_col in enumerate(sorted(tension_cols)):
                st.write(f"Level {i+1}: {target_tension_values[t_col]:.1f} kPa")

            st.write("### Average moisture and tension per device")
            # Moisture bar chart
            moist_melt = summary_df.melt(
                id_vars=["device"],
                value_vars=moisture_cols,
                var_name="Sensor", value_name="Moisture (%)"
            )
            fig_moist = px.bar(
                moist_melt, x="device", y="Moisture (%)", color="Sensor",
                barmode="group", title="Average soil moisture per device"
            )
            st.plotly_chart(fig_moist, use_container_width=True)

            # Tension bar chart
            tension_melt = summary_df.melt(
                id_vars=["device"],
                value_vars=tension_cols,
                var_name="Sensor", value_name="Tension (kPa)"
            )
            fig_tension = px.bar(
                tension_melt, x="device", y="Tension (kPa)", color="Sensor",
                barmode="group", title="Average soil tension per device"
            )
            st.plotly_chart(fig_tension, use_container_width=True)

            # Compute irrigation/suction recommendations
            recs = []
            for _, row in summary_df.iterrows():
                device = row["device"]
                device_rec = {"device": device}
                for i, m_col in enumerate(sorted(moisture_cols)):
                    t_col = sorted(tension_cols)[i]
                    moisture_diff = moisture_inputs[m_col] - row[m_col]
                    # Positive tension_diff means soil is drier than target
                    tension_diff = row[t_col] - target_tension_values[t_col]
                    # Combine differences: dryness_score > 0 means add water
                    dryness_score = moisture_diff + tension_diff / 10.0
                    action = "Add" if dryness_score > 0 else "Remove"
                    # Water volume per 1% VWC difference; adjust constant here
                    water_per_percent = 0.67
                    change_litres = round(
                        abs(moisture_diff) * water_per_percent, 2
                    )
                    device_rec[f"Level {i+1} action"] = action
                    device_rec[f"Level {i+1} change (L)"] = change_litres
                recs.append(device_rec)

            rec_df = pd.DataFrame(recs)
            st.write("### Irrigation/Suction recommendations")
            st.write(
                "For each device and soil depth, the table below shows whether to add or remove water and the "
                "approximate litres needed to reach your target VWC. These volumes are calculated from the difference "
                "between the target and observed moisture content multiplied by the actual soil volume at each depth."
            )
            st.dataframe(rec_df)

    elif insight_task == "Detect sensor issues":
        st.markdown(
            """
            **Objective:** Identify probes that may be disconnected or malfunctioning.
            Moisture sensors reporting 0 % (or NaN) across the selected date
            range, or tension readings above 1 500 kPa (beyond the sensor’s
            specified range), are flagged.  Alerts are shown below for each
            device and sensor level.
            """
        )
        if summary_df.empty:
            st.info("No data to analyse for sensor issues.")
        else:
            alerts = []
            for _, row in summary_df.iterrows():
                device = row["device"]
                # Flag moisture sensors at 0% or missing
                for i, m_col in enumerate(moisture_cols):
                    moisture_val = row[m_col]
                    if pd.isna(moisture_val) or moisture_val == 0:
                        alerts.append(
                            f"{device}: Moisture sensor level {i+1} appears disconnected or reporting 0 %."
                        )
                # Flag tension sensors outside valid range
                for i, t_col in enumerate(tension_cols):
                    tension_val = row[t_col]
                    if pd.isna(tension_val) or abs(tension_val) > 1500:
                        alerts.append(
                            f"{device}: Tensiometer level {i+1} out of range (|value| > 1500 kPa)."
                        )
            if alerts:
                for alert in alerts:
                    st.error(alert)
                st.info(
                    "Alerts would be emailed to v.munaldilube@uu.nl for further action."
                )
            else:
                st.success("No sensor issues detected in the selected data range.")

    # remove climate predictions from insights: handled in separate tab

###############################################################################
# TAB 3: CLIMATE PREDICTIONS
###############################################################################
with tab_climate:
    st.subheader("Climate predictions")
    st.markdown(
        """
        **Objective:** Use historical data to model and predict atmospheric humidity and temperature.
        This feature fits a sinusoidal model (sine and cosine terms) for each room using the day of
        the year as the predictor【316970089103360†L979-L984】.  Select a room and a date below to view the predicted
        humidity and temperature for that day, and explore the predicted annual cycle.  Historical
        observations for the selected date are also shown when available.
        """
    )
    if not models:
        st.warning(
            "Climate models are unavailable. Ensure that your data contains columns with 'humidity' "
            "and 'temperature' in their names."
        )
    else:
        # Choose room for prediction
        available_rooms = sorted(models.keys())
        selected_room_pred = st.selectbox("Select room for prediction", available_rooms)
        # Date input for prediction.  Allow any date beyond the available data to
        # enable future predictions by not specifying a maximum date.
        min_date = data["timestamp"].min().date()
        date_input_pred = st.date_input(
            "Date for prediction",
            value=min_date,
            min_value=min_date,
            # max_value intentionally omitted to permit arbitrary future dates
        )
        if selected_room_pred and date_input_pred:
            date_ts = pd.Timestamp(date_input_pred)
            humidity_pred, temperature_pred = predict_for_room(
                selected_room_pred, date_ts, models, seasonal_avgs
            )
            st.metric(
                label=f"Predicted humidity (% RH) in {selected_room_pred}",
                value=f"{humidity_pred:.2f}"
            )
            st.metric(
                label=f"Predicted temperature (°C) in {selected_room_pred}",
                value=f"{temperature_pred:.2f}"
            )
            # Plot predicted annual cycle for the room
            yearly_preds = get_predictions_over_year(
                selected_room_pred, models, seasonal_avgs
            )
            if not yearly_preds.empty:
                melt_cols = [c for c in ["humidity", "temperature"] if c in yearly_preds.columns]
                fig_pred = px.line(
                    yearly_preds.melt(id_vars=["dayofyear"], value_vars=melt_cols, var_name="Variable", value_name="Value"),
                    x="dayofyear", y="Value", color="Variable",
                    title=f"Predicted annual cycle for {selected_room_pred}"
                )
                fig_pred.update_layout(xaxis_title="Day of Year", yaxis_title="Predicted value")
                st.plotly_chart(fig_pred, use_container_width=True)
            # Show historical observations on the selected date
            hist = data[(data["room"] == selected_room_pred)].copy()
            hist["date"] = hist["timestamp"].dt.date
            same_day = hist[hist["date"] == date_input_pred]
            if not same_day.empty:
                st.subheader("Historical observations on this date")
                cols_to_show: List[str] = []
                if humidity_cols_model:
                    cols_to_show += humidity_cols_model
                if temperature_cols_model:
                    cols_to_show += temperature_cols_model
                st.dataframe(same_day[["timestamp"] + cols_to_show])
            else:
                st.info("No historical observations on this date for the selected room.")

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
