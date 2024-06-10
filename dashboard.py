import streamlit as st
import pandas as pd
import plotly.express as px
import zipfile
import requests
import io

# Set page configuration
st.set_page_config(layout="wide")

# Function to convert OneDrive share link to direct download link
def onedrive_direct_download_link(share_link):
    # This link transformation might need adjustments based on the exact sharing method
    base_url = "https://onedrive.live.com/download?resid="
    file_id = share_link.split('/')[-1].split('?')[0]
    return base_url + file_id

# Function to download files from OneDrive public link
def download_file_from_onedrive(onedrive_link):
    download_link = onedrive_direct_download_link(onedrive_link)
    response = requests.get(download_link)
    response.raise_for_status()
    return io.BytesIO(response.content)

# Function to load multiple CSV files into a single DataFrame
def load_data(uploaded_files):
    data_frames = []
    for uploaded_file in uploaded_files:
        try:
            df = pd.read_csv(uploaded_file, delimiter=';')
            df['device'] = uploaded_file.name.split('_')[0]
            data_frames.append(df)
        except Exception as e:
            st.error(f"Error reading {uploaded_file.name}: {e}")
    
    if not data_frames:
        st.error("No data frames were created from the uploaded files.")
        return pd.DataFrame()
    
    combined_df = pd.concat(data_frames, ignore_index=True)
    return combined_df

# Function to load multiple CSV files from a ZIP into separate DataFrames based on the specified dates
def load_data_from_zip(zip_file, specific_dates):
    data_frames_specified = []
    data_frames_other = []
    
    with zipfile.ZipFile(zip_file) as z:
        for filename in z.namelist():
            if filename.endswith('.csv') and not filename.startswith('__MACOSX/'):
                with z.open(filename) as f:
                    try:
                        df = pd.read_csv(f, delimiter=';')
                        df['device'] = filename.split('/')[0].split('_')[0]
                        if any(filename.endswith(date + '.csv') for date in specific_dates):
                            data_frames_specified.append(df)
                        else:
                            data_frames_other.append(df)
                    except Exception as e:
                        st.error(f"Error reading {filename}: {e}")
    
    specified_combined_df = pd.concat(data_frames_specified, ignore_index=True) if data_frames_specified else pd.DataFrame()
    other_combined_df = pd.concat(data_frames_other, ignore_index=True) if data_frames_other else pd.DataFrame()
    return specified_combined_df, other_combined_df

# Upload CSV or ZIP files
st.title('Upload CSV or ZIP files')
uploaded_files = st.file_uploader("Upload CSV files", accept_multiple_files=True, type="csv")
uploaded_zip = st.file_uploader("Upload a ZIP file containing CSV files", type="zip")

data_specified = pd.DataFrame()
data_other = pd.DataFrame()

# Specific dates to filter
specific_dates = ['20240605', '20240606']

# Load data from uploaded files
if uploaded_files:
    data_specified = load_data(uploaded_files)
elif uploaded_zip:
    data_specified, data_other = load_data_from_zip(uploaded_zip, specific_dates)

# Option to fetch files from OneDrive
st.title('Fetch Files from OneDrive')
onedrive_link = st.text_input('Enter OneDrive public link:', 'https://1drv.ms/f/s!Anuwhpfjswn1akYZhJrSGmcvz4g?e=IbGrDq')
if st.button('Fetch Files from OneDrive'):
    try:
        file_content = download_file_from_onedrive(onedrive_link)
        with zipfile.ZipFile(file_content) as z:
            for filename in z.namelist():
                if filename.endswith('.csv') and not filename.startswith('__MACOSX/'):
                    with z.open(filename) as f:
                        try:
                            df = pd.read_csv(f, delimiter=';')
                            df['device'] = filename.split('/')[0].split('_')[0]
                            if any(filename.endswith(date + '.csv') for date in specific_dates):
                                data_specified = pd.concat([data_specified, df], ignore_index=True)
                            else:
                                data_other = pd.concat([data_other, df], ignore_index=True)
                        except Exception as e:
                            st.error(f"Error reading {filename}: {e}")
    except requests.exceptions.HTTPError as e:
        st.error(f"Error downloading file from OneDrive: {e}")

# Convert timestamp to datetime
for data in [data_specified, data_other]:
    if not data.empty:
        try:
            data['timestamp'] = pd.to_datetime(data['timestamp'], format='%d.%m.%Y %H:%M:%S')
        except Exception as e:
            st.error(f"Error converting timestamp: {e}")
            st.stop()

# Handle missing values
data_specified = data_specified.interpolate().ffill().bfill() if not data_specified.empty else data_specified
data_other = data_other.interpolate().ffill().bfill() if not data_other.empty else data_other

# Get all column names for selection
all_columns_specified = data_specified.columns.tolist() if not data_specified.empty else []
all_columns_other = data_other.columns.tolist() if not data_other.empty else []

for all_columns in [all_columns_specified, all_columns_other]:
    if 'timestamp' in all_columns: all_columns.remove('timestamp')
    if 'device' in all_columns: all_columns.remove('device')

# Get unique devices
devices_specified = data_specified['device'].unique() if not data_specified.empty else []
devices_other = data_other['device'].unique() if not data_other.empty else []

# Streamlit layout for specified dates data
st.title('Sensor Data Dashboard for Specified Dates (20240605, 20240606)')

if not data_specified.empty:
    selected_devices_specified = st.multiselect('Select Devices (Specified Dates)', devices_specified, default=devices_specified[0] if devices_specified else None)
    selected_parameters_specified = st.multiselect('Select Parameters (Specified Dates)', all_columns_specified, default=all_columns_specified[:1] if all_columns_specified else None)
    start_date_specified, end_date_specified = st.date_input('Select Date Range (Specified Dates)', [data_specified['timestamp'].min(), data_specified['timestamp'].max()])

    filtered_data_specified = data_specified[(data_specified['device'].isin(selected_devices_specified)) & (data_specified['timestamp'] >= pd.to_datetime(start_date_specified)) & (data_specified['timestamp'] <= pd.to_datetime(end_date_specified))]

    if selected_parameters_specified and not filtered_data_specified.empty:
        fig_specified = px.line()
        for parameter in selected_parameters_specified:
            for device in selected_devices_specified:
                device_data = filtered_data_specified[filtered_data_specified['device'] == device]
                fig_specified.add_scatter(x=device_data['timestamp'], y=device_data[parameter], mode='lines', name=f'{device} - {parameter}', connectgaps=False)
        fig_specified.update_layout(title='Time Series Comparison (Specified Dates)', xaxis_title='Timestamp', yaxis_title='Values', width=1200, height=600)
        st.plotly_chart(fig_specified, use_container_width=True)
        
        st.subheader('Raw Data (Specified Dates)')
        st.dataframe(filtered_data_specified)
    else:
        st.write("No data available for the selected parameters and date range (Specified Dates).")
else:
    st.write("No data available for the specified dates (20240605, 20240606).")

# Streamlit layout for other dates data
st.title('Sensor Data Dashboard for Other Dates')

if not data_other.empty:
    selected_devices_other = st.multiselect('Select Devices (Other Dates)', devices_other, default=devices_other[0] if devices_other else None)
    selected_parameters_other = st.multiselect('Select Parameters (Other Dates)', all_columns_other, default=all_columns_other[:1] if all_columns_other else None)
    start_date_other, end_date_other = st.date_input('Select Date Range (Other Dates)', [data_other['timestamp'].min(), data_other['timestamp'].max()])

    filtered_data_other = data_other[(data_other['device'].isin(selected_devices_other)) & (data_other['timestamp'] >= pd.to_datetime(start_date_other)) & (data_other['timestamp'] <= pd.to_datetime(end_date_other))]

    if selected_parameters_other and not filtered_data_other.empty:
        fig_other = px.line()
        for parameter in selected_parameters_other:
            for device in selected_devices_other:
                device_data = filtered_data_other[filtered_data_other['device'] == device]
                fig_other.add_scatter(x=device_data['timestamp'], y=device_data[parameter], mode='lines', name=f'{device} - {parameter}', connectgaps=False)
        fig_other.update_layout(title='Time Series Comparison (Other Dates)', xaxis_title='Timestamp', yaxis_title='Values', width=1200, height=600)
        st.plotly_chart(fig_other, use
