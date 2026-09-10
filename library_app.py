import streamlit as st
import pandas as pd
import re
import os
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import json

# --- Color Maps ---
NORMAL_COLORS = {
    'Current Needed': '#E69F00',            # Orange
    'Current Surplus': '#56B4E9',           # Sky Blue
    'Projected Needed': '#D55E00',          # Dark Orange/Red
    'Projected Surplus': '#0072B2',         # Dark Blue
    'Initial Hist': '#999999',              # Gray
    'Current Post-Shift Hist': '#CC79A7',   # Reddish Purple
    'Projected Post-Shift Hist': '#F0E442', # Yellow,
}

# Helper for custom notification color
def custom_warning(message):
    st.markdown(
        f"""
        <div style="background-color: #E69F00; color: white; padding: 12px; border-radius: 5px; margin-bottom: 10px; font-weight: bold;">
            {message}
        </div>
        """, 
        unsafe_allow_html=True
    )

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Library Space Management Tool",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Library Space Management Tool")
st.caption("Created by: Dana Makinen")
st.markdown("""
This application helps libraries analyze current and projected shelf space utilization,
and generates shift recommendations.
""")

# --- 1. Configuration Section ---

st.header("1. Configuration")

unit_system = st.radio(
    "Select System of Measurement:",
    ("Imperial (Inches)", "Metric (Centimeters)"),
    index=0,
    horizontal=True,
    help="This changes labels and default values throughout the application."
)

if unit_system == "Imperial (Inches)":
    u_label = "inches"
    u_short = "in"
else:
    u_label = "centimeters"
    u_short = "cm"

uploaded_file = st.file_uploader(
    f"Upload your 'Range Summary' CSV file (Values should be in {u_label})",
    type=["csv"]
)

default_collection_target_map_json = """
{
    "Collection 1": 0.25,
    "Collection 2": 0.30,
    "Collection 3": 0.40,
    "Collection 4": 0.50,
    "Collection 5": 0.60
}
"""

default_collection_growth_rates_json = """
{
    "Collection 1": 0.0,
    "Collection 2": 0.0,
    "Collection 3": 0.0,
    "Collection 4": 0.0,
    "Collection 5": 0.0
}
"""

col1, col2 = st.columns(2)

with col1:
    st.subheader("Collection Target Empty Percentages")
    collection_target_map_input = st.text_area(
        "Edit target % empty for each collection (JSON format):",
        value=default_collection_target_map_json,
        height=200
    )
    collection_target_map = {}
    try:
        collection_target_map = json.loads(collection_target_map_input)
    except json.JSONDecodeError:
        st.error("Invalid JSON format for Collection Target Percentages. Please correct it.")

with col2:
    st.subheader(f"Collection Annual Growth Rates ({u_short})")
    collection_growth_rates_input = st.text_area(
        f"Edit annual growth rates ({u_short}) per range within each collection (JSON format):",
        value=default_collection_growth_rates_json,
        height=200
    )
    collection_growth_rates = {}
    try:
        collection_growth_rates = json.loads(collection_growth_rates_input)
    except json.JSONDecodeError:
        st.error("Invalid JSON format for Collection Growth Rates. Please correct it.")

projection_years = st.number_input(
    "Number of years to project into the future:",
    min_value=0,
    max_value=20,
    value=5,
    step=1
)

# Strategy is hardcoded to min_moves
selected_strategy = 'min_moves'

if 'localized_start_id' not in st.session_state:
    st.session_state.localized_start_id = None
if 'localized_end_id' not in st.session_state:
    st.session_state.localized_end_id = None
if 'localized_analysis_active' not in st.session_state:
    st.session_state.localized_analysis_active = False
if 'report_view_active' not in st.session_state:
    st.session_state.report_view_active = False


# --- Core Functions ---

@st.cache_data
def parse_range_id(range_id):
    match = re.match(r'(\d+)([ab])', str(range_id))
    if match:
        num = int(match.group(1))
        side = match.group(2)
        side_val = 0.0 if side == 'a' else 0.5
        return num, side_val
    return None, None

@st.cache_data
def load_and_process_data(uploaded_file_buffer, collection_target_map_val):
    df_range_summary = pd.read_csv(uploaded_file_buffer, header=0)
    df_range_summary = df_range_summary.drop(columns=['Unnamed: 13', 'Unnamed: 14', 'Unnamed: 15'], errors='ignore')

    for col in df_range_summary.columns:
        if any(keyword in col for keyword in ['Capacity', 'Inches', 'Available', 'Occupied', 'Percent', 'Target']):
             df_range_summary[col] = df_range_summary[col].astype(str).str.replace(',', '', regex=False)
             df_range_summary[col] = pd.to_numeric(df_range_summary[col], errors='coerce')

    df_range_summary['Percent Empty per Side'] = df_range_summary['Available Inches'] / df_range_summary['Total Capacity']
    df_range_summary['Percent Full per Side'] = 1 - df_range_summary['Percent Empty per Side']
    df_range_summary['Target % Empty (Calculated)'] = df_range_summary['Collection Type'].map(collection_target_map_val)
    df_range_summary['Current Available Inches (Calculated)'] = df_range_summary.apply(
        lambda row: row['Total Capacity'] * row['Percent Empty per Side'] if row['Total Capacity'] > 0 else 0,
        axis=1
    )
    df_range_summary['Target Available Inches'] = df_range_summary['Total Capacity'] * df_range_summary['Target % Empty (Calculated)']
    df_range_summary['Inches Needed/Surplus (Calculated)'] = df_range_summary['Target Available Inches'] - df_range_summary['Current Available Inches (Calculated)']

    df_range_summary[['Range_Num', 'Range_Side_Val']] = df_range_summary['Range'].apply(
        lambda x: pd.Series(parse_range_id(x))
    )
    df_range_summary['Range_Position'] = df_range_summary['Range_Num'] + df_range_summary['Range_Side_Val']

    return df_range_summary

@st.cache_data
def allocate_shifts(df_data_state, strategy='min_moves'):
    df_alloc_needy = df_data_state[df_data_state['Inches Needed/Surplus (Calculated)'] > 0].copy()
    df_alloc_surplus = df_data_state[df_data_state['Inches Needed/Surplus (Calculated)'] < 0].copy()
    df_alloc_surplus['Surplus Inches'] = abs(df_alloc_surplus['Inches Needed/Surplus (Calculated)'])

    df_alloc_needy = df_alloc_needy.sort_values(by='Inches Needed/Surplus (Calculated)', ascending=False).reset_index(drop=True)

    shift_guide = []
    processed_needy_ranges = set()

    for needy_index, current_needy in df_alloc_needy.iterrows():
        if current_needy['Range'] in processed_needy_ranges:
            continue

        space_needed = current_needy['Inches Needed/Surplus (Calculated)']
        if space_needed <= 0:
            processed_needy_ranges.add(current_needy['Range'])
            continue

        available_surpluses = df_alloc_surplus[df_alloc_surplus['Surplus Inches'] > 0].copy()
        if available_surpluses.empty:
            break

        # Min Moves Strategy Logic
        available_surpluses['Distance'] = abs(available_surpluses['Range_Position'] - current_needy['Range_Position'])
        available_surpluses = available_surpluses.sort_values(by=['Surplus Inches', 'Distance'], ascending=[False, True]).reset_index(drop=True)

        for i in range(len(available_surpluses)):
            if space_needed <= 0:
                break

            potential_supplier = available_surpluses.loc[i]
            space_available = potential_supplier['Surplus Inches']
            transfer_amount = min(space_needed, space_available)

            if transfer_amount > 0:
                shift_guide.append({
                    'Action': 'Shift From',
                    'Source Range Side ID': potential_supplier['Range'],
                    'Inches to Move': transfer_amount,
                    'Destination Range Side ID': current_needy['Range'],
                })

                needy_original_idx = df_alloc_needy[df_alloc_needy['Range'] == current_needy['Range']].index[0]
                surplus_original_idx = df_alloc_surplus[df_alloc_surplus['Range'] == potential_supplier['Range']].index[0]

                df_alloc_needy.loc[needy_original_idx, 'Inches Needed/Surplus (Calculated)'] -= transfer_amount
                df_alloc_surplus.loc[surplus_original_idx, 'Surplus Inches'] -= transfer_amount
                space_needed -= transfer_amount

                if space_needed <= 0:
                    processed_needy_ranges.add(current_needy['Range'])

    final_needy = df_alloc_needy[df_alloc_needy['Inches Needed/Surplus (Calculated)'] > 0].copy()
    final_surplus = df_alloc_surplus[df_alloc_surplus['Surplus Inches'] > 0].copy()

    return pd.DataFrame(shift_guide), final_needy, final_surplus

@st.cache_data
def get_post_shift_df(df_initial, df_shifts):
    df_post_shift = df_initial.copy()
    if not df_shifts.empty:
        for index, row in df_shifts.iterrows():
            source_range = row['Source Range Side ID']
            safety_check_source = df_post_shift['Range'] == source_range
            if safety_check_source.any():
                df_post_shift.loc[safety_check_source, 'Current Available Inches (Calculated)'] -= row['Inches to Move']

            dest_range = row['Destination Range Side ID']
            safety_check_dest = df_post_shift['Range'] == dest_range
            if safety_check_dest.any():
                df_post_shift.loc[safety_check_dest, 'Current Available Inches (Calculated)'] += row['Inches to Move']

    df_post_shift['Percent Empty per Side'] = df_post_shift['Current Available Inches (Calculated)'] / df_post_shift['Total Capacity']
    df_post_shift['Percent Full per Side'] = 1 - df_post_shift['Percent Empty per Side']
    df_post_shift['Inches Needed/Surplus (Calculated)'] = df_post_shift['Target Available Inches'] - df_post_shift['Current Available Inches (Calculated)']
    return df_post_shift

@st.cache_data
def get_shift_impact_summary(df_initial_state, df_shift_guide):
    df_summary = df_initial_state[['Range', 'Collection Type', 'Current Available Inches (Calculated)', 'Inches Needed/Surplus (Calculated)', 'Target Available Inches', 'Target % Empty (Calculated)']].copy()
    df_summary.rename(columns={'Current Available Inches (Calculated)': 'Initial Available Space', 'Inches Needed/Surplus (Calculated)': 'Initial Needed/Surplus'}, inplace=True)

    df_summary[['Range_Num', 'Range_Side_Val']] = df_summary['Range'].apply(lambda x: pd.Series(parse_range_id(x)))
    df_summary['Range_Position'] = df_summary['Range_Num'] + df_summary['Range_Side_Val']
    df_summary = df_summary.dropna(subset=['Range_Position']).copy()

    if not df_shift_guide.empty:
        df_moved_out = df_shift_guide.groupby('Source Range Side ID')['Inches to Move'].sum().reset_index()
        df_moved_out.rename(columns={'Source Range Side ID': 'Range', 'Inches to Move': 'Space Moved Out'}, inplace=True)
        df_summary = pd.merge(df_summary, df_moved_out, on='Range', how='left')

        df_moved_in = df_shift_guide.groupby('Destination Range Side ID')['Inches to Move'].sum().reset_index()
        df_moved_in.rename(columns={'Destination Range Side ID': 'Range', 'Inches to Move': 'Space Moved In'}, inplace=True)
        df_summary = pd.merge(df_summary, df_moved_in, on='Range', how='left')
    else:
        df_summary['Space Moved Out'] = 0
        df_summary['Space Moved In'] = 0

    df_summary['Space Moved Out'] = df_summary['Space Moved Out'].fillna(0)
    df_summary['Space Moved In'] = df_summary['Space Moved In'].fillna(0)
    df_summary['Net Change in Space'] = df_summary['Space Moved In'] - df_summary['Space Moved Out']
    df_summary['Final Available Space'] = df_summary['Initial Available Space'] + df_summary['Net Change in Space']
    
    return df_summary[['Range', 'Collection Type', 'Range_Position', 'Initial Available Space', 'Target Available Inches', 'Initial Needed/Surplus', 'Space Moved Out', 'Space Moved In', 'Target % Empty (Calculated)']]

def display_detailed_report(is_current_year, report_start_id, report_end_id, df_initial_state, df_shift_guide, df_post_shift, selected_strategy, is_localized_run, projection_years, unit_label_short):
    start_range_num, start_range_side_val = parse_range_id(report_start_id)
    end_range_num, end_range_side_val = parse_range_id(report_end_id)
    
    if start_range_num is None or end_range_num is None:
        st.error("Invalid start or end range ID format.")
        return

    start_range_position = start_range_num + start_range_side_val
    end_range_position = end_range_num + end_range_side_val

    df_selected_ranges_initial = df_initial_state[(df_initial_state['Range_Position'] >= start_range_position) & (df_initial_state['Range_Position'] <= end_range_position)].copy()
    df_selected_ranges_impact = get_shift_impact_summary(df_selected_ranges_initial, df_shift_guide)
    df_selected_ranges_impact = df_selected_ranges_impact.sort_values(by='Range_Position', ascending=True).copy()

    result_df_impact = df_selected_ranges_impact[['Range', 'Collection Type', 'Initial Available Space', 'Target Available Inches', 'Initial Needed/Surplus', 'Space Moved Out', 'Space Moved In']].copy() 
    result_df_impact.columns = ['Range', 'Collection Type', f'Initial Available ({unit_label_short})', f'Target Available ({unit_label_short})', f'Initial Need/Surplus ({unit_label_short})', f'{unit_label_short.capitalize()} Moved Out', f'{unit_label_short.capitalize()} Moved In']

    df_selected_ranges_post_shift = df_post_shift[(df_post_shift['Range_Position'] >= start_range_position) & (df_post_shift['Range_Position'] <= end_range_position)].copy()
    remaining_need = df_selected_ranges_post_shift[df_selected_ranges_post_shift['Inches Needed/Surplus (Calculated)'] > 0]['Inches Needed/Surplus (Calculated)'].sum()

    report_title = "Current Year's Shift Impact" if is_current_year else f"Projected Year's Shift Impact ({projection_years} Years)"
    st.subheader(report_title)

    if remaining_need <= 0.001:
        st.success(f"NOTIFICATION: The needs within the selected ranges (**{report_start_id}** to **{report_end_id}**) have been fully addressed.")
    else:
        custom_warning(f"NOTIFICATION: The needs within the selected ranges (**{report_start_id}** to **{report_end_id}**) could NOT be fully addressed. Unfulfilled need: **{remaining_need:,.2f}** {unit_label_short}.")

    if not result_df_impact.empty:
        st.dataframe(result_df_impact)
        
        # --- Added Download Feature ---
        csv_data = result_df_impact.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Shift Impact Report (CSV)",
            data=csv_data,
            file_name=f"shift_impact_report_{report_start_id}_to_{report_end_id}.csv",
            mime="text/csv",
            key=f"download_shift_impact_{report_start_id}_{report_end_id}"
        )


# --- Main Application Logic ---
if uploaded_file is not None:
    st.header("2. Analysis Results")
    is_localized_run = (st.session_state.localized_analysis_active and st.session_state.localized_start_id)

    try:
        df_range_summary = load_and_process_data(uploaded_file, collection_target_map)
        df_filtered = df_range_summary[(df_range_summary['Total Capacity'] > 0) & (df_range_summary['Target % Empty (Calculated)'].notna())].copy()

        if is_localized_run:
            s_num, s_side = parse_range_id(st.session_state.localized_start_id)
            e_num, e_side = parse_range_id(st.session_state.localized_end_id)
            if s_num is not None and e_num is not None:
                df_filtered = df_filtered[(df_filtered['Range_Position'] >= s_num + s_side) & (df_filtered['Range_Position'] <= e_num + e_side)].copy()
        
        df_filtered = df_filtered.dropna(subset=['Inches Needed/Surplus (Calculated)', 'Range_Position']).copy()

        # --- Current Year Logic ---
        st.subheader(f"Current Year's Shift Summary (Min Moves Strategy)")
        df_initial_state = df_filtered.copy()
        df_shift_guide_current, final_needy_current, final_surplus_current = allocate_shifts(df_initial_state.copy())

        total_inches_shifted_current = df_shift_guide_current['Inches to Move'].sum() if not df_shift_guide_current.empty else 0
        df_post_shift_current = get_post_shift_df(df_initial_state, df_shift_guide_current)
        
        final_total_available_current = df_post_shift_current['Current Available Inches (Calculated)'].sum()
        initial_total_available = df_initial_state['Current Available Inches (Calculated)'].sum()
        total_capacity = df_filtered['Total Capacity'].sum()
        initial_overall_percent_empty = (initial_total_available / total_capacity) if total_capacity > 0 else 0
        final_overall_percent_empty_current = (final_total_available_current / total_capacity) if total_capacity > 0 else 0
        
        st.markdown(f"### Current Year Space Summary ({u_short})")
        st.write(f"**Total Capacity in Analysis Scope:** {total_capacity:,.2f} {u_short}")
        st.write(f"**Initial Available Space in Analysis Scope:** {initial_total_available:,.2f} {u_short} ({initial_overall_percent_empty:.2%})")
        st.write(f"**Total Proposed for Shift:** {total_inches_shifted_current:,.2f} {u_short}")
        st.write(f"**Remaining Unfulfilled Need:** {final_needy_current['Inches Needed/Surplus (Calculated)'].sum():,.2f} {u_short}")
        st.write(f"**Remaining Unallocated Surplus:** {final_surplus_current['Surplus Inches'].sum():,.2f} {u_short}")
        st.write(f"**Simulated Final Available Space:** {final_total_available_current:,.2f} {u_short} ({final_overall_percent_empty_current:.2%})")

        if final_needy_current['Inches Needed/Surplus (Calculated)'].sum() > 0:
            custom_warning(f"NOTIFICATION: The targeted shift for the CURRENT year could NOT be fully achieved. Remaining need: {final_needy_current['Inches Needed/Surplus (Calculated)'].sum():,.2f} {u_short}.")
        else:
            st.success(f"NOTIFICATION: The targeted shift for the CURRENT year has been fully achieved.")

        # --- Projected Year Logic ---
        st.subheader(f"Projected Year's Shift Summary ({projection_years} Years Ahead)")
        df_projected_state = df_filtered.copy()
        for index, row in df_projected_state.iterrows():
            growth_per_year = collection_growth_rates.get(row['Collection Type'], 0)
            current_occupied = row['Total Capacity'] - row['Current Available Inches (Calculated)']
            projected_growth = growth_per_year * projection_years
            df_projected_state.at[index, 'Current Available Inches (Calculated)'] = max(0, row['Total Capacity'] - (current_occupied + projected_growth))
        
        df_projected_state['Inches Needed/Surplus (Calculated)'] = df_projected_state['Target Available Inches'] - df_projected_state['Current Available Inches (Calculated)']
        proj_need_before = df_projected_state[df_projected_state['Inches Needed/Surplus (Calculated)'] > 0]['Inches Needed/Surplus (Calculated)'].sum()
        proj_surplus_before = abs(df_projected_state[df_projected_state['Inches Needed/Surplus (Calculated)'] < 0]['Inches Needed/Surplus (Calculated)'].sum())
        
        df_projected_shift_guide, final_needy_projected, _ = allocate_shifts(df_projected_state)
        total_shifted_proj = df_projected_shift_guide['Inches to Move'].sum() if not df_projected_shift_guide.empty else 0
        df_post_shift_proj = get_post_shift_df(df_projected_state, df_projected_shift_guide)
        
        final_total_available_proj = df_post_shift_proj['Current Available Inches (Calculated)'].sum()
        final_overall_percent_empty_proj = (final_total_available_proj / total_capacity) if total_capacity > 0 else 0

        st.markdown(f"### Projected Year Space Summary ({u_short})")
        st.write(f"**Projected Total Need (Before Shifts):** {proj_need_before:,.2f} {u_short}")
        st.write(f"**Projected Total Surplus (Before Shifts):** {proj_surplus_before:,.2f} {u_short}")
        st.write(f"**Total Proposed for Shift (Projected):** {total_shifted_proj:,.2f} {u_short}")
        st.write(f"**Remaining Unfulfilled Need (Projected):** {final_needy_projected['Inches Needed/Surplus (Calculated)'].sum():,.2f} {u_short}")
        st.write(f"**Simulated Final Available Space (Projected):** {final_total_available_proj:,.2f} {u_short} ({final_overall_percent_empty_proj:.2%})")

        if final_needy_projected['Inches Needed/Surplus (Calculated)'].sum() > 0:
            custom_warning(f"NOTIFICATION: The targeted shift for {projection_years} years ahead could NOT be fully achieved.")
        else:
            st.success(f"NOTIFICATION: The targeted shift for {projection_years} years ahead has been fully achieved!")

        # --- 3. Detailed Shift Impact Report ---
        st.header("3. Detailed Shift Impact Report")
        col_s, col_e, col_b = st.columns([1, 1, 1])
        with col_s: start_range_id_query = st.text_input("Start Range ID:", value=st.session_state.localized_start_id or '')
        with col_e: end_range_id_query = st.text_input("End Range ID:", value=st.session_state.localized_end_id or '')
        with col_b:
            st.markdown("##")
            if st.button("Run Localized Shift Analysis"):
                st.session_state.localized_start_id, st.session_state.localized_end_id, st.session_state.localized_analysis_active, st.session_state.report_view_active = start_range_id_query, end_range_id_query, True, True
                st.rerun()
            if is_localized_run and st.button("Reset to Full Library Analysis"):
                st.session_state.localized_analysis_active, st.session_state.report_view_active = False, True
                st.rerun()

        if st.session_state.report_view_active and start_range_id_query and end_range_id_query:
            display_detailed_report(True, start_range_id_query, end_range_id_query, df_initial_state, df_shift_guide_current, df_post_shift_current, 'min_moves', is_localized_run, projection_years, u_short)

        # --- 4. Visualizations ---
        st.header("4. Visualizations")
        BIN_CONFIG = dict(start=0.0, end=1.0, size=0.05)

        st.subheader(f"Collection Performance (Current vs. Projected vs. Target in {u_short})")
        coll_init = df_initial_state.groupby('Collection Type')['Inches Needed/Surplus (Calculated)'].sum().reset_index()
        coll_proj = df_projected_state.groupby('Collection Type')['Inches Needed/Surplus (Calculated)'].sum().reset_index()
        coll_comp = pd.merge(coll_init, coll_proj, on='Collection Type', suffixes=('_Init', '_Proj')).fillna(0)

        fig_coll = go.Figure()
        fig_coll.add_trace(go.Bar(name='Current Need', x=coll_comp['Collection Type'], y=coll_comp['Inches Needed/Surplus (Calculated)_Init'].apply(lambda x: x if x > 0 else 0), marker_color=NORMAL_COLORS['Current Needed']))
        fig_coll.add_trace(go.Bar(name='Current Surplus', x=coll_comp['Collection Type'], y=coll_comp['Inches Needed/Surplus (Calculated)_Init'].apply(lambda x: x if x < 0 else 0), marker_color=NORMAL_COLORS['Current Surplus']))
        fig_coll.add_trace(go.Bar(name=f'Projected Need ({projection_years}y)', x=coll_comp['Collection Type'], y=coll_comp['Inches Needed/Surplus (Calculated)_Proj'].apply(lambda x: x if x > 0 else 0), marker_color=NORMAL_COLORS['Projected Needed']))
        
        fig_coll.update_layout(barmode='relative', title=f'Space Needed (+) / Surplus (-) by Collection ({u_short})')
        st.plotly_chart(fig_coll, use_container_width=True)

        st.subheader("Distribution of Range Fullness")
        fig_dist = make_subplots(rows=1, cols=3, subplot_titles=('Initial % Full', 'Post-Shift % Full', f'Projected % Full ({projection_years}y)'))
        fig_dist.add_trace(go.Histogram(x=df_initial_state['Percent Full per Side'], xbins=BIN_CONFIG, name='Initial', marker_color=NORMAL_COLORS['Initial Hist']), row=1, col=1)
        fig_dist.add_trace(go.Histogram(x=df_post_shift_current['Percent Full per Side'], xbins=BIN_CONFIG, name='Post-Shift', marker_color=NORMAL_COLORS['Current Post-Shift Hist']), row=1, col=2)
        fig_dist.add_trace(go.Histogram(x=df_post_shift_proj['Percent Full per Side'], xbins=BIN_CONFIG, name='Projected', marker_color=NORMAL_COLORS['Projected Post-Shift Hist']), row=1, col=3)
        fig_dist.update_xaxes(tickformat=".0%", range=[0, 1])
        st.plotly_chart(fig_dist, use_container_width=True)

    except Exception as e:
        st.error(f"Analysis error: {e}")
else:
    st.info("Upload your 'Range Summary' CSV file to begin.")