import streamlit as st
import pandas as pd
import math

# إعدادات الصفحة
st.set_page_config(
    page_title="Breadfast - Truck Capacity Calculator",
    page_icon="🍞",
    layout="wide"
)

# Breadfast Custom Styling (CSS)
st.markdown("""
    <style>
    /* Main Background & Fonts */
    .main {
        background-color: #F8F9FA;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Header Styling */
    .main-header {
        background-color: #0B192C; /* Breadfast Dark Navy */
        padding: 24px;
        border-radius: 12px;
        color: #FFFFFF;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 {
        color: #FFC107; /* Breadfast Yellow Accent */
        margin: 0;
        font-size: 32px;
        font-weight: 700;
    }
    .main-header p {
        color: #E0E0E0;
        margin-top: 8px;
        font-size: 16px;
    }

    /* Card Box */
    .metric-card {
        background-color: #FFFFFF;
        border-left: 6px solid #FFC107;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .metric-title {
        font-size: 14px;
        color: #6C757D;
        font-weight: bold;
    }
    .metric-value {
        font-size: 28px;
        color: #0B192C;
        font-weight: bold;
    }

    /* Truck Status Boxes */
    .truck-box-full {
        background-color: #E8F5E9;
        border: 1px solid #81C784;
        border-right: 6px solid #2E7D32;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 12px;
        color: #1B5E20;
    }
    .truck-box-partial {
        background-color: #FFF8E1;
        border: 1px solid #FFE082;
        border-right: 6px solid #FFB300;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 12px;
        color: #E65100;
    }

    /* Custom Progress Bar Color */
    .stProgress > div > div > div > div {
        background-color: #FFC107 !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #1E293B;
    }
    section[data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    </style>
""", unsafe_allow_html=True)

# App Header
st.markdown("""
    <div class="main-header">
        <h1>🍞 Breadfast Logistics</h1>
        <p>حاسبة سعة عربات التبريد والتوزيع (Truck Capacity Calculator)</p>
    </div>
""", unsafe_allow_html=True)

# Load Data from Excel
@st.cache_data
def load_data():
    excel_path = 'Rack Capacity.xlsx'
    cheese_df = pd.read_excel(excel_path, sheet_name='cheese')
    chilled_df = pd.read_excel(excel_path, sheet_name='chilled')
    return cheese_df, chilled_df

try:
    cheese_df, chilled_df = load_data()

    # Sidebar Team Selection
    st.sidebar.title("🍞 Breadfast")
    st.sidebar.subheader("إعدادات الخطة")
    team = st.sidebar.radio("اختر التيم (Team):", ["Cheese", "Chilled"])

    if team == "Cheese":
        df = cheese_df.copy()
        cap_col = 'Rack Capacity (Qty per Rack)'
    else:
        df = chilled_df.copy()
        cap_col = 'Item per container'

    st.subheader(f"🛒 خطة شحن قسم: {team}")

    # Multiselect SKUs
    selected_skus = st.multiselect("اختر المنتجات المراد إضافتها للخطة:", df['SKU'].unique())

    plan_data = []

    if selected_skus:
        st.markdown("### 📦 إدخال الكميات:")
        
        col1, col2 = st.columns(2)
        total_racks = 0
        
        for idx, sku in enumerate(selected_skus):
            rack_cap = df[df['SKU'] == sku][cap_col].values[0]
            
            # Divide into 2 columns for better layout
            with (col1 if idx % 2 == 0 else col2):
                qty = st.number_input(f"{sku} (الـ Rack: {rack_cap} قطعة)", min_value=0, value=0, step=10, key=sku)
            
            racks_needed = qty / rack_cap if rack_cap > 0 else 0
            total_racks += racks_needed
            
            if qty > 0:
                plan_data.append({
                    "اسم المنتج (SKU)": sku,
                    "الكمية بالقطع": qty,
                    "سعة الـ Rack": rack_cap,
                    "عدد الـ Racks": round(racks_needed, 2)
                })

        st.markdown("---")
        
        # Display Metrics
        truck_capacity = 70
        full_trucks = int(total_racks // truck_capacity)
        remaining_racks = total_racks % truck_capacity
        total_trucks_needed = math.ceil(total_racks / truck_capacity) if total_racks > 0 else 0
        
        col_m1, col_m2, col_m3 = st.columns(3)
        
        with col_m1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">إجمالي الـ Racks المطلوبة</div>
                    <div class="metric-value">{total_racks:.2f} Racks</div>
                </div>
            """, unsafe_allow_html=True)
            
        with col_m2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">عدد العربيات المطلوبة</div>
                    <div class="metric-value">{total_trucks_needed} عربات</div>
                </div>
            """, unsafe_allow_html=True)
            
        with col_m3:
            overall_fill = (total_racks / (total_trucks_needed * 70) * 100) if total_trucks_needed > 0 else 0
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">متوسط نسبة استغلال العربية</div>
                    <div class="metric-value">{overall_fill:.1f}%</div>
                </div>
            """, unsafe_allow_html=True)

        # Plan Summary Table
        if plan_data:
            st.markdown("### 📋 تفاصيل الخطة:")
            st.dataframe(pd.DataFrame(plan_data), use_container_width=True)

        # Truck Breakdown
        st.markdown("### 🚛 نسبة امتلاء كل عربية:")
        
        if total_racks == 0:
            st.info("من فضلك أدخل كميات للمنتجات لعرض نسبة امتلاء العربيات.")
        else:
            # Full Trucks
            for i in range(1, full_trucks + 1):
                st.markdown(f"""
                    <div class="truck-box-full">
                        <b>🚛 العربية رقم {i}:</b> مليانة بالكامل بنسبة <b>100%</b> (70 / 70 Racks) ✅
                    </div>
                """, unsafe_allow_html=True)
                st.progress(1.0)
                
            # Partial Truck
            if remaining_racks > 0:
                rem_percentage = (remaining_racks / truck_capacity) * 100
                st.markdown(f"""
                    <div class="truck-box-partial">
                        <b>🚚 العربية رقم {full_trucks + 1}:</b> مليانة بنسبة <b>{rem_percentage:.1f}%</b> ({remaining_racks:.2f} / 70 Racks) ⚠️
                    </div>
                """, unsafe_allow_html=True)
                st.progress(rem_percentage / 100.0)

except Exception as e:
    st.error(f"حدث خطأ أثناء تحميل البيانات: {e}")
