import streamlit as st
import pandas as pd
import plotly.express as px
import zipfile
import io

# Set page configuration
st.set_page_config(layout="wide")

# Function to load multiple CSV files from a ZIP into a single DataFrame
def load_data_from_zip(zip_file):
    data_frames = []
    with zipfile.ZipFile(zip_file) as z:
        for filename in z.namelist():
            if filename.endswith('.csv'):
                with z.open(filename) as f:
                    try:
                        st.write(f"Reading file: {filename}")  # Debug statement
                        df = pd.read_csv(f, delimiter=';')
                        # Infer device name from the filename
                        df['device'] = filename.split('_')[0]  # Modify this line as needed
                        data_frames.append(df)
                    except Exception as e:
                        st.error(f"Error reading {filename}: {e}")
    
    if not data_frames:
        st.error("No data frames were created from the ZIP file.")
        return pd.DataFrame()
    
    combined_df = pd.concat(data_frames, ignore_index=True)
    return combined_df

# Upload ZIP file
uploaded_zip = st.file_uploader("Upload a ZIP file containing CSV files", type="zip")

if not uploaded_zip:
    st.stop()

# Load data from ZIP file
data = load_data_from_zip(uploaded_zip)

if data.empty:
    st.stop()

# Convert timestamp to datetime
try:
    data['timestamp'] = pd.to_datetime(data['timestamp'], format='%d.%m.%Y %H:%M:%S')
except Exception as e:
    st.error(f"Error converting timestamp: {e}")
    st.stop()

# Handle missing values
data = data.interpolate().ffill().bfill()

# Get all column names for selection
all_columns = data.columns.tolist()
if 'timestamp' in all_columns: all_columns.remove('timestamp')
if 'device' in all_columns: all_columns.remove('device')

# Get unique devices
devices = data['device'].unique()

# Streamlit layout
st.title('Sensor Data Dashboard')

selected_devices = st.multiselect('Select Devices', devices, default=devices[0])
selected_parameters = st.multiselect('Select Parameters', all_columns, default=all_columns[:1])

start_date, end_date = st.date_input('Select Date Range', [data['timestamp'].min(), data['timestamp'].max()])

filtered_data = data[(data['device'].isin(selected_devices)) & (data['timestamp'] >= pd.to_datetime(start_date)) & (data['timestamp'] <= pd.to_datetime(end_date))]

if selected_parameters and not filtered_data.empty:
    fig = px.line()
    for parameter in selected_parameters:
        for device in selected_devices:
            device_data = filtered_data[filtered_data['device'] == device]
            fig.add_scatter(x=device_data['timestamp'], y=device_data[parameter], mode='lines', name=f'{device} - {parameter}', connectgaps=False)
    fig.update_layout(title='Time Series Comparison', xaxis_title='Timestamp', yaxis_title='Values', width=1200, height=600)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.write("No data available for the selected parameters and date range.")
