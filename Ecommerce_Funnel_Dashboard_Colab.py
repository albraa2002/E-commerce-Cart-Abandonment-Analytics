# ============================================================
#  E-COMMERCE FUNNEL & CART ABANDONMENT DASHBOARD
#  Single-Cell Google Colab Script  |  Author: Senior E-com Analyst
# ============================================================

# ── 0. Install / Import ──────────────────────────────────────
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from google.colab import files

np.random.seed(42)

# ============================================================
# STEP 1 ── GENERATE REALISTIC SESSION DATA (20,000 rows)
# ============================================================

N = 20_000
stages = ['1_Visit', '2_Product_View', '3_Add_to_Cart', '4_Checkout_Initiated', '5_Purchase']

# --- Traffic Source (Paid Social drives most traffic) --------
source_probs = [0.30, 0.35, 0.15, 0.20]        # Organic, Paid Social, Influencer, Direct
sources       = ['Organic Search', 'Paid Social', 'Influencer Campaign', 'Direct']
traffic       = np.random.choice(sources, size=N, p=source_probs)

# --- Device (Mobile = 80 %) ----------------------------------
device = np.random.choice(['Mobile', 'Desktop'], size=N, p=[0.80, 0.20])

# --- Farthest Stage with source & device logic ---------------
# Base stage probabilities aligned to: 40/30/15/10/5
# Adjust per-source and per-device to honour business rules.

def assign_stage(src, dev):
    """Return a stage string given traffic source and device."""
    # Base weights for stages 1-5
    w = np.array([0.40, 0.30, 0.15, 0.10, 0.05], dtype=float)

    # Source adjustments
    if src == 'Organic Search':
        # Better conversion: shift weight from Visit/PV toward later stages
        w += np.array([-0.05, -0.03,  0.02,  0.03,  0.03])
    elif src == 'Paid Social':
        # More bounces, highest cart abandonment (low Purchase weight)
        w += np.array([ 0.06,  0.04,  0.01, -0.04, -0.07])
    elif src == 'Influencer Campaign':
        # Moderate funnel, highest AOV (handled in order value)
        w += np.array([-0.02,  0.00,  0.02,  0.00,  0.00])
    # Direct: use base

    # Device adjustments (Mobile drops off more at Checkout)
    if dev == 'Mobile':
        w += np.array([ 0.02,  0.01,  0.01, -0.02, -0.02])
    # Desktop: keep as is

    # Clip & normalise
    w = np.clip(w, 0.005, None)
    w /= w.sum()
    return np.random.choice(stages, p=w)

stage_col = np.array([assign_stage(s, d) for s, d in zip(traffic, device)])

# --- Order Value (EGP) ---------------------------------------
def order_value(stage, src):
    if stage != '5_Purchase':
        return 0.0
    if src == 'Influencer Campaign':
        return np.random.uniform(900, 3500)   # Highest AOV
    elif src == 'Organic Search':
        return np.random.uniform(400, 2500)
    elif src == 'Paid Social':
        return np.random.uniform(300, 1800)
    else:                                      # Direct
        return np.random.uniform(350, 2200)

order_values = np.array([order_value(st, sr) for st, sr in zip(stage_col, traffic)])

# --- Dates (Jan–Dec 2025, slight seasonal uplift in Nov/Dec) --
date_start = pd.Timestamp('2025-01-01')
date_end   = pd.Timestamp('2025-12-31')
total_days = (date_end - date_start).days + 1

# Weight: normal traffic Jan-Oct, +30 % Nov, +50 % Dec
day_index   = np.arange(total_days)
day_weights = np.ones(total_days, dtype=float)
for i, d in enumerate(pd.date_range(date_start, date_end)):
    if d.month == 11:
        day_weights[i] = 1.30
    elif d.month == 12:
        day_weights[i] = 1.50
day_weights /= day_weights.sum()

random_days  = np.random.choice(day_index, size=N, p=day_weights)
dates        = pd.to_datetime(date_start) + pd.to_timedelta(random_days, unit='D')

# --- Assemble DataFrame --------------------------------------
df = pd.DataFrame({
    'Session_ID'            : [f'SID-{str(i).zfill(6)}' for i in range(N)],
    'Date'                  : dates,
    'Traffic_Source'        : traffic,
    'Device'                : device,
    'Farthest_Stage_Reached': stage_col,
    'Order_Value_EGP'       : order_values,
})

df['Date'] = pd.to_datetime(df['Date'])
print(f"✅ Dataset generated: {df.shape[0]:,} rows × {df.shape[1]} columns")
print(df['Farthest_Stage_Reached'].value_counts().sort_index())

# ============================================================
# STEP 2 ── CALCULATE KPIs
# ============================================================

total_sessions  = len(df)
total_purchases = (df['Farthest_Stage_Reached'] == '5_Purchase').sum()
reached_cart    = df['Farthest_Stage_Reached'].isin(
                      ['3_Add_to_Cart', '4_Checkout_Initiated', '5_Purchase']).sum()

conversion_rate    = total_purchases / total_sessions * 100
cart_abandon_rate  = (1 - total_purchases / reached_cart) * 100
aov                = df.loc[df['Order_Value_EGP'] > 0, 'Order_Value_EGP'].mean()

print(f"\n📊 KPIs")
print(f"   Overall Conversion Rate  : {conversion_rate:.2f}%")
print(f"   Cart Abandonment Rate    : {cart_abandon_rate:.2f}%")
print(f"   Average Order Value (AOV): {aov:,.0f} EGP")

# ============================================================
# STEP 3 ── CREATE 3 INDEPENDENT PLOTLY FIGURES
# ============================================================

# ── Palette ──────────────────────────────────────────────────
TEAL        = '#00B4A6'
CORAL       = '#FF6B6B'
INDIGO      = '#3D3D8F'
TEAL_LIGHT  = '#80DDD8'
CORAL_LIGHT = '#FFB3B3'
BG          = '#f9fafb'
CARD_BG     = '#ffffff'
TEXT_DARK   = '#1a1a2e'
TEXT_MID    = '#4a4a6a'

plotly_layout_base = dict(
    paper_bgcolor = CARD_BG,
    plot_bgcolor  = CARD_BG,
    font          = dict(family='Segoe UI, sans-serif', color=TEXT_DARK),
    margin        = dict(l=30, r=30, t=50, b=30),
)

# ── Figure 1: Funnel Chart ────────────────────────────────────
stage_order  = stages
stage_labels = ['Visit', 'Product View', 'Add to Cart', 'Checkout Initiated', 'Purchase']
stage_counts = [
    (df['Farthest_Stage_Reached'] >= s).sum() if False else
    df['Farthest_Stage_Reached'].isin(stages[i:]).sum()
    for i, s in enumerate(stage_order)
]

fig_funnel = go.Figure(go.Funnel(
    y          = stage_labels,
    x          = stage_counts,
    textinfo   = 'value+percent initial',
    textfont   = dict(size=13, color='white'),
    marker     = dict(
        color = [TEAL, TEAL_LIGHT, CORAL_LIGHT, CORAL, INDIGO],
        line  = dict(width=2, color='white'),
    ),
    connector  = dict(line=dict(color='#e0e0e0', width=1)),
    hovertemplate = '<b>%{y}</b><br>Sessions: %{x:,}<br>% of Total: %{percentInitial:.1%}<extra></extra>',
))

fig_funnel.update_layout(
    **plotly_layout_base,
    title = dict(text='<b>Conversion Funnel</b>', font=dict(size=16, color=TEXT_DARK), x=0.5),
)

# ── Figure 2: Cart Abandonment Rate by Traffic Source ────────
cart_df = (
    df[df['Farthest_Stage_Reached'].isin(['3_Add_to_Cart','4_Checkout_Initiated','5_Purchase'])]
    .groupby('Traffic_Source')
    .agg(
        reached_cart = ('Session_ID', 'count'),
        purchased    = ('Farthest_Stage_Reached', lambda x: (x == '5_Purchase').sum())
    )
    .assign(abandon_rate = lambda d: (1 - d['purchased'] / d['reached_cart']) * 100)
    .sort_values('abandon_rate', ascending=False)
    .reset_index()
)

bar_colors = [CORAL if src == 'Paid Social' else TEAL for src in cart_df['Traffic_Source']]

fig_abandonment = go.Figure(go.Bar(
    x             = cart_df['Traffic_Source'],
    y             = cart_df['abandon_rate'],
    marker_color  = bar_colors,
    text          = cart_df['abandon_rate'].apply(lambda v: f'{v:.1f}%'),
    textposition  = 'outside',
    textfont      = dict(size=12, color=TEXT_DARK),
    hovertemplate = '<b>%{x}</b><br>Abandonment Rate: %{y:.1f}%<extra></extra>',
))

fig_abandonment.update_layout(
    **plotly_layout_base,
    title    = dict(text='<b>Cart Abandonment Rate by Traffic Source</b>',
                    font=dict(size=16, color=TEXT_DARK), x=0.5),
    yaxis    = dict(title='Abandonment Rate (%)', ticksuffix='%', gridcolor='#f0f0f0',
                    range=[0, cart_df['abandon_rate'].max() * 1.15]),
    xaxis    = dict(title=''),
    bargap   = 0.35,
    showlegend = False,
)

# Add annotation for Paid Social bar
paid_row = cart_df[cart_df['Traffic_Source'] == 'Paid Social'].iloc[0]
fig_abandonment.add_annotation(
    x         = paid_row['Traffic_Source'],
    y         = paid_row['abandon_rate'] + 3,
    text      = '⚠️ Highest',
    showarrow = False,
    font      = dict(size=11, color=CORAL),
)

# ── Figure 3: Monthly Revenue Trend ──────────────────────────
monthly_rev = (
    df[df['Order_Value_EGP'] > 0]
    .assign(Month = df['Date'].dt.to_period('M'))
    .groupby('Month')['Order_Value_EGP']
    .sum()
    .reset_index()
)
monthly_rev['Month_str'] = monthly_rev['Month'].dt.strftime('%b %Y')
monthly_rev['Month_ord'] = monthly_rev['Month'].apply(lambda p: p.ordinal)
monthly_rev = monthly_rev.sort_values('Month_ord')

fig_revenue = go.Figure()

# Filled area
fig_revenue.add_trace(go.Scatter(
    x          = monthly_rev['Month_str'],
    y          = monthly_rev['Order_Value_EGP'],
    fill       = 'tozeroy',
    fillcolor  = f'rgba(0,180,166,0.12)',
    line       = dict(color=TEAL, width=3),
    mode       = 'lines+markers',
    marker     = dict(size=8, color=INDIGO, line=dict(width=2, color='white')),
    hovertemplate = '<b>%{x}</b><br>Revenue: %{y:,.0f} EGP<extra></extra>',
    name       = 'Monthly Revenue',
))

# Add Nov/Dec annotation
for month_lbl, label_txt, color in [
    (monthly_rev[monthly_rev['Month_str'].str.startswith('Nov')]['Month_str'].values[0] if any(monthly_rev['Month_str'].str.startswith('Nov')) else None, 'Black Friday 🛒', CORAL),
    (monthly_rev[monthly_rev['Month_str'].str.startswith('Dec')]['Month_str'].values[0] if any(monthly_rev['Month_str'].str.startswith('Dec')) else None, 'Holiday Peak 🎄', INDIGO),
]:
    if month_lbl:
        rev_val = monthly_rev.loc[monthly_rev['Month_str'] == month_lbl, 'Order_Value_EGP'].values[0]
        fig_revenue.add_annotation(
            x=month_lbl, y=rev_val,
            text=label_txt, showarrow=True, arrowhead=2,
            ax=0, ay=-40, font=dict(size=11, color=color),
            arrowcolor=color,
        )

fig_revenue.update_layout(
    **plotly_layout_base,
    title   = dict(text='<b>Monthly Revenue Trend (2025)</b>',
                   font=dict(size=16, color=TEXT_DARK), x=0.5),
    yaxis   = dict(title='Revenue (EGP)', tickformat=',.0f', gridcolor='#f0f0f0'),
    xaxis   = dict(title='', tickangle=-30),
    showlegend = False,
)

print("\n✅ All 3 Plotly figures created.")

# ============================================================
# STEP 4 ── BUILD HTML DASHBOARD
# ============================================================

funnel_html      = fig_funnel.to_html(full_html=False, include_plotlyjs=False)
abandonment_html = fig_abandonment.to_html(full_html=False, include_plotlyjs=False)
revenue_html     = fig_revenue.to_html(full_html=False, include_plotlyjs=False)

html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>E-Commerce Funnel & Cart Abandonment Dashboard</title>
  <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Syne:wght@700;800&display=swap" rel="stylesheet"/>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --teal:   #00B4A6;
      --coral:  #FF6B6B;
      --indigo: #3D3D8F;
      --bg:     #f0f4f8;
      --card:   #ffffff;
      --shadow: 0 4px 20px rgba(0,0,0,0.07);
      --radius: 16px;
      --text:   #1a1a2e;
      --muted:  #64748b;
    }}

    body {{
      font-family: 'DM Sans', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
    }}

    /* ── Header ── */
    header {{
      background: linear-gradient(135deg, var(--indigo) 0%, #1a1a4e 100%);
      padding: 28px 40px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 4px 24px rgba(61,61,143,0.3);
    }}
    header h1 {{
      font-family: 'Syne', sans-serif;
      font-size: 1.65rem;
      font-weight: 800;
      color: #fff;
      letter-spacing: -0.5px;
    }}
    header span.badge {{
      background: rgba(255,255,255,0.15);
      color: #fff;
      font-size: 0.78rem;
      font-weight: 500;
      padding: 5px 14px;
      border-radius: 20px;
      border: 1px solid rgba(255,255,255,0.25);
    }}

    /* ── Main wrapper ── */
    .wrapper {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 32px 24px 48px;
      display: flex;
      flex-direction: column;
      gap: 28px;
    }}

    /* ── Section label ── */
    .section-label {{
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 1.8px;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 8px;
    }}

    /* ── KPI Cards Row ── */
    .kpi-row {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
    }}
    .kpi-card {{
      background: var(--card);
      border-radius: var(--radius);
      padding: 24px 28px;
      box-shadow: var(--shadow);
      position: relative;
      overflow: hidden;
      transition: transform .2s ease, box-shadow .2s ease;
    }}
    .kpi-card:hover {{
      transform: translateY(-3px);
      box-shadow: 0 8px 28px rgba(0,0,0,0.11);
    }}
    .kpi-card::before {{
      content: '';
      position: absolute;
      top: 0; left: 0;
      width: 5px; height: 100%;
      border-radius: var(--radius) 0 0 var(--radius);
    }}
    .kpi-card.teal::before   {{ background: var(--teal);   }}
    .kpi-card.coral::before  {{ background: var(--coral);  }}
    .kpi-card.indigo::before {{ background: var(--indigo); }}

    .kpi-label {{
      font-size: 0.82rem;
      font-weight: 500;
      color: var(--muted);
      margin-bottom: 10px;
    }}
    .kpi-value {{
      font-family: 'Syne', sans-serif;
      font-size: 2.4rem;
      font-weight: 800;
      line-height: 1;
    }}
    .kpi-card.teal   .kpi-value {{ color: var(--teal);   }}
    .kpi-card.coral  .kpi-value {{ color: var(--coral);  }}
    .kpi-card.indigo .kpi-value {{ color: var(--indigo); }}

    .kpi-sub {{
      font-size: 0.78rem;
      color: var(--muted);
      margin-top: 8px;
    }}
    .kpi-icon {{
      position: absolute;
      top: 20px; right: 22px;
      font-size: 1.8rem;
      opacity: 0.18;
    }}

    /* ── Chart Cards ── */
    .chart-card {{
      background: var(--card);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 12px 8px 4px;
      transition: transform .2s ease, box-shadow .2s ease;
    }}
    .chart-card:hover {{
      transform: translateY(-2px);
      box-shadow: 0 8px 28px rgba(0,0,0,0.10);
    }}

    /* ── Middle Row (2-col) ── */
    .mid-row {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }}

    /* ── Bottom Row (full-width) ── */
    .bottom-row {{ display: grid; grid-template-columns: 1fr; }}

    /* ── Footer ── */
    footer {{
      text-align: center;
      font-size: 0.75rem;
      color: var(--muted);
      padding: 16px 0 8px;
      border-top: 1px solid #e2e8f0;
      margin-top: 8px;
    }}

    @media (max-width: 900px) {{
      .kpi-row  {{ grid-template-columns: 1fr; }}
      .mid-row  {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>

  <header>
    <h1>🛒 E-Commerce Funnel &amp; Cart Abandonment Dashboard</h1>
    <span class="badge">📅 FY 2025 &nbsp;|&nbsp; 20,000 Sessions</span>
  </header>

  <div class="wrapper">

    <!-- KPI Row -->
    <div>
      <p class="section-label">Key Performance Indicators</p>
      <div class="kpi-row">

        <div class="kpi-card teal">
          <span class="kpi-icon">📈</span>
          <div class="kpi-label">Overall Conversion Rate</div>
          <div class="kpi-value">{conversion_rate:.2f}%</div>
          <div class="kpi-sub">Sessions that reached Purchase</div>
        </div>

        <div class="kpi-card coral">
          <span class="kpi-icon">🛒</span>
          <div class="kpi-label">Cart Abandonment Rate</div>
          <div class="kpi-value">{cart_abandon_rate:.2f}%</div>
          <div class="kpi-sub">Lost at or after Add-to-Cart stage</div>
        </div>

        <div class="kpi-card indigo">
          <span class="kpi-icon">💳</span>
          <div class="kpi-label">Average Order Value (AOV)</div>
          <div class="kpi-value">{aov:,.0f} EGP</div>
          <div class="kpi-sub">Mean revenue per completed order</div>
        </div>

      </div>
    </div>

    <!-- Middle Row: Funnel + Abandonment -->
    <div>
      <p class="section-label">Funnel Performance &amp; Channel Analysis</p>
      <div class="mid-row">
        <div class="chart-card">{funnel_html}</div>
        <div class="chart-card">{abandonment_html}</div>
      </div>
    </div>

    <!-- Bottom Row: Revenue Trend -->
    <div>
      <p class="section-label">Revenue Trend</p>
      <div class="bottom-row">
        <div class="chart-card">{revenue_html}</div>
      </div>
    </div>

    <footer>
      Built with Python · Pandas · Plotly &nbsp;|&nbsp;
      Synthetic data for analytical demonstration &nbsp;|&nbsp;
      E-Commerce Analytics Dashboard © 2025
    </footer>

  </div>
</body>
</html>"""

print("✅ HTML template assembled.")

# ============================================================
# STEP 5 ── EXPORT & AUTO-DOWNLOAD
# ============================================================

OUTPUT_FILE = 'Ecommerce_Funnel_Dashboard.html'

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write(html_template)

print(f"\n✅ Dashboard saved to '{OUTPUT_FILE}'")
print("⬇️  Starting download …")

files.download(OUTPUT_FILE)

print("\n🎉 Done! Your dashboard is ready.")
