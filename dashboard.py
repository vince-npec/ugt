import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io
from bs4 import BeautifulSoup

# Function to extract file links from OneDrive folder
def fetch_file_links_from_onedrive(folder_link):
    response = requests.get(folder_link)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    file_links = []
    for a_tag in soup.find_all('a'):
        href = a_tag.get('href')
        if href and 'download' in href:
            file_links.append(href)
    
    return file_links

# Function to download a file from a given URL
def download_file(file_url):
    response = requests.get(file_url)
    response.raise_for_status()
    return io.BytesIO(response.content)

# Function to load multiple CSV files into a single DataFrame
def load_data(file_urls, specific_dates):
    data_frames_specified = []
    data_frames_other = []
    
    for file_url in file_urls:
        file_content = download_file(file_url)
        try:
            df = pd.read_csv(file_content, delimiter=';')
            df['device'] = file_url.split('/')[-1].split('_')[0]
            if any(file_url.endswith(date + '.csv') for date in specific_dates):
                data_frames_specified.append(df)
            else:
                data_frames_other.append(df)
        except Exception as e:
            st.error(f"Error reading {file_url}: {e}")
    
    specified_combined_df = pd.concat(data_frames_specified, ignore_index=True) if data_frames_specified else pd.DataFrame()
    other_combined_df = pd.concat(data_frames_other, ignore_index=True) if data_frames_other else pd.DataFrame()
    return specified_combined_df, other_combined_df

# Set page configuration
st.set_page_config(layout="wide")

# Specific dates to filter
specific_dates = ['20240605', '20240606']

# Initialize data frames
data_specified = pd.DataFrame()
data_other = pd.DataFrame()

# Option to fetch files from OneDrive folder
st.title('Fetch Files from OneDrive Folder')
folder_link = st.text_input('Enter OneDrive folder link:', 'https://1drv.ms/f/s!Anuwhpfjswn1akYZhJrSGmcvz4g?e=TT0WrP')
if st.button('Fetch Files from OneDrive Folder'):
    try:
        file_urls = fetch_file_links_from_onedrive(folder_link)
        data_specified, data_other = load_data(file_urls, specific_dates)
    except Exception as e:
        st.error(f"Error fetching files: {e}")

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
        st.plotly_chart(fig_other, use_container_width=True)
        
        st.subheader('Raw Data (Other Dates)')
        st.dataframe(filtered_data_other)
    else:
        st.write("No data available for the selected parameters and date range (Other Dates).")
else:
    st.write("No data available for the other dates.")
