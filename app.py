import streamlit as st
import pandas as pd
import math

# Page Setup
st.set_page_config(
    page_title="Breadfast Logistics Planner",
    page_icon="🚚",
    layout="wide"
)

# Custom Styling - Force Light Mode & Full Contrast (No Black Backgrounds)
st.markdown("""
<style>
    .stApp, [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        color: #111111 !important;
    }
    
    p, span, label, h1, h2, h3, h4, h5, h6, div, .stMarkdown {
        color: #111111 !important;
    }

    .main-header {
        background-color: #AA0082 !important;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
    }
    .main-header h1 {
        color: #FFFFFF !important;
        margin: 0;
        font-weight: 800;
    }
    .main-header p {
        color: #FFC107 !important;
        margin-top: 5px;
        font-weight: 600;
    }

    div[data-testid="stMetric"] {
        background-color: #F8F9FA !important;
        border-left: 5px solid #AA0082 !important;
        padding: 12px;
        border-radius: 8px;
    }
    div[data-testid="stMetric"] label {
        color: #444444 !important;
        font-weight: bold !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #AA0082 !important;
        font-weight: bold !important;
    }

    div[data-baseweb="input"], div[data-baseweb="select"] {
        background-color: #FFFFFF !important;
        border: 1px solid #AA0082 !important;
    }
    input {
        color: #111111 !important;
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

# سعات الشاحنات (بالراك)
TRUCK_CAPACITIES = {
    "شاحنة تبريد عادية (Standard)": 70,
    "شاحنة NKR": 150,
    "شاحنة جامبو تبريد (Jumbo)": 300
}


@st.cache_data
def load_rack_data():
    try:
        df = pd.read_excel(RACK_FILE)
        df.columns = df.columns.str.strip()

        # تنظيف القيم النصية (إزالة المسافات الزيادة) عشان مطابقة الفروع تبقى صح
        for col in ['Destination#1', 'Destination#2', 'Category', 'SKU']:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

        return df
    except Exception as e:
        st.error(f"خطأ في تحميل الملف '{RACK_FILE}': {e}")
        return None


rack_df = load_rack_data()

if rack_df is not None:
    # قائمة كل الفروع الموجودة في العمودين
    dest1 = rack_df['Destination#1'].dropna().unique().tolist() if 'Destination#1' in rack_df.columns else []
    dest2 = rack_df['Destination#2'].dropna().unique().tolist() if 'Destination#2' in rack_df.columns else []
    all_branches = sorted(list(set(dest1 + dest2)))

    # ------------------- الشريط الجانبي: إعدادات الرحلة -------------------
    st.sidebar.header("⚙️ إعدادات الرحلة")

    # 1) اختيار فرع أو فرعين (أو أكتر) للعربية دي
    selected_branches = st.sidebar.multiselect(
        "اختر الفرع/الفروع اللي العربية رايحالهم:",
        options=all_branches,
        default=[]
    )

    # 2) نوع الشاحنة
    selected_truck_type = st.sidebar.selectbox(
        "اختر نوع الشاحنة:",
        list(TRUCK_CAPACITIES.keys()),
        index=0
    )
    truck_max_capacity = TRUCK_CAPACITIES[selected_truck_type]

    st.sidebar.markdown(f"**سعة الشاحنة المختارة:** {truck_max_capacity} Racks")

    # 3) خيار: هل عايز تفلتر المنتجات حسب الفرع المختار ولا تشوف كل المنتجات؟
    filter_by_branch = st.sidebar.checkbox(
        "فلترة المنتجات حسب الفرع/الفروع المختارة فقط",
        value=False,
        help="لو مش مفعّل، هتظهرلك كل المنتجات دايمًا زي ما هي بالملف."
    )

    # ------------------- تحديد المنتجات اللي هتتعرض -------------------
    if filter_by_branch and selected_branches:
        condition = pd.Series(False, index=rack_df.index)
        if 'Destination#1' in rack_df.columns:
            condition |= rack_df['Destination#1'].isin(selected_branches)
        if 'Destination#2' in rack_df.columns:
            condition |= rack_df['Destination#2'].isin(selected_branches)

        filtered_df = rack_df[condition].copy()

        if filtered_df.empty:
            st.warning("مفيش منتجات مطابقة للفروع المختارة، هيتم عرض كل المنتجات بدل ما القائمة تفضل فاضية.")
            filtered_df = rack_df.copy()
    else:
        # الافتراضي: عرض كل المنتجات دايمًا (مفيش فلترة تخفي منتجات بالغلط)
        filtered_df = rack_df.copy()

    # عنوان الرحلة
    if selected_branches:
        st.markdown(f"### 📍 فروع الرحلة: **{', '.join(selected_branches)}**")
    else:
        st.markdown("### 📍 لسه ماخترتش فروع للرحلة (اختر من القائمة الجانبية)")

    st.markdown(f"### 📦 إدخال الكميات المطلوبة لكل المنتجات ({len(filtered_df)} منتج)")

    # Group Products by Category
    categories = filtered_df['Category'].dropna().unique() if 'Category' in filtered_df.columns else ['كل المنتجات']

    input_records = []

    # عرض كل المنتجات مقسّمة حسب الفئة
    for cat in categories:
        cat_skus = filtered_df[filtered_df['Category'] == cat] if 'Category' in filtered_df.columns else filtered_df

        with st.expander(f"📂 الفئة: **{cat}** ({len(cat_skus)} منتج)", expanded=True):
            col1, col2 = st.columns(2)

            for idx, row in cat_skus.reset_index(drop=True).iterrows():
                sku_name = row.get('SKU', f"منتج #{idx + 1}")
                units_per_container = row.get('Item per container', 1)

                with col1 if idx % 2 == 0 else col2:
                    demand_qty = st.number_input(
                        f"**{sku_name}** (وحدة/راك: {units_per_container})",
                        min_value=0,
                        value=0,
                        step=10,
                        key=f"input_{cat}_{idx}_{sku_name}"
                    )

                    if demand_qty > 0:
                        racks_needed = demand_qty / units_per_container if units_per_container > 0 else 0
                        input_records.append({
                            "الفئة": cat,
                            "المنتج": sku_name,
                            "الكمية (وحدة)": demand_qty,
                            "وحدة/راك": units_per_container,
                            "عدد الراكات": racks_needed
                        })

    # ------------------- حساب النتيجة النهائية -------------------
    if input_records:
        summary_df = pd.DataFrame(input_records)
        total_racks = summary_df['عدد الراكات'].sum()

        trucks_needed = math.ceil(total_racks / truck_max_capacity) if truck_max_capacity > 0 else 0
        overall_fill_pct = (total_racks / (trucks_needed * truck_max_capacity) * 100) if trucks_needed > 0 else 0

        summary_df['نسبة إشغال الشاحنة %'] = summary_df['عدد الراكات'].apply(
            lambda r: f"{(r / truck_max_capacity * 100):.1f}%"
        )

        st.markdown("---")
        st.markdown("### 🚛 نتائج تحميل الشاحنة")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("إجمالي الراكات المطلوبة", f"{total_racks:.2f}")
        m2.metric("نوع وسعة الشاحنة", f"{selected_truck_type} ({truck_max_capacity} Racks)")
        m3.metric("عدد الشاحنات المطلوبة", f"{trucks_needed}")
        m4.metric("نسبة الإشغال", f"{overall_fill_pct:.1f}%")

        st.markdown("#### 📋 ملخص الطلب ونسبة الإشغال")
        st.dataframe(summary_df, use_container_width=True)

        if overall_fill_pct > 100:
            st.error(f"⚠️ الكمية أكبر من سعة شاحنة واحدة! محتاج **{trucks_needed} شاحنة**.")
        elif overall_fill_pct >= 85:
            st.success(f"✅ استغلال ممتاز للشاحنة! نسبة الإشغال **{overall_fill_pct:.1f}%**.")
        else:
            st.warning(f"⚠️ استغلال منخفض لسعة الشاحنة (**{overall_fill_pct:.1f}%**). فكر تضيف كمية أكتر.")
    else:
        st.info("دخّل الكميات فوق عشان تشوف حساب سعة الشاحنة.")
else:
    st.error("ملف 'Rack Capacity.xlsx' مش موجود. من فضلك ارفعه في الريبو بتاعك.")
