import streamlit as st
import pandas as pd
import plotly.express as px
import zipfile
import re
import hashlib
from typing import List, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Visualization Dashboard | NPEC Ecotrons", layout="wide")

# ─────────────────────────────────────────────────────────────────────────────
# UTILS
# ─────────────────────────────────────────────────────────────────────────────
def normalize(name: str) -> str:
    """Lowercase and strip spaces, hyphens, underscores for consistent matching."""
    return re.sub(r"[\s\-_]+", "", name.lower())

def ip_from(url: str) -> str:
    try:
        return url.split("//", 1)[1].split("/", 1)[0]
    except Exception:
        return url

def check_password(pw: str) -> bool:
    """
    Password check for locking the left menu.
    Priority:
      1) st.secrets['SIDEBAR_PASSWORD_HASH']  (sha256 hex)
      2) st.secrets['SIDEBAR_PASSWORD']       (plain text)
      3) fallback 'npec' (for local/dev)
    """
    hash_secret = st.secrets.get("SIDEBAR_PASSWORD_HASH", "").strip()
    if hash_secret:
        return hashlib.sha256(pw.encode()).hexdigest() == hash_secret
    plain_secret = st.secrets.get("SIDEBAR_PASSWORD", "").strip()
    if plain_secret:
        return pw == plain_secret
    # fallback for convenience
    return pw == "npec"

# ─────────────────────────────────────────────────────────────────────────────
# DEVICE DIRECTORY (SIDEBAR)
# ─────────────────────────────────────────────────────────────────────────────
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
    "Ulysses":"🦋","Admiral":"🦋","Scarab":"🪲","Ladybug":"🐞","Stag beetle":"🪲",
    "Mosquito":"🦟","Flea":"🪳","Yellowjacket":"🐝","Dragonfly":"🐉","Moth":"🦋",
    "Cockroach":"🪳","Fly":"🪰","Mantis":"🦗","Tick":"🕷️","Termite":"🐜","Giraffe":"🦒",
    "Millipede":"🪱","Fire bug":"🔥","Centipede":"🪱","Tarantula":"🕷️","Dung beetle":"🪲",
    "Ant":"🐜","Hornet":"🐝","Maybug":"🪲","Bumblebee":"🐝","Honeybee":"🐝","Stink":"💨",
    "Hercules":"💪","Strider":"🚶","Stick":"🪵","Longhorn":"🐂","Weaver":"🧵","Scorpion":"🦂",
    "Caterpillar":"🐛","Potato beetle":"🥔🪲","Cricket":"🦗",
}

# Room/type mapping (from your table)
META = {
    "ulysses":("Ecolab 1","Advanced"), "admiral":("Ecolab 1","Advanced"), "scarab":("Ecolab 1","Advanced"),
    "ladybug":("Ecolab 1","Advanced"), "yellowjacket":("Ecolab 1","Advanced"), "flea":("Ecolab 1","Advanced"),
    "mosquito":("Ecolab 1","Advanced"), "stagbeetle":("Ecolab 1","Advanced"),
    "dragonfly":("Ecolab 2","Basic"), "moth":("Ecolab 2","Basic"), "cockroach":("Ecolab 2","Basic"),
    "fly":("Ecolab 2","Basic"), "mantis":("Ecolab 2","Basic"), "tick":("Ecolab 2","Basic"),
    "termite":("Ecolab 2","Basic"), "giraffe":("Ecolab 2","Basic"), "millipede":("Ecolab 2","Basic"),
    "firebug":("Ecolab 2","Basic"), "centipede":("Ecolab 2","Basic"), "tarantula":("Ecolab 2","Basic"),
    "dungbeetle":("Ecolab 3","Basic"), "ant":("Ecolab 3","Basic"), "hornet":("Ecolab 3","Basic"),
    "maybug":("Ecolab 3","Basic"), "bumblebee":("Ecolab 3","Basic"), "honeybee":("Ecolab 3","Basic"),
    "stink":("Ecolab 3","Basic"), "hercules":("Ecolab 3","Basic"), "strider":("Ecolab 3","Basic"),
    "stick":("Ecolab 3","Basic"), "longhorn":("Ecolab 3","Basic"),
    "weaver":("Ecolab 3","Basic"), "scorpion":("Ecolab 3","Basic"),
    "caterpillar":("Ecolab 3","Basic"), "potatobeetle":("Ecolab 3","Basic"), "cricket":("Ecolab 3","Basic"),
}
def meta_for(name: str):
    return META.get(normalize(name), ("Ecolab 3", "Basic"))

# ── RhizoCam units
RHIZOCAMS = [
    {"host": "Cricket", "gantry": "http://192.168.162.186:8501/", "analysis": "http://192.168.162.186:8502/"},
    # add more as needed…
]

# ── IP Cameras (from your list)
_IPC = {
    "Admiral":"192.168.162.45", "Ant":"192.168.162.65", "Bumblebee":"192.168.162.68",
    "Caterpillar":"192.168.162.77", "Centipede":"192.168.162.62", "Cockroach":"192.168.162.54",
    "Cricket":"192.168.162.79", "Dragonfly":"192.168.162.52", "Dung-Beetle":"192.168.162.64",
    "Firebug":"192.168.162.61", "Flea":"192.168.162.50", "Fly":"192.168.162.55",
    "Giraffe":"192.168.162.161", "Hercules":"192.168.162.71", "Honeybee":"192.168.162.69",
    "Hornet":"192.168.162.66", "Ladybug":"192.168.162.47", "Longhorn":"192.168.162.74",
    "Mantis":"192.168.162.56", "Maybug":"192.168.162.67", "Millipedes":"192.168.162.60",
    "Mosquito":"192.168.162.49", "Moth":"192.168.162.53", "Potato-Beetle":"192.168.162.78",
    "Scarab":"192.168.162.46", "Scorpio":"192.168.162.76", "Stag-beetle":"192.168.162.48",
    "Stick":"192.168.162.130", "Stink":"192.168.162.70", "Strider":"192.168.162.72",
    "Tarantula":"192.168.162.63", "Termite":"192.168.162.58", "Tick":"192.168.162.57",
    "Ulysses":"192.168.162.44", "Weaver":"192.168.162.75", "YellowJacket":"192.168.162.140",
}
# Map camera name -> canonical device name for room grouping
_CAM_CANON = {
    "dungbeetle": "Dung beetle",
    "potatobeetle": "Potato beetle",
    "yellowjacket": "Yellowjacket",
    "stagbeetle": "Stag beetle",
    "millipedes": "Millipede",
    "firebug": "Fire bug",
    "scorpio": "Scorpion",
}
def camera_room(name: str) -> str:
    canon = _CAM_CANON.get(normalize(name), name)
    return meta_for(canon)[0]

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR (LOCKABLE)  — all sections default collapsed
# ─────────────────────────────────────────────────────────────────────────────
if "menu_unlocked" not in st.session_state:
    st.session_state.menu_unlocked = False

with st.sidebar:
    st.title("Devices")

    if not st.session_state.menu_unlocked:
        st.info("🔒 Left menu is locked. Enter password to unlock.")
        pw = st.text_input("Password", type="password", key="__sb_pw")
        col_a, col_b = st.columns([1,1])
        with col_a:
            if st.button("Unlock"):
                if check_password(pw or ""):
                    st.session_state.menu_unlocked = True
                    st.success("Menu unlocked.")
                else:
                    st.error("Wrong password.")
        with col_b:
            st.caption("Default: **npec** (set secrets for production).")

    else:
        top_row = st.columns([2,1,1])
        with top_row[0]:
            q = st.text_input("Filter by name or IP", value="", key="__filter_q")
        with top_row[1]:
            room_filter = st.selectbox("Room", ["All","Ecolab 1","Ecolab 2","Ecolab 3"], key="__room_sel")
        with top_row[2]:
            if st.button("Lock menu", use_container_width=True):
                st.session_state.menu_unlocked = False
                st.stop()

        rooms_order = ["Ecolab 1","Ecolab 2","Ecolab 3"] if room_filter=="All" else [room_filter]

        # Devices
        for room_name in rooms_order:
            with st.expander(room_name, expanded=False):
                for name, url in DEVICES:
                    room, typ = meta_for(name)
                    if room != room_name:  # filtered by room section
                        continue
                    if q and (q.lower() not in name.lower() and q.lower() not in ip_from(url)):
                        continue
                    emoji = EMOJI.get(name, "🔗")
                    st.markdown(
                        f"**{emoji} {name}**  \n"
                        f"`{ip_from(url)}` • *{typ}*  \n"
                        f"[Open ↗]({url})"
                    )

        st.markdown("---")

        # RhizoCam units (grouped by host room)
        st.subheader("RhizoCam units")
        for room_name in rooms_order:
            room_rhizo = [rc for rc in RHIZOCAMS if meta_for(rc["host"])[0] == room_name]
            if not room_rhizo:
                continue
            with st.expander(room_name, expanded=False):
                for rc in room_rhizo:
                    host = rc["host"]
                    gantry_ip = ip_from(rc["gantry"])
                    analysis_ip = ip_from(rc["analysis"])
                    if q and (q.lower() not in host.lower() and q.lower() not in gantry_ip and q.lower() not in analysis_ip):
                        continue
                    st.markdown(
                        f"**📷 RhizoCam @ {host}**  \n"
                        f"`Gantry: {gantry_ip}`  \n"
                        f"`Analysis: {analysis_ip}`  \n"
                        f"[Gantry ↗]({rc['gantry']}) &nbsp;|&nbsp; [Analysis ↗]({rc['analysis']})"
                    )

        st.markdown("---")

        # IP cameras
        st.subheader("IP cameras")
        # build per-room groups
        cams_by_room = {"Ecolab 1": [], "Ecolab 2": [], "Ecolab 3": []}
        for cam_name, cam_ip in _IPC.items():
            r = camera_room(cam_name)
            if r in cams_by_room:
                cams_by_room[r].append((cam_name, cam_ip))

        for room_name in rooms_order:
            items = cams_by_room.get(room_name, [])
            if not items:
                continue
            with st.expander(room_name, expanded=False):
                for cam_name, cam_ip in sorted(items, key=lambda t: t[0].lower()):
                    if q and (q.lower() not in cam_name.lower() and q not in cam_ip):
                        continue
                    st.markdown(
                        f"**🎥 {cam_name}**  \n"
                        f"`{cam_ip}`  \n"
                        f"[Open ↗](http://{cam_ip}/)"
                    )

        st.caption("Tip: collapse the sidebar with the chevron (>) to give charts more room.")

# ─────────────────────────────────────────────────────────────────────────────
# HEADER WITH LOGOS + TITLE (approx. 5 cm height, no cropping)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
        <img src="https://raw.githubusercontent.com/vince-npec/ugt/main/Module-1-icon.png"
             alt="Ecotron Module"
             style="height: 189px; width: auto;" />
        <h1 style="text-align: center; color: white; flex-grow: 1; margin: 0; font-size: 2.6rem; font-weight: 400;">
            Visualization Dashboard | <b style="font-weight:700;">NPEC Ecotrons</b>
        </h1>
        <img src="https://raw.githubusercontent.com/vince-npec/ugt/main/NPEC-dashboard-logo.png"
             alt="NPEC"
             style="height: 189px; width: auto;" />
    </div>
""", unsafe_allow_html=True)
st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# ROBUST UPLOAD SECTION (fragment + stable widget keys)
# ─────────────────────────────────────────────────────────────────────────────
MAX_ROWS = 50000
room_assignments = {
    "Ulysses": "Room 1", "Admiral": "Room 1", "Scarab": "Room 1",
    "Ladybug": "Room 1", "Yellowjacket": "Room 1", "Flea": "Room 1",
    "Mosquito": "Room 1", "Stag beetle": "Room 1", "Stag_Bettle": "Room 1",
    "Cockroach": "Room 2", "Termite": "Room 2", "Centipede": "Room 2",
    "Fly": "Room 2", "Giraffe": "Room 2", "Tarantula": "Room 2",
    "Fire bug": "Room 2", "Fire_Bug": "Room 2", "Tick": "Room 2",
    "Moth": "Room 2", "Millipede": "Room 2", "Mantis": "Room 2", "Dragonfly": "Room 2"
}

def load_data(uploaded_files, max_rows=MAX_ROWS):
    data_frames, total_rows = [], 0
    for uploaded_file in uploaded_files:
        try:
            df = pd.read_csv(uploaded_file, delimiter=';')
            device_name = uploaded_file.name.split('_')[0]
            if device_name == "Fire": device_name = "Fire bug"
            elif device_name == "Stag": device_name = "Stag beetle"
            df['device'] = device_name
            df['room'] = room_assignments.get(device_name, "Unknown")
            if not df.empty:
                if total_rows + len(df) > max_rows:
                    df = df.iloc[:max_rows - total_rows]
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

def load_data_from_zip(zip_file, max_rows=MAX_ROWS):
    data_frames, total_rows = [], 0
    with zipfile.ZipFile(zip_file) as z:
        for filename in z.namelist():
            if filename.endswith('.csv') and not filename.startswith('__MACOSX/'):
                with z.open(filename) as f:
                    try:
                        df = pd.read_csv(f, delimiter=';')
                        device_name = filename.split('/')[0].split('_')[0]
                        if device_name == "Fire": device_name = "Fire bug"
                        elif device_name == "Stag": device_name = "Stag beetle"
                        df['device'] = device_name
                        df['room'] = room_assignments.get(device_name, "Unknown")
                        if not df.empty:
                            if total_rows + len(df) > max_rows:
                                df = df.iloc[:max_rows - total_rows]
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

@st.fragment  # isolates the chunk so sidebar interactions don't re-mount uploader JS
def data_loader_fragment():
    st.title('Upload CSV or ZIP files')
    uploaded_files = st.file_uploader("Upload CSV files", accept_multiple_files=True, type="csv", key="csv_uploader_key")
    uploaded_zip   = st.file_uploader("Upload a ZIP file containing CSV files", type="zip", key="zip_uploader_key")

    if uploaded_zip and hasattr(uploaded_zip, "size") and uploaded_zip.size > 50_000_000:
        st.warning("Uploaded ZIP is quite large; this may take a while or could crash the dashboard.")

    # Load logic happens here; results stored into session_state
    if uploaded_files:
        st.session_state.data_df = load_data(uploaded_files)
    elif uploaded_zip:
        st.session_state.data_df = load_data_from_zip(uploaded_zip)
    else:
        st.session_state.data_df = pd.DataFrame()

data_loader_fragment()

data = st.session_state.get("data_df", pd.DataFrame())
if data.empty:
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# TIMESTAMPS & RESAMPLING
# ─────────────────────────────────────────────────────────────────────────────
try:
    data['timestamp'] = pd.to_datetime(data['timestamp'], format='%d.%m.%Y %H:%M:%S')
except Exception as e:
    st.error(f"Error converting timestamp: {e}")
    st.stop()

sampling_options = {"Raw (10 min)": "10T", "30 min": "30T", "Hourly": "1H", "Daily": "1D"}
selected_freq_label = st.selectbox("Select Data Frequency (downsampling)", list(sampling_options.keys()), index=0)
selected_freq = sampling_options[selected_freq_label]

def resample_data(df, freq):
    if freq == "10T":
        return df
    numeric_cols = df.select_dtypes(include='number').columns
    if 'timestamp' not in df.columns:
        return df
    frames = []
    for (device, room), group in df.groupby(['device', 'room']):
        group = group.set_index('timestamp').sort_index()
        resampled = group[numeric_cols].resample(freq).mean()
        resampled['device'] = device
        resampled['room'] = room
        frames.append(resampled.reset_index())
    return pd.concat(frames, ignore_index=True) if frames else df

data = resample_data(data, selected_freq)

numeric_cols = data.select_dtypes(include='number').columns
data[numeric_cols] = data[numeric_cols].interpolate().ffill().bfill()

columns = ['device', 'room'] + [c for c in data.columns if c not in ['device', 'room']]
data = data[columns]

def looks_like_data_point(col):
    try:
        float(str(col)); return True
    except Exception:
        pass
    if re.match(r'^\d{2}\.\d{2}\.\d{4}', str(col)): return True
    if len(str(col)) < 3: return True
    return False

all_columns = [c for c in data.columns if c not in ['timestamp','device','room'] and not looks_like_data_point(c)]

standard_parameters = [
    'Atmosphere temperature (°C)', 'Atmosphere humidity (% RH)',
    'FRT tension 1 (kPa)', 'FRT tension 2 (kPa)', 'FRT tension 3 (kPa)',
    'SMT temperature 1 (°C)', 'SMT temperature 2 (°C)', 'SMT temperature 3 (°C)',
    'SMT water content 1 (%)', 'SMT water content 2 (%)', 'SMT water content 3 (%)'
]
dcc_parameters = [
    'SMT water content 1 (%)', 'SMT water content 2 (%)', 'SMT water content 3 (%)',
    'Current Days Irrigation (L)', 'Lysimeter weight (Kg)', 'LBC tank weight (Kg)'
]

devices_list = data['device'].unique()
device_options = ['All'] + devices_list.tolist()
rooms_list = data['room'].unique()
room_options = ['All'] + rooms_list.tolist()

st.title('Sensor Data Dashboard')

selected_rooms = st.multiselect('Select Rooms', room_options, default='All')
if 'All' in selected_rooms:
    selected_rooms = rooms_list.tolist()

selected_devices = st.multiselect('Select Devices', device_options, default='All')
if 'All' in selected_devices:
    selected_devices = devices_list.tolist()

parameter_options = ['Standard Parameters', 'DCC project'] + all_columns if all_columns else ['Standard Parameters', 'DCC project']
selected_parameters = st.multiselect('Select Parameters', parameter_options)

final_parameters, seen = [], set()
if 'Standard Parameters' in selected_parameters:
    final_parameters += [p for p in standard_parameters if p in all_columns]
if 'DCC project' in selected_parameters:
    final_parameters += [p for p in dcc_parameters if p in all_columns]
final_parameters += [p for p in selected_parameters if p not in ['Standard Parameters', 'DCC project']]
final_parameters = [x for x in final_parameters if not (x in seen or seen.add(x))]

try:
    start_date, end_date = st.date_input('Select Date Range', [data['timestamp'].min(), data['timestamp'].max()])
    if start_date > end_date:
        st.error("Error: End date must be after start date.")
        st.stop()
except Exception as e:
    st.error(f"Error with date input: {e}")
    st.stop()

filtered_data = data[
    (data['room'].isin(selected_rooms)) &
    (data['device'].isin(selected_devices)) &
    (data['timestamp'] >= pd.to_datetime(start_date)) &
    (data['timestamp'] <= pd.to_datetime(end_date))
]

if final_parameters and not filtered_data.empty:
    for parameter in final_parameters:
        fig = px.line()
        for device in selected_devices:
            ddf = filtered_data[filtered_data['device'] == device]
            if parameter in ddf.columns:
                fig.add_scatter(x=ddf['timestamp'], y=ddf[parameter],
                                mode='lines', name=f'{device} - {parameter}', connectgaps=False)
        fig.update_layout(title=f'Time Series Comparison for {parameter}',
                          xaxis_title='Timestamp', yaxis_title=parameter, height=600)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader('Raw Data')
    st.dataframe(filtered_data.head(100))
    if len(filtered_data) > 100:
        st.info(f"Showing first 100 of {len(filtered_data)} rows out of {len(filtered_data)} total.")
else:
    st.write("No data available for the selected parameters and date range.")

st.markdown("<hr style='margin-top:50px; margin-bottom:10px;'>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align: center; color: grey; font-size: 14px;'>"
    "© 2025 NPEC Ecotron Module - Visualization Dashboard by Dr. Vinicius Lube | "
    "Phenomics Engineer Innovation Lead</p>",
    unsafe_allow_html=True
)
