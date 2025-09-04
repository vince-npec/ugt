"""
Streamlit dashboard for NPEC Ecotrons
This file replicates the original dashboard logic provided by the user and
extends it with an additional “Insights” tab.  The Insights tab makes it
possible to analyse moisture and tension data across devices and provide
suggestions for homogenising soil moisture levels or detecting sensor
issues.  Broken or disconnected probes are highlighted and alerts are
displayed (and would be emailed to the operator in a production system).

The existing page structure – including the sidebar with devices, RhizoCam
units and cameras, the data upload interface, and the standard visualisation
tools – remains unchanged.  The new tab lives alongside the original
visualisations so that users can choose between viewing raw sensor
information and performing higher‑level analyses.
"""

import os
import re
from typing import List, Tuple

import pandas as pd
import plotly.express as px
import streamlit as st
import zipfile

###############################################################################
# PAGE CONFIG
###############################################################################
# Set up the Streamlit page.  Use a wide layout to give charts more room.
st.set_page_config(page_title="Visualization Dashboard | NPEC Ecotrons", layout="wide")

###############################################################################
# UTILITIES / CONSTANTS
###############################################################################
def normalize_name(name: str) -> str:
    """
    Normalize device/camera names so they match META keys.  This helper
    collapses whitespace and handles a few common aliases so that lookups
    against the META mapping are robust.
    """
    s = name.strip().lower().replace("-", " ").replace("_", " ")
    # Known aliases
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
    """Extract an IP (or host) from a URL.

    If parsing fails the original string is returned.  This helper is used
    throughout the dashboard to display the host portion of device URLs in
    the sidebar.
    """
    try:
        return url.split("//", 1)[1].split("/", 1)[0]
    except Exception:
        return url


# Sidebar password (optional).  This can be set via Streamlit secrets or the
# environment.  When set, the sidebar will be locked by default until the
# correct password is entered.
SIDEBAR_PASS = st.secrets.get("SIDEBAR_PASS", os.environ.get("SIDEBAR_PASS", ""))

###############################################################################
# DEVICE DIRECTORY (SIDEBAR DATA)
###############################################################################
# List of Ecotron devices and their control UI endpoints.  These are used
# purely for display purposes in the sidebar – clicking a link opens the
# respective device’s UI in a new browser tab.
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

# Emoji mapping for cute icons next to each device.  Keys are normalised via
# ``normalize_name`` and values are strings containing the emoji.
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

# Room/type mapping.  Each device is assigned to a room and a type (Advanced
# vs Basic) for grouping in the sidebar.  Normalisation via ``normalize_name``
# ensures that strings like "Stag beetle" and "Stag  beetle" map correctly.
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
    """Return (room, type) for a given device name.

    If the device isn’t found, default to ("Ecolab 3", "Basic").  Names
    undergo normalisation via ``normalize_name`` before the lookup.
    """
    return META.get(normalize_name(name), ("Ecolab 3", "Basic"))


# RhizoCam units (per host Ecotron).  Each entry contains the host device name
# along with the addresses for gantry and analysis interfaces.  These are
# displayed in the sidebar for quick access.
RHIZOCAMS = [
    {"host": "Cricket", "gantry": "http://192.168.162.186:8501/", "analysis": "http://192.168.162.186:8502/"},
]


# IP camera list (name -> ip).  IP cameras are grouped by room in the sidebar.
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
# SIDEBAR (with optional password lock)
###############################################################################
# The sidebar lists all devices, RhizoCam units and IP cameras.  A password
# lock can hide these menus to prevent casual browsing.  Users can filter
# devices by name or IP and collapse groups by room.

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

        # RhizoCam units — only in their host room
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
# Display the top-of-page header with the Ecotron module and NPEC logos.  These
# are loaded from GitHub (as in the original dashboard) and scaled to fill the
# header area.

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
# The following section handles data upload, parsing and downsampling.  It
# matches the original dashboard logic but has been factored so that data
# loading occurs outside of the visualisation and insights tabs.  This allows
# both tabs to reuse the same filtered data without re-reading or resampling.

# Room assignment mapping used for default room grouping of CSV files.
room_assignments = {
    "Ulysses": "Room 1", "Admiral": "Room 1", "Scarab": "Room 1",
    "Ladybug": "Room 1", "Yellowjacket": "Room 1", "Flea": "Room 1",
    "Mosquito": "Room 1", "Stag beetle": "Room 1", "Stag_Bettle": "Room 1",
    "Cockroach": "Room 2", "Termite": "Room 2", "Centipede": "Room 2",
    "Fly": "Room 2", "Giraffe": "Room 2", "Tarantula": "Room 2",
    "Fire bug": "Room 2", "Fire_Bug": "Room 2", "Tick": "Room 2",
    "Moth": "Room 2", "Millipede": "Room 2", "Mantis": "Room 2", "Dragonfly": "Room 2",
}

# Limit the maximum number of rows to load for performance reasons.
MAX_ROWS = 50_000


def load_data(uploaded_files, max_rows: int = MAX_ROWS) -> pd.DataFrame:
    """
    Load multiple CSV files provided by the user.

    Each CSV must use a semicolon (;) delimiter and begins with the device name
    followed by an underscore.  The device name is extracted from the file
    name and assigned to a new "device" column.  A "room" column is also
    assigned using ``room_assignments``.  Rows beyond ``max_rows`` are
    truncated to protect the dashboard from large uploads.
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
    """
    Load multiple CSV files from a ZIP archive.

    The ZIP archive may contain files in subdirectories.  Only files ending
    in `.csv` (and not starting with ``__MACOSX/``) are processed.  Device
    names are extracted as for ``load_data``.
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
    """
    Downsample the dataset using the specified frequency.

    If ``freq`` is '10T' (the raw 10‑minute interval), the data is returned
    unchanged.  Otherwise the numeric columns are resampled using the mean,
    grouped by device and room.  Non-numeric columns are dropped during
    resampling; device and room columns are added back after grouping.
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
    """
    Heuristically determine if a column name is likely to represent a data
    point (numeric), based on simple string checks.  This helps separate
    numeric sensor data from metadata when building a list of selectable
    parameters for charting.
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


###############################################################################
# USER INTERFACE: DATA UPLOAD
###############################################################################

st.title("Upload CSV or ZIP files")

uploaded_files = st.file_uploader("Upload CSV files", accept_multiple_files=True, type="csv")
uploaded_zip = st.file_uploader("Upload a ZIP file containing CSV files", type="zip")

# Warn about large ZIP files
if uploaded_zip and hasattr(uploaded_zip, "size") and uploaded_zip.size > 50_000_000:
    st.warning("Uploaded ZIP is quite large; this may take a while or could crash the dashboard.")

# Load data from either multiple CSV files or a single ZIP archive.
data = pd.DataFrame()
if uploaded_files:
    data = load_data(uploaded_files)
elif uploaded_zip:
    data = load_data_from_zip(uploaded_zip)
else:
    # No data uploaded yet; stop the app here.
    st.stop()

# Convert timestamps.  The log files use a European format (DD.MM.YYYY HH:MM:SS).
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

# Interpolate numeric columns and forward/backfill to smooth missing data.
numeric_cols = data.select_dtypes(include="number").columns
data[numeric_cols] = data[numeric_cols].interpolate().ffill().bfill()

# Reorder columns for consistency: device and room first, followed by others.
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

# Identify columns that are not clearly data points; these represent metadata or
# descriptive text and should not appear in the parameter selection list.
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

# Filter data by room, device and date range.
filtered_data = data[
    (data["room"].isin(selected_rooms))
    & (data["device"].isin(selected_devices))
    & (data["timestamp"] >= pd.to_datetime(start_date))
    & (data["timestamp"] <= pd.to_datetime(end_date))
]

# If no data remains after filtering, stop early.
if filtered_data.empty:
    st.write("No data available for the selected parameters and date range.")
    st.stop()


###############################################################################
# TABS: VISUALISATIONS AND INSIGHTS
###############################################################################
# Create two tabs: one for the original parameter visualisations and another
# called “Insights” for higher-level analysis.  Both tabs share the same
# filtered dataset computed above.

tab_visuals, tab_insights = st.tabs(["Visualizations", "Insights"])

###############################################################################
# TAB 1: VISUALISATIONS
###############################################################################
with tab_visuals:
    st.subheader("Visualizations")
    # Build the parameter selection list.  Users can choose between a preset
    # collection of standard parameters, a DCC project set, or any other
    # available column in the data that isn't obviously a numeric value.
    parameter_options = (
        ["Standard Parameters", "DCC project"] + all_columns
        if all_columns
        else ["Standard Parameters", "DCC project"]
    )
    selected_parameters = st.multiselect(
        "Select Parameters", parameter_options
    )

    # Expand the selection into an explicit list of columns to plot.
    final_parameters, seen = [], set()
    if "Standard Parameters" in selected_parameters:
        final_parameters += [p for p in standard_parameters if p in data.columns]
    if "DCC project" in selected_parameters:
        final_parameters += [p for p in dcc_parameters if p in data.columns]
    final_parameters += [p for p in selected_parameters if p not in ["Standard Parameters", "DCC project"]]
    final_parameters = [x for x in final_parameters if not (x in seen or seen.add(x))]

    # Plot each selected parameter as a time series.  Separate lines are drawn
    # for each selected device.  If no parameters are selected, display a
    # placeholder message.
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

        # Display the first 100 rows of the filtered dataset for inspection.
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
    # Choose an analysis task.  At present the dashboard supports homogenising
    # moisture content across all devices and detecting potential sensor
    # malfunctions.  Additional tasks can be added here in the future.
    insight_task = st.selectbox(
        "Select an insights task", [
            "Homogenize moisture content", 
            "Detect sensor issues",
        ],
    )

    # Compute summary statistics up front to avoid redundant calculations.
    # Group by device and compute mean moisture and tension per soil layer.
    moisture_cols = [
        col for col in filtered_data.columns if col.startswith("SMT water content")
    ]
    tension_cols = [
        col for col in filtered_data.columns if col.startswith("FRT tension")
    ]
    summary_df = (
        filtered_data.groupby("device")[moisture_cols + tension_cols]
        .mean()
        .reset_index()
    )

    if insight_task == "Homogenize moisture content":
        st.markdown(
            """
            **Objective:** Bring soil moisture levels across all devices into a
            consistent range at each sensor level.  The plots below show the
            average volumetric water content (VWC) and tension for each device.
            Devices with moisture far from the overall median may require
            adjustments to their irrigation schedules.
            """
        )

        if summary_df.empty:
            st.info("No data to analyse for moisture homogenisation.")
        else:
            # Determine target moisture as the median across all devices for each
            # soil level.  These targets can be used to compute suggested
            # irrigation adjustments.
            target_moisture = summary_df[moisture_cols].median()

            st.write("### Average moisture and tension per device")
            # Display a bar chart for moisture by device and layer.
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

            # Display a bar chart for tension by device and layer.
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

            # Calculate differences from the target moisture for recommendations.
            recs = []
            for _, row in summary_df.iterrows():
                device = row["device"]
                adjustments = {}
                for col in moisture_cols:
                    diff = target_moisture[col] - row[col]
                    # Suggest change proportionally: positive diff -> increase irrigation.
                    # The factor 0.05 is arbitrary and can be tuned based on system response.
                    adj = round(diff * 0.05, 3)
                    adjustments[col] = adj
                recs.append((device, adjustments))

            # Convert recommendations into a DataFrame for display.
            rec_df = pd.DataFrame([
                {"device": device, **adj} for device, adj in recs
            ])
            # Rename columns for readability.
            rec_df = rec_df.rename(columns={
                moisture_cols[i]: f"Level {i+1} change (L)" for i in range(len(moisture_cols))
            })

            st.write("### Suggested irrigation adjustments")
            st.write(
                "Values represent the recommended change in daily irrigation volume (litres). "
                "Positive values indicate increasing irrigation; negative values indicate reducing it."
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
                for i, col in enumerate(moisture_cols):
                    moisture_val = row[col]
                    if pd.isna(moisture_val) or moisture_val == 0:
                        alerts.append(f"{device}: Moisture sensor level {i+1} appears disconnected or reporting 0 %.")
                for i, col in enumerate(tension_cols):
                    tension_val = row[col]
                    if pd.isna(tension_val) or abs(tension_val) > 1500:
                        alerts.append(f"{device}: Tensiometer level {i+1} out of range (|value| > 1500 kPa).")
            if alerts:
                for alert in alerts:
                    st.error(alert)
                # In a production system you could send an email via SMTP or a
                # notification service.  Here we simply display a note.
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
