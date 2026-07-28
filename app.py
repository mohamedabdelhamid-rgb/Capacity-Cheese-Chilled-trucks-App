import streamlit as st
import pandas as pd
import math

# Page Setup
st.set_page_config(
    page_title="Breadfast Logistics Planner",
    page_icon="🚚",
    layout="wide"
)

# Custom Styling - Light theme, brand colors, no black text/background anywhere
st.markdown("""
<style>
    .stApp, [data-testid="stSidebar"] {
        background-color: #FAF7FB;
    }

    .main-header {
        background-color: #AA0082;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
    }
    .main-header h1 {
        color: #FFFFFF;
        margin: 0;
        font-weight: 800;
    }
    .main-header p {
        color: #FFD966;
        margin-top: 5px;
        font-weight: 600;
    }

    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border-left: 5px solid #AA0082;
        padding: 12px;
        border-radius: 8px;
    }
    div[data-testid="stMetric"] label {
        color: #6B5B73 !important;
        font-weight: bold !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #AA0082 !important;
        font-weight: bold !important;
    }

    div[data-baseweb="input"], div[data-baseweb="select"] {
        background-color: #FFFFFF;
        border: 1px solid #AA0082;
        border-radius: 6px;
    }

    .streamlit-expanderHeader {
        background-color: #F3E9F1;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# Header Section
st.markdown("""
<div class="main-header">
    <h1>🍞 Breadfast Logistics Planning</h1>
    <p>Multi-Branch & Full Category Truck Capacity Allocator</p>
</div>
""", unsafe_allow_html=True)

RACK_FILE = "Rack Capacity.xlsx"

# Each team lives on its own sheet in the same workbook
TEAM_SHEETS = {
    "Cheese Team": "Cheese Team",
    "Chilled Team": "Chilled Team"
}

# Truck capacities (in racks)
TRUCK_CAPACITIES = {
    "Standard Chiller Truck": 70,
    "NKR Truck": 150,
    "Jumbo Chiller Truck": 300
}


@st.cache_data
def load_rack_data(sheet_name):
    try:
        df = pd.read_excel(RACK_FILE, sheet_name=sheet_name)
        df.columns = df.columns.str.strip()

        # Clean up extra whitespace in text columns so branch matching works correctly
        for col in ['Destination#1', 'Destination#2', 'Category', 'SKU']:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

        return df
    except Exception as e:
        st.error(f"Error loading sheet '{sheet_name}' from '{RACK_FILE}': {e}")
        return None


# ------------------- Sidebar: Trip Settings -------------------
st.sidebar.header("⚙️ Trip Settings")

# 0) Team selection (which sheet to load)
selected_team = st.sidebar.selectbox(
    "Select Team:",
    list(TEAM_SHEETS.keys()),
    index=0
)

rack_df = load_rack_data(TEAM_SHEETS[selected_team])

if rack_df is not None:
    # List of all branches across both destination columns
    dest1 = rack_df['Destination#1'].dropna().unique().tolist() if 'Destination#1' in rack_df.columns else []
    dest2 = rack_df['Destination#2'].dropna().unique().tolist() if 'Destination#2' in rack_df.columns else []
    all_branches = sorted(list(set(dest1 + dest2)))

    # 1) Branch selection is informational only (for the route label / metrics).
    #    It NEVER filters the product list — all products, all categories, and
    #    all branches are always shown regardless of what's picked here.
    selected_branches = st.sidebar.multiselect(
        "Select Branch(es) for this Truck Route (optional, for labeling only):",
        options=all_branches,
        default=[]
    )

    # 2) Truck type
    selected_truck_type = st.sidebar.selectbox(
        "Select Truck Type:",
        list(TRUCK_CAPACITIES.keys()),
        index=0
    )
    truck_max_capacity = TRUCK_CAPACITIES[selected_truck_type]

    st.sidebar.markdown(f"**Selected Truck Capacity:** {truck_max_capacity} Racks")

    st.sidebar.info("📦 All products, categories, and branches are always shown below — nothing is filtered out.")

    # ------------------- Always show ALL products for the selected team -------------------
    filtered_df = rack_df.copy()

    # Trip header
    st.markdown(f"### 🧑‍🤝‍🧑 Team: **{selected_team}**")
    if selected_branches:
        st.markdown(f"### 📍 Route Branches: **{', '.join(selected_branches)}**")
    else:
        st.markdown(f"### 📍 All Branches: **{', '.join(all_branches) if all_branches else 'N/A'}**")

    st.markdown(f"### 📦 Enter Demand Quantities ({len(filtered_df)} Products)")

    # Group products by category — every category present in the sheet is shown
    categories = sorted(filtered_df['Category'].dropna().unique().tolist()) if 'Category' in filtered_df.columns else ['All Products']

    input_records = []

    # Display all products, grouped by category
    for cat in categories:
        cat_skus = filtered_df[filtered_df['Category'] == cat] if 'Category' in filtered_df.columns else filtered_df

        with st.expander(f"📂 Category: **{cat}** ({len(cat_skus)} Products)", expanded=True):
            col1, col2 = st.columns(2)

            for idx, row in cat_skus.reset_index(drop=True).iterrows():
                sku_name = row.get('SKU', f"Item #{idx + 1}")
                units_per_container = row.get('Item per container', 1)

                with col1 if idx % 2 == 0 else col2:
                    demand_qty = st.number_input(
                        f"**{sku_name}** (Units/Rack: {units_per_container})",
                        min_value=0,
                        value=0,
                        step=10,
                        key=f"input_{selected_team}_{cat}_{idx}_{sku_name}"
                    )

                    if demand_qty > 0:
                        racks_needed = demand_qty / units_per_container if units_per_container > 0 else 0
                        input_records.append({
                            "Category": cat,
                            "SKU": sku_name,
                            "Demand (Units)": demand_qty,
                            "Units/Rack": units_per_container,
                            "Calculated Racks": racks_needed
                        })

    # ------------------- Final calculation -------------------
    if input_records:
        summary_df = pd.DataFrame(input_records)
        total_racks = summary_df['Calculated Racks'].sum()

        trucks_needed = math.ceil(total_racks / truck_max_capacity) if truck_max_capacity > 0 else 0
        overall_fill_pct = (total_racks / (trucks_needed * truck_max_capacity) * 100) if trucks_needed > 0 else 0

        summary_df['Truck Capacity Share %'] = summary_df['Calculated Racks'].apply(
            lambda r: f"{(r / truck_max_capacity * 100):.1f}%"
        )

        st.markdown("---")
        st.markdown("### 🚛 Fleet & Truck Fill Metrics")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Racks Needed", f"{total_racks:.2f}")
        m2.metric("Truck Type & Limit", f"{selected_truck_type} ({truck_max_capacity} Racks)")
        m3.metric("Required Trucks", f"{trucks_needed}")
        m4.metric("Truck Fill %", f"{overall_fill_pct:.1f}%")

        st.markdown("#### 📋 Order & Truck Share Summary")
        st.dataframe(summary_df, use_container_width=True)

        if overall_fill_pct > 100:
            st.error(f"⚠️ Demand exceeds a single truck's capacity! Need **{trucks_needed} trucks**.")
        elif overall_fill_pct >= 85:
            st.success(f"✅ Optimal truck usage! Filled at **{overall_fill_pct:.1f}%**.")
        else:
            st.warning(f"⚠️ Low capacity utilization (**{overall_fill_pct:.1f}%**). Consider adding more stock.")
    else:
        st.info("Enter quantities above to see the truck capacity calculation.")
else:
    st.error(f"Could not load the '{selected_team}' sheet from '{RACK_FILE}'. Please check the file is uploaded to your repo and the sheet name matches.")
