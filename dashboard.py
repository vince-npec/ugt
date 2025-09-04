"""
Streamlit dashboard for NPEC Ecotrons with user‑defined moisture targets
and automatically derived tension targets.  This version corrects the
recommendation logic by treating higher tension as drier soil and
clamping predicted tensions to the sensor’s valid range (–100 to +1500 kPa).

This revised code also incorporates the actual lysimeter geometry and
field‑capacity moisture targets.  The top and middle soil layers (0–0.3 m
and 0.3–0.6 m) each hold about 59 L of soil, and the bottom layer
(0.6–1.0 m) holds about 79 L.  Recommended water additions or removals
are calculated as (target VWC – observed VWC)/100 × zone volume for
each level, yielding litres of water to add (positive) or remove
(negative).  Default moisture targets correspond to field capacity for
potato roots: ~35 % in the upper clay layer, 30 % in the middle
loam layer and 20 % in the lower sand layer.
"""

import os
import re
import zipfile
from typing import List, Tuple

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
    """Normalize device/camera names so they match META keys."""
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
    """Extract an IP (or host) from a URL."""
    try:
        return url.split("//", 1)[1].split("/", 1)[0]
    except Exception:
        return url

# Optional password for the sidebar
SIDEBAR_PASS = st.secrets.get("SIDEBAR_PASS", os.environ.get("SIDEBAR_PASS", ""))

###############################################################################
# NEW CONSTANTS FOR GEOMETRY AND TARGETS
###############################################################################
# Each lysimeter’s top and middle layers (~0.3 m) hold about 59 L of soil,
# while the lower layer (~0.4 m) holds about 79 L.  These volumes are used
# to calculate irrigation/suction recommendations in litres.
ZONE_VOLUMES = [59.0, 59.0, 79.0]

# Default volumetric water content targets (% VWC) corresponding to field
# capacity for potatoes: clay (upper layer) ~35 %, loam (middle layer) ~30 %,
# sand (lower layer) ~20 %.  These values are used as defaults when the user
# does not specify their own targets.
DEFAULT_MOISTURE_TARGETS = {
    "SMT water content 1 (%)": 35.0,
    "SMT water content 2 (%)": 30.0,
    "SMT water content 3 (%)": 20.0,
}

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
    return META.get(normalize_name(name), ("Ecolab 3", "Basic"))

# RhizoCam units
RHIZOCAMS = [
    {"host": "Cricket", "gantry": "http://192.168.162.186:8501/", "analysis": "http://192.168.162.186:8502/"},
]
# IP cameras
IP_CAMERAS = [
    ("Admiral","192.168.162.45"), ("Ant","192.168.162.65"),
    ("Bumblebee","192.168.162.68"), ("Caterpillar","192.168.162.77"),
    ("Centipede","192.168.162.62"), ("Cockroach","192.168.162.54"),
    ("Cricket","192.168.162.79"), ("Dragonfly","192.168.162.52"),
    ("Dung beetle","192.168.162.64"), ("Fire bug","192.168.162.61"),
    ("Flea","192.168.162.50"), ("Fly","192.168.162.55"),
    ("Giraffe","192.168.162.161"), ("Hercules","192.168.162.71"),
    ("Honeybee","192.168.162.69"), ("Hornet","192.168.162.66"),
    ("Ladybug","192.168.162.47"), ("Longhorn","192.168.162.74"),
    ("Mantis","192.168.162.56"), ("Maybug","192.168.162.67"),
    ("Millipede","192.168.162.60"), ("Mosquito","192.168.162.49"),
    ("Moth","192.168.162.53"), ("Potato beetle","192.168.162.78"),
    ("Scarab","192.168.162.46"), ("Scorpion","192.168.162.76"),
    ("Stag beetle","192.168.162.48"), ("Stick","192.168.162.130"),
    ("Stink","192.168.162.70"), ("Strider","192.168.162.72"),
    ("Tarantula","192.168.162.63"), ("Termite","192.168.162.58"),
    ("Tick","192.168.162.57"), ("Ulysses","192.168.162.44"),
    ("Weaver","192.168.162.75"), ("Yellowjacket","192.168.162.140"),
]

###############################################################################
# SIDEBAR (with optional password lock)
###############################################################################
if "sidebar_unlocked" not in st.session_state:
    st.session_state.sidebar_unlocked = (SIDEBAR_PASS == "")

with st.sidebar:
    st.title("Devices")

    # Lock / Unlock controls
    cols = st.columns([1, 1, 1.2])
    with cols[2]:
        if st.session_state.sidebar_unlocked:
            if st.button("Lock menu", use_container_width=True):
                st.session_state.sidebar_unlocked = False
                st.rerun()
        elif SIDEBAR_PASS:
            with st.popover("Unlock"):
                pw = st.text_input("Password", type="password", placeholder="••••••")
                if st.button("Unlock"):
                    if pw == SIDEBAR_PASS:
                        st.session_state.sidebar_unlocked = True
                        st.rerun()
                    else:
                        st.error("Wrong password")

    # When locked, hide the rest of the menu
    if not st.session_state.sidebar_unlocked and SIDEBAR_PASS:
        st.caption("Menu locked. Click **Unlock** to enter the password.")
    else:
        # Filters
        q = st.text_input("Filter by name or IP", value="")
        room_filter = st.selectbox("Room", ["All", "Ecolab 1", "Ecolab 2", "Ecolab 3"], index=0)

        rooms_order = ["Ecolab 1", "Ecolab 2", "Ecolab 3"] if room_filter == "All" else [room_filter]

        # Devices (by room)
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

        st.markdown("---")

        # RhizoCam units
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

        st.markdown("---")

        # IP cameras — grouped by room
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
# HEADER WITH LOGOS + TITLE
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
# ANALYTICS AND DATA LOADING
###############################################################################
room_assignments = {
    "Ulysses": "Room 1", "Admiral": "Room 1", "Scarab": "Room 1",
    "Ladybug": "Room 1", "Yellowjacket": "Room 1", "Flea": "Room 1",
    "Mosquito": "Room 1", "Stag beetle": "Room 1", "Stag_Bettle": "Room 1",
    "Cockroach": "Room 2", "Termite": "Room 2", "Centipede": "Room 2",
    "Fly": "Room 2", "Giraffe": "Room 2", "Tarantula": "Room 2",
    "Fire bug": "Room 2", "Fire_Bug": "Room 2", "Tick": "Room 2",
    "Moth": "Room 2", "Millipede": "Room 2", "Mantis": "Room 2", "Dragonfly": "Room 2",
}
MAX_ROWS = 50_000

def load_data(uploaded_files, max_rows: int = MAX_ROWS) -> pd.DataFrame:
    """Load multiple CSV files provided by the user."""
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
                if total_rows + len(df) > max_rows:
                    df = df.iloc[: max_rows - total_rows]
                data_frames.append(df)
                total_rows += len(df)
                if total_rows >= max_rows:
                    st.warning(f"Loaded {max_rows} rows (limit reached for performance).")
                    break
        except Exception as e:
            st.error(f"Error reading {uploaded_file.name}: {e}")
    if not data_frames:
        st.error("No data frames were created from the uploaded files.")
        return pd.DataFrame()
    return pd.concat(data_frames, ignore_index=True)

def load_data_from_zip(zip_file, max_rows: int = MAX_ROWS) -> pd.DataFrame:
    """Load multiple CSV files from a ZIP archive."""
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
                            if total_rows + len(df) > max_rows:
                                df = df.iloc[: max_rows - total_rows]
                            data_frames.append(df)
                            total_rows += len(df)
                            if total_rows >= max_rows:
                                st.warning(f"Loaded {max_rows} rows (limit reached for performance).")
                                break
                    except Exception as e:
                        st.error(f"Error reading {filename}: {e}")
    if not data_frames:
        st.error("No data frames were created from the ZIP file.")
        return pd.DataFrame()
    return pd.concat(data_frames, ignore_index=True)

def resample_data(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    """Downsample the dataset using the specified frequency."""
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
    """
    Heuristically determine if a column name is likely to represent a data
    point (numeric), based on simple string checks.
    """
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

def derive_tension_targets(data: pd.DataFrame,
                           moisture_cols: List[str],
                           tension_cols: List[str],
                           moisture_targets: dict) -> dict:
    """
    Fit a linear regression between moisture and tension for each level and compute
    a target tension for each level, clamped to the sensor range (–100 to +1500 kPa).
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
            # Fallback slope/intercept
            slope, intercept = -2.0, y.median()
        predicted = intercept + slope * moisture_targets[m_col]
        # Clamp predicted tension to valid range
        predicted = max(-100, min(1500, predicted))
        targets[t_col] = predicted
    return targets

###############################################################################
# USER INTERFACE: DATA UPLOAD
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
try:
    data["timestamp"] = pd.to_datetime(data["timestamp"], format="%d.%m.%Y %H:%M:%S")
except Exception as e:
    st.error(f"Error converting timestamp: {e}")
    st.stop()

###############################################################################
# DATA DOWNSAMPLING AND INTERPOLATION
###############################################################################
sampling_options = {"Raw (10 min)": "10T", "30 min": "30T", "Hourly": "1H", "Daily": "1D"}
selected_freq_label = st.selectbox("Select Data Frequency (downsampling)", list(sampling_options.keys()), index=0)
selected_freq = sampling_options[selected_freq_label]

data = resample_data(data, selected_freq)

numeric_cols = data.select_dtypes(include="number").columns
data[numeric_cols] = data[numeric_cols].interpolate().ffill().bfill()

columns_order = ["device", "room"] + [c for c in data.columns if c not in ["device", "room"]]
data = data[columns_order]

###############################################################################
# SELECTION OF ROOMS AND DEVICES
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

###############################################################################
# DATE RANGE FILTERING
###############################################################################
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
]

if filtered_data.empty:
    st.write("No data available for the selected parameters and date range.")
    st.stop()

###############################################################################
# TABS: VISUALISATIONS AND INSIGHTS
###############################################################################
tab_visuals, tab_insights = st.tabs(["Visualizations", "Insights"])

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

    final_parameters, seen = [], set()
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
                        x=ddf["timestamp"], y=ddf[parameter],
                        mode="lines", name=f"{device} - {parameter}", connectgaps=False
                    )
            fig.update_layout(
                title=f"Time Series Comparison for {parameter}",
                xaxis_title="Timestamp", yaxis_title=parameter, height=600
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
        [
            "Homogenize moisture content",
            "Detect sensor issues",
        ],
    )

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
            add or remove water for each device and level.  Volumes are based on
            the actual soil volumes at each depth (~59 L for 0–0.6 m and ~79 L for
            0.6–1.0 m).
            """
        )

        if summary_df.empty:
            st.info("No data to analyse for moisture homogenisation.")
        else:
            # Ask user for moisture targets; use default field-capacity targets if available
            default_targets_moisture = {}
            for i, m_col in enumerate(sorted(moisture_cols)):
                default_targets_moisture[m_col] = DEFAULT_MOISTURE_TARGETS.get(
                    m_col, round(summary_df[m_col].median(), 2)
                )

            moisture_inputs = {}
            cols_m = st.columns(len(sorted(moisture_cols)))
            for i, m_col in enumerate(sorted(moisture_cols)):
                with cols_m[i]:
                    moisture_inputs[m_col] = st.number_input(
                        f"Level {i+1} target VWC (%)",
                        min_value=0.0,
                        max_value=100.0,
                        value=float(default_targets_moisture[m_col]),
                        step=0.1,
                        format="%.1f",
                    )

            # Derive tension targets from moisture targets
            target_tension_values = derive_tension_targets(
                filtered_data, moisture_cols, tension_cols, moisture_inputs
            )
            st.write("### Derived target tension (kPa)")
            for i, t_col in enumerate(sorted(tension_cols)):
                st.write(f"Level {i+1}: {target_tension_values[t_col]:.1f} kPa")

            st.write("### Average moisture and tension per device")
            # Plot moisture averages
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

            # Plot tension averages
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

            # Compute irrigation recommendations: calculate litres based on zone volumes
            recs = []
            for _, row in summary_df.iterrows():
                device = row["device"]
                device_rec = {"device": device}
                for i, m_col in enumerate(sorted(moisture_cols)):
                    # Calculate difference between target and observed moisture (% VWC)
                    moisture_diff_percent = moisture_inputs[m_col] - row[m_col]
                    # Determine zone volume in litres for this level
                    zone_vol = ZONE_VOLUMES[i] if i < len(ZONE_VOLUMES) else ZONE_VOLUMES[-1]
                    # Convert percentage difference to litres (positive to add, negative to remove)
                    change_litres = (moisture_diff_percent / 100.0) * zone_vol
                    action = "Add" if change_litres > 0 else "Remove"
                    device_rec[f"Level {i+1} action"] = action
                    device_rec[f"Level {i+1} change (L)"] = round(abs(change_litres), 2)
                recs.append(device_rec)

            rec_df = pd.DataFrame(recs)
            st.write("### Irrigation/Suction recommendations")
            st.write(
                "For each device and soil depth, the table below shows whether to "
                "add or remove water and the approximate litres needed to reach your target VWC. "
                "These volumes are calculated from the difference between the target and observed "
                "moisture content multiplied by the actual soil volume at each depth."
            )
            st.dataframe(rec_df)

    elif insight_task == "Detect sensor issues":
        st.markdown(
            """
            **Objective:** Identify probes that may be disconnected or malfunctioning.
            Moisture sensors reporting 0 % (or NaN) across the selected date
            range, or tension readings above 1 500 kPa (beyond the sensor’s
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
                for i, m_col in enumerate(moisture_cols):
                    moisture_val = row[m_col]
                    if pd.isna(moisture_val) or moisture_val == 0:
                        alerts.append(f"{device}: Moisture sensor level {i+1} appears disconnected or reporting 0 %.")
                for i, t_col in enumerate(tension_cols):
                    tension_val = row[t_col]
                    if pd.isna(tension_val) or abs(tension_val) > 1500:
                        alerts.append(f"{device}: Tensiometer level {i+1} out of range (|value| > 1500 kPa).")
            if alerts:
                for alert in alerts:
                    st.error(alert)
                st.info(
                    "Alerts would be emailed to v.munaldilube@uu.nl for further action."
                )
            else:
                st.success("No sensor issues detected in the selected data range.")

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
