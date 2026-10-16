import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

# ==============================================================================
# 1. Konfigurasi Halaman Streamlit
# ==============================================================================
st.set_page_config(
    page_title="E-Commerce Business & Logistics Dashboard",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Styling visualisasi
sns.set_theme(style="whitegrid")
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.size"] = 10

# ==============================================================================
# 2. Fungsi Pemuatan & Pembersihan Data (Cached)
# ==============================================================================
@st.cache_data
def load_data():
    """
    Memuat dataset main_data.csv jika sudah ada, atau melakukan penggabungan
    data mentah secara otomatis jika berkas main_data.csv belum dibuat.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)

    candidate_main_paths = [
        os.path.join(current_dir, "main_data.csv"),
        os.path.join(current_dir, "main_data.csv.gz"),
        os.path.join(parent_dir, "dashboard", "main_data.csv"),
        "dashboard/main_data.csv",
        "main_data.csv",
        os.path.join(parent_dir, "main_data.csv"),
    ]
    
    for p in candidate_main_paths:
        if os.path.exists(p):
            df = pd.read_csv(p)
            date_cols = [
                "order_purchase_timestamp",
                "order_delivered_customer_date",
                "order_estimated_delivery_date"
            ]
            for col in date_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
            return df

    # Fallback jika main_data.csv belum tersedia: muat dari dataset mentah
    candidate_raw_dirs = [
        os.path.join(parent_dir, "data"),
        os.path.join(current_dir, "..", "data"),
        "data",
        "../data",
        "E-commerce-public-dataset/E-Commerce Public Dataset",
        "../E-commerce-public-dataset/E-Commerce Public Dataset"
    ]
    
    raw_dir = None
    for d in candidate_raw_dirs:
        if os.path.exists(os.path.join(d, "orders_dataset.csv")):
            raw_dir = d
            break
            
    if raw_dir is None:
        st.error("Dataset tidak ditemukan. Pastikan berkas CSV berada di folder data/ atau direktori dashboard/.")
        st.stop()
        
    orders_df = pd.read_csv(os.path.join(raw_dir, "orders_dataset.csv"))
    order_items_df = pd.read_csv(os.path.join(raw_dir, "order_items_dataset.csv"))
    products_df = pd.read_csv(os.path.join(raw_dir, "products_dataset.csv"))
    cat_trans_df = pd.read_csv(os.path.join(raw_dir, "product_category_name_translation.csv"))
    reviews_df = pd.read_csv(os.path.join(raw_dir, "order_reviews_dataset.csv"))
    customers_df = pd.read_csv(os.path.join(raw_dir, "customers_dataset.csv"))
    
    # Standarisasi tipe tanggal
    for col in ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]:
        orders_df[col] = pd.to_datetime(orders_df[col], errors="coerce")
        
    # Filter pesanan delivered 2017-2018
    orders_delivered = orders_df[
        (orders_df["order_status"] == "delivered") &
        (orders_df["order_delivered_customer_date"].notna()) &
        (orders_df["order_purchase_timestamp"].dt.year >= 2017) &
        (orders_df["order_purchase_timestamp"].dt.year <= 2018)
    ].copy()
    
    orders_delivered["delivery_delay_days"] = (
        orders_delivered["order_delivered_customer_date"] - orders_delivered["order_estimated_delivery_date"]
    ).dt.total_seconds() / (24 * 3600)
    
    orders_delivered["delivery_status"] = orders_delivered["delivery_delay_days"].apply(
        lambda x: "Late" if x > 0 else "On Time"
    )
    
    # Penerjemahan kategori
    products_clean = pd.merge(products_df, cat_trans_df, on="product_category_name", how="left")
    products_clean["product_category_name_english"] = products_clean["product_category_name_english"].fillna("others")
    
    # Penggabungan seluruh entitas
    main_df = pd.merge(
        order_items_df[["order_id", "order_item_id", "product_id", "price", "freight_value"]],
        orders_delivered[["order_id", "customer_id", "order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date", "delivery_delay_days", "delivery_status"]],
        on="order_id",
        how="inner"
    )
    main_df = pd.merge(
        main_df,
        products_clean[["product_id", "product_category_name_english"]],
        on="product_id",
        how="left"
    )
    main_df = pd.merge(
        main_df,
        reviews_df[["order_id", "review_score"]].drop_duplicates(subset=["order_id"]),
        on="order_id",
        how="left"
    )
    main_df = pd.merge(
        main_df,
        customers_df[["customer_id", "customer_unique_id", "customer_city", "customer_state"]],
        on="customer_id",
        how="left"
    )
    
    # Simpan berkas main_data.csv HANYA di dalam folder dashboard
    try:
        out_csv = os.path.join(current_dir, "main_data.csv")
        main_df.to_csv(out_csv, index=False)
    except Exception:
        pass
        
    return main_df

# ==============================================================================
# 3. Fungsi Agregasi Metrik & Visualisasi
# ==============================================================================
def create_category_performance_df(df):
    cat_df = df.groupby("product_category_name_english").agg(
        total_revenue=("price", "sum"),
        total_items_sold=("order_item_id", "count"),
        total_orders=("order_id", "nunique"),
        avg_price=("price", "mean")
    ).reset_index().sort_values(by="total_revenue", ascending=False)
    return cat_df

def create_delivery_satisfaction_df(df):
    orders_unique = df.drop_duplicates(subset=["order_id"]).dropna(subset=["delivery_status", "review_score"])
    summary = orders_unique.groupby("delivery_status").agg(
        total_reviews=("review_score", "count"),
        avg_review_score=("review_score", "mean"),
        median_review_score=("review_score", "median")
    ).reset_index()
    
    rating_crosstab = (
        pd.crosstab(
            orders_unique["delivery_status"],
            orders_unique["review_score"],
            normalize="index"
        ) * 100
    ).round(2)
    
    return summary, rating_crosstab

def create_rfm_df(df):
    recent_date = df["order_purchase_timestamp"].max() + pd.Timedelta(days=1)
    rfm = df.groupby("customer_unique_id").agg(
        max_order_timestamp=("order_purchase_timestamp", "max"),
        frequency=("order_id", "nunique"),
        monetary=("price", "sum")
    ).reset_index()
    rfm["recency"] = (recent_date - rfm["max_order_timestamp"]).dt.days
    rfm.drop(columns=["max_order_timestamp"], inplace=True)
    return rfm

def create_bystate_df(df):
    state_df = df.drop_duplicates(subset=["order_id"]).groupby("customer_state")["order_id"].nunique().reset_index(name="order_count")
    return state_df.sort_values(by="order_count", ascending=False)

# ==============================================================================
# 4. Pemuatan Data Awal & Sidebar Kontrol
# ==============================================================================
raw_main_df = load_data()

min_date = raw_main_df["order_purchase_timestamp"].dropna().min().date()
max_date = raw_main_df["order_purchase_timestamp"].dropna().max().date()

with st.sidebar:
    try:
        st.image("https://raw.githubusercontent.com/dicodingacademy/assets/main/logo.png", width=220)
    except Exception:
        st.subheader("Dicoding Academy")
        
    st.title("⚙️ Filter Analisis")
    st.markdown("Sesuaikan rentang waktu dan wilayah untuk melihat dinamika data.")
    
    # Filter Rentang Tanggal
    date_range = st.date_input(
        label="📅 Rentang Waktu Pemesanan:",
        min_value=min_date,
        max_value=max_date,
        value=[min_date, max_date]
    )
    
    # Filter Negara Bagian (States)
    all_states = sorted(raw_main_df["customer_state"].dropna().unique().tolist())
    selected_states = st.multiselect(
        label="📍 Pilih Negara Bagian (State):",
        options=all_states,
        default=all_states
    )
    
    st.markdown("---")
    st.markdown("**Proyek Akhir:** Fundamental Analisis Data")
    st.markdown("**Author:** Gabriel Jel Blessly Aipassa")

# Validasi filter tanggal
if isinstance(date_range, (list, tuple)):
    if len(date_range) == 2:
        start_date, end_date = date_range
    elif len(date_range) == 1:
        start_date = date_range[0]
        end_date = max_date
    else:
        start_date, end_date = min_date, max_date
else:
    start_date, end_date = min_date, max_date

if start_date > end_date:
    start_date, end_date = end_date, start_date

# Penerapan Filter
filtered_df = raw_main_df[
    (raw_main_df["order_purchase_timestamp"].dt.date >= start_date) &
    (raw_main_df["order_purchase_timestamp"].dt.date <= end_date) &
    (raw_main_df["customer_state"].isin(selected_states))
]

if filtered_df.empty:
    st.warning("Tidak ada data transaksi yang sesuai dengan kombinasi filter yang dipilih.")
    st.stop()

# ==============================================================================
# 5. Header & KPI Metrik Utama
# ==============================================================================
st.title("🛍️ E-Commerce Business & Delivery Performance Dashboard")
st.markdown(f"Menganalisis performa platform e-commerce pada periode **{start_date.strftime('%d %b %Y')}** hingga **{end_date.strftime('%d %b %Y')}**.")

# Perhitungan KPI Metrik
total_revenue = filtered_df["price"].sum()
total_orders = filtered_df["order_id"].nunique()
avg_review = filtered_df.drop_duplicates(subset=["order_id"])["review_score"].mean()

orders_status_counts = filtered_df.drop_duplicates(subset=["order_id"])["delivery_status"].value_counts(normalize=True)
ontime_rate = orders_status_counts.get("On Time", 0.0) * 100

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Revenue", f"R$ {total_revenue:,.0f}")
with col2:
    st.metric("Total Pesanan", f"{total_orders:,}")
with col3:
    st.metric("Rata-rata Skor Ulasan", f"{avg_review:.2f} / 5.0" if pd.notna(avg_review) else "N/A")
with col4:
    st.metric("Tingkat Ketepatan Waktu", f"{ontime_rate:.1f}%")

st.markdown("---")

# ==============================================================================
# 6. Tab Navigasi Analisis
# ==============================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🏆 Performa Produk",
    "🚚 Kepuasan & Pengiriman",
    "👥 Analisis RFM",
    "🗺️ Demografi Geospasial"
])

# ------------------------------------------------------------------------------
# TAB 1: PERFORMA KATEGORI PRODUK
# ------------------------------------------------------------------------------
with tab1:
    st.subheader("Top 5 dan Bottom 5 Kategori Produk Berdasarkan Total Revenue")
    st.markdown("Identifikasi kategori produk yang menjadi motor penggerak pendapatan serta kategori dengan volume terendah.")
    
    cat_df = create_category_performance_df(filtered_df)
    
    top_5 = cat_df.head(5).copy()
    bottom_5 = cat_df.tail(5).sort_values(by="total_revenue", ascending=True).copy()
    
    fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(18, 6))
    
    # Top 5 Chart
    colors_top = ["#1A5276", "#2980B9", "#5DADE2", "#85C1E9", "#AED6F1"][:len(top_5)]
    bars_top = sns.barplot(
        x="total_revenue",
        y="product_category_name_english",
        data=top_5,
        hue="product_category_name_english",
        palette=colors_top,
        legend=False,
        ax=axes[0]
    )
    axes[0].set_title("Top 5 Kategori Produk (Revenue Tertinggi)", fontsize=13, fontweight="bold", pad=12)
    axes[0].set_xlabel("Total Revenue (BRL)", fontsize=11)
    axes[0].set_ylabel("Kategori Produk", fontsize=11)
    max_rev_top = top_5["total_revenue"].max() if not top_5.empty else 100
    axes[0].set_xlim(0, max_rev_top * 1.25 if max_rev_top > 0 else 100)
    axes[0].xaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: f"R$ {x:,.0f}"))
    
    for bar in bars_top.patches:
        width = bar.get_width()
        if pd.notna(width) and width > 0:
            axes[0].annotate(
                f"R$ {width:,.0f}",
                (width, bar.get_y() + bar.get_height() / 2.),
                ha="left", va="center",
                xytext=(6, 0), textcoords="offset points",
                fontsize=10, fontweight="bold"
            )
        
    # Bottom 5 Chart
    colors_bottom = ["#922B21", "#C0392B", "#E74C3C", "#F1948A", "#FADBD8"][:len(bottom_5)]
    bars_bottom = sns.barplot(
        x="total_revenue",
        y="product_category_name_english",
        data=bottom_5,
        hue="product_category_name_english",
        palette=colors_bottom,
        legend=False,
        ax=axes[1]
    )
    axes[1].set_title("Bottom 5 Kategori Produk (Revenue Terendah)", fontsize=13, fontweight="bold", pad=12)
    axes[1].set_xlabel("Total Revenue (BRL)", fontsize=11)
    axes[1].set_ylabel("Kategori Produk", fontsize=11)
    max_rev_bot = bottom_5["total_revenue"].max() if not bottom_5.empty else 100
    axes[1].set_xlim(0, max(max_rev_bot * 1.35, 100))
    axes[1].xaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: f"R$ {x:,.0f}"))
    
    for bar in bars_bottom.patches:
        width = bar.get_width()
        if pd.notna(width) and width > 0:
            axes[1].annotate(
                f"R$ {width:,.0f}",
                (width, bar.get_y() + bar.get_height() / 2.),
                ha="left", va="center",
                xytext=(6, 0), textcoords="offset points",
                fontsize=10, fontweight="bold"
            )
        
    plt.tight_layout()
    st.pyplot(fig)
    
    with st.expander("🔍 Lihat Rincian Tabel Agregasi Kategori Produk"):
        try:
            st.dataframe(
                cat_df.style.format({
                    "total_revenue": "R$ {:,.2f}",
                    "total_items_sold": "{:,}",
                    "total_orders": "{:,}",
                    "avg_price": "R$ {:,.2f}"
                }, na_rep="-"),
                use_container_width=True
            )
        except Exception:
            display_df = cat_df.copy()
            display_df["total_revenue"] = display_df["total_revenue"].apply(lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "-")
            display_df["total_items_sold"] = display_df["total_items_sold"].apply(lambda x: f"{x:,}" if pd.notna(x) else "-")
            display_df["total_orders"] = display_df["total_orders"].apply(lambda x: f"{x:,}" if pd.notna(x) else "-")
            display_df["avg_price"] = display_df["avg_price"].apply(lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "-")
            st.dataframe(display_df, use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 2: KEPUASAN & PENGIRIMAN
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("Dampak Keterlambatan Pengiriman Terhadap Kepuasan Pelanggan")
    st.markdown("Evaluasi korelasi status kedatangan aktual vs estimasi terhadap skor kepuasan ulasan pembeli.")
    
    delivery_summary, rating_dist = create_delivery_satisfaction_df(filtered_df)
    
    palette_status = {"On Time": "#27AE60", "Late": "#C0392B"}
    
    fig_deliv, axes_deliv = plt.subplots(nrows=1, ncols=2, figsize=(16, 5.5))
    
    # Subplot 1: Rata-rata Skor Ulasan
    bars_avg = sns.barplot(
        x="delivery_status",
        y="avg_review_score",
        data=delivery_summary,
        hue="delivery_status",
        palette=palette_status,
        legend=False,
        ax=axes_deliv[0],
        width=0.45
    )
    axes_deliv[0].set_title("Rata-rata Skor Ulasan (Skala 1 - 5)", fontsize=13, fontweight="bold", pad=12)
    axes_deliv[0].set_xlabel("Status Pengiriman", fontsize=11)
    axes_deliv[0].set_ylabel("Skor Ulasan Rata-rata", fontsize=11)
    axes_deliv[0].set_ylim(0, 5.5)
    
    for bar in bars_avg.patches:
        h = bar.get_height()
        if pd.notna(h) and h > 0:
            axes_deliv[0].annotate(
                f"{h:.2f} / 5.0",
                (bar.get_x() + bar.get_width() / 2., h),
                ha="center", va="bottom",
                xytext=(0, 6), textcoords="offset points",
                fontsize=11, fontweight="bold"
            )
        
    # Subplot 2: Sebaran Persentase Rating Bintang 1 - 5
    rating_melted = rating_dist.reset_index().melt(
        id_vars="delivery_status",
        var_name="review_score",
        value_name="percentage"
    )
    rating_melted["review_score"] = rating_melted["review_score"].apply(
        lambda x: f"★ {int(x)}" if pd.notna(x) and isinstance(x, (int, float)) else str(x)
    )
    
    bars_dist = sns.barplot(
        x="review_score",
        y="percentage",
        hue="delivery_status",
        data=rating_melted,
        palette=palette_status,
        ax=axes_deliv[1]
    )
    axes_deliv[1].set_title("Distribusi Rating Bintang 1 - 5 (%)", fontsize=13, fontweight="bold", pad=12)
    axes_deliv[1].set_xlabel("Rating Bintang", fontsize=11)
    axes_deliv[1].set_ylabel("Persentase Pelanggan (%)", fontsize=11)
    axes_deliv[1].set_ylim(0, 85)
    axes_deliv[1].legend(title="Status Pengiriman")
    
    for bar in bars_dist.patches:
        h = bar.get_height()
        if pd.notna(h) and h > 0:
            axes_deliv[1].annotate(
                f"{h:.1f}%",
                (bar.get_x() + bar.get_width() / 2., h),
                ha="center", va="bottom",
                xytext=(0, 4), textcoords="offset points",
                fontsize=8, fontweight="bold"
            )
            
    plt.tight_layout()
    st.pyplot(fig_deliv)
    
    st.info(
        "💡 **Insight Kritis:** Pesanan yang terlambat mengalami lonjakan drastis pada ulasan bintang 1 (>55%), "
        "sedangkan pesanan tepat waktu didominasi oleh rating bintang 5 (>70%). Hal ini membuktikan bahwa efisiensi logistik "
        "merupakan pilar utama pembentuk kepuasan pelanggan."
    )

# ------------------------------------------------------------------------------
# TAB 3: ANALISIS RFM
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("Analisis RFM (Recency, Frequency, Monetary)")
    st.markdown("Mengelompokkan pelanggan berdasarkan kapan terakhir bertransaksi, frekuensi pesanan, dan total nilai belanja.")
    
    rfm_df = create_rfm_df(filtered_df)
    
    col_rfm1, col_rfm2, col_rfm3 = st.columns(3)
    with col_rfm1:
        st.metric("Rata-rata Recency", f"{rfm_df['recency'].mean():.1f} Hari")
    with col_rfm2:
        st.metric("Rata-rata Frekuensi", f"{rfm_df['frequency'].mean():.2f} Order")
    with col_rfm3:
        st.metric("Rata-rata Monetary", f"R$ {rfm_df['monetary'].mean():,.2f}")
        
    fig_rfm, axes_rfm = plt.subplots(nrows=1, ncols=3, figsize=(20, 5.5))
    colors_rfm = ["#1A5276", "#2980B9", "#5DADE2", "#85C1E9", "#AED6F1"]
    
    # 1. Recency
    top_rec = rfm_df.sort_values(by="recency", ascending=True).head(5).copy()
    top_rec["short_id"] = top_rec["customer_unique_id"].apply(lambda cid: f"...{str(cid)[-6:]}")
    sns.barplot(
        y="recency",
        x="short_id",
        data=top_rec,
        hue="short_id",
        palette=colors_rfm[:len(top_rec)],
        legend=False,
        ax=axes_rfm[0]
    )
    axes_rfm[0].set_title("Best Recency (Hari Terendah)", fontsize=12, fontweight="bold")
    axes_rfm[0].set_ylabel("Recency (Hari)")
    axes_rfm[0].set_xlabel("Customer ID (Truncated)")
    axes_rfm[0].tick_params(axis='x', rotation=45)
    for b in axes_rfm[0].patches:
        h = b.get_height()
        if pd.notna(h):
            axes_rfm[0].annotate(f"{h:.0f} d", (b.get_x() + b.get_width() / 2., h),
                                 ha="center", va="bottom", fontsize=10, fontweight="bold")
                             
    # 2. Frequency
    top_frq = rfm_df.sort_values(by="frequency", ascending=False).head(5).copy()
    top_frq["short_id"] = top_frq["customer_unique_id"].apply(lambda cid: f"...{str(cid)[-6:]}")
    sns.barplot(
        y="frequency",
        x="short_id",
        data=top_frq,
        hue="short_id",
        palette=colors_rfm[:len(top_frq)],
        legend=False,
        ax=axes_rfm[1]
    )
    axes_rfm[1].set_title("Best Frequency (Order Terbanyak)", fontsize=12, fontweight="bold")
    axes_rfm[1].set_ylabel("Jumlah Order Unik")
    axes_rfm[1].set_xlabel("Customer ID (Truncated)")
    axes_rfm[1].tick_params(axis='x', rotation=45)
    for b in axes_rfm[1].patches:
        h = b.get_height()
        if pd.notna(h):
            axes_rfm[1].annotate(f"{h:.0f}", (b.get_x() + b.get_width() / 2., h),
                                 ha="center", va="bottom", fontsize=10, fontweight="bold")
                             
    # 3. Monetary
    top_mon = rfm_df.sort_values(by="monetary", ascending=False).head(5).copy()
    top_mon["short_id"] = top_mon["customer_unique_id"].apply(lambda cid: f"...{str(cid)[-6:]}")
    sns.barplot(
        y="monetary",
        x="short_id",
        data=top_mon,
        hue="short_id",
        palette=colors_rfm[:len(top_mon)],
        legend=False,
        ax=axes_rfm[2]
    )
    axes_rfm[2].set_title("Best Monetary (Belanja Terbesar)", fontsize=12, fontweight="bold")
    axes_rfm[2].set_ylabel("Total Pengeluaran (BRL)")
    axes_rfm[2].set_xlabel("Customer ID (Truncated)")
    axes_rfm[2].tick_params(axis='x', rotation=45)
    for b in axes_rfm[2].patches:
        h = b.get_height()
        if pd.notna(h):
            axes_rfm[2].annotate(f"R$ {h:,.0f}", (b.get_x() + b.get_width() / 2., h),
                                 ha="center", va="bottom", fontsize=9, fontweight="bold")
                             
    plt.tight_layout()
    st.pyplot(fig_rfm)

# ------------------------------------------------------------------------------
# TAB 4: DEMOGRAFI GEOSPASIAL
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("Distribusi Geospasial Pelanggan Berdasarkan Negara Bagian")
    st.markdown("Peta sebaran volume transaksi per negara bagian (*state*) di Brazil.")
    
    bystate_df = create_bystate_df(filtered_df)
    top_10_states = bystate_df.head(10).copy()
    
    fig_geo, ax_geo = plt.subplots(figsize=(14, 5.5))
    colors_geo = ["#1A5276" if i < 3 else "#5DADE2" for i in range(len(top_10_states))]
    
    bars_geo = sns.barplot(
        x="customer_state",
        y="order_count",
        data=top_10_states,
        hue="customer_state",
        palette=colors_geo,
        legend=False,
        ax=ax_geo
    )
    ax_geo.set_title("Top 10 Negara Bagian Berdasarkan Jumlah Pesanan", fontsize=13, fontweight="bold", pad=12)
    ax_geo.set_xlabel("Negara Bagian (State Code)", fontsize=11)
    ax_geo.set_ylabel("Jumlah Pesanan", fontsize=11)
    
    for bar in bars_geo.patches:
        h = bar.get_height()
        if pd.notna(h) and h > 0:
            ax_geo.annotate(
                f"{h:,}",
                (bar.get_x() + bar.get_width() / 2., h),
                ha="center", va="bottom",
                fontsize=10, fontweight="bold"
            )
        
    plt.tight_layout()
    st.pyplot(fig_geo)
    
    st.caption("Keterangan kode negara bagian teratas: SP (São Paulo), RJ (Rio de Janeiro), MG (Minas Gerais), RS (Rio Grande do Sul), PR (Paraná).")

# ==============================================================================
# 7. Footer
# ==============================================================================
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "E-Commerce Data Analysis Dashboard | Dicoding Academy © 2026 Gabriel Jel Blessly Aipassa"
    "</div>",
    unsafe_allow_html=True
)