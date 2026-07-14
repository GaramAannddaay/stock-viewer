import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="Stock Price Viewer", page_icon="📈", layout="wide")


def money(value):
    """Turn a big number into $1.23T / $4.56B / $7.89M style text."""
    if value is None:
        return "N/A"
    for unit, size in [("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)]:
        if abs(value) >= size:
            return f"${value / size:,.2f}{unit}"
    return f"${value:,.2f}"


def num(value, suffix=""):
    if value is None:
        return "N/A"
    return f"{value:,.2f}{suffix}"


def volume(value):
    if value is None:
        return "N/A"
    for unit, size in [("B", 1e9), ("M", 1e6), ("K", 1e3)]:
        if abs(value) >= size:
            return f"{value / size:,.2f}{unit}"
    return f"{value:,.0f}"


PERIODS = {
    "1 Month": "1mo",
    "3 Months": "3mo",
    "6 Months": "6mo",
    "1 Year": "1y",
    "3 Years": "3y",
    "5 Years": "5y",
}

# ------------------------------------------------------------------ Sidebar
st.sidebar.title("📈 Stock Price Viewer")
st.sidebar.caption("Enter a ticker to explore price, metrics and news.")
ticker = st.sidebar.text_input("Stock ticker", value="AAPL", placeholder="e.g. AAPL, MSFT, TSLA")
choice = st.sidebar.selectbox("Chart time period", list(PERIODS.keys()), index=3)

st.sidebar.divider()
st.sidebar.caption("Compare up to 3 stocks (normalized).")
_popular = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"]
_options = sorted(set(_popular + ([ticker.upper()] if ticker else [])))
_default = [ticker.upper()] if ticker and ticker.upper() in _options else []
compare = st.sidebar.multiselect(
    "Compare stocks",
    options=_options,
    default=_default,
    max_selections=3,
    accept_new_options=True,
)

# ------------------------------------------------------------------ Main
st.title("Stock Price Viewer")

if not ticker:
    st.info("👈 Enter a stock ticker in the sidebar to get started.")
    st.stop()

stock = yf.Ticker(ticker)
info = stock.info
history = stock.history(period=PERIODS[choice])

if history.empty:
    st.error(f"Could not find any data for '{ticker}'. Check the ticker and try again.")
    st.stop()

# One period history powers both the chart and the period-aware metrics.
price = history["Close"].iloc[-1]
prev_close = history["Close"].iloc[-2] if len(history) >= 2 else price
start_close = history["Close"].iloc[0]

day_change = price - prev_close
day_pct = (day_change / prev_close * 100) if prev_close else 0
period_change = price - start_close
period_pct = (period_change / start_close * 100) if start_close else 0

company = info.get("longName") or info.get("shortName") or ticker.upper()

left, right = st.columns([1, 1], gap="large")

# ----------------------------------------------------- Left: price + metrics
with left:
    st.subheader(company)
    st.metric(
        label="Current Price",
        value=f"${price:,.2f}",
        delta=f"{day_change:+,.2f} ({day_pct:+.2f}%) today",
    )

    st.markdown("**Valuation**")
    v = st.columns(2)
    v[0].metric("Market Cap", money(info.get("marketCap")))
    v[1].metric("P/E Ratio", num(info.get("trailingPE")))
    v2 = st.columns(2)
    v2[0].metric("EV / EBITDA", num(info.get("enterpriseToEbitda")))
    v2[1].metric("Dividend Yield", num(info.get("dividendYield"), "%"))

    st.markdown(f"**Performance · {choice}**")
    p = st.columns(2)
    p[0].metric("Period Return", f"{period_pct:+.2f}%", delta=f"${period_change:+,.2f}")
    p[1].metric("Period High", num(history["High"].max()))
    p2 = st.columns(2)
    p2[0].metric("Period Low", num(history["Low"].min()))
    p2[1].metric("52-Week High", num(info.get("fiftyTwoWeekHigh")))

    st.markdown(f"**Volume · {choice}**")
    vol = st.columns(2)
    vol[0].metric("Average Volume", volume(history["Volume"].mean()))
    vol[1].metric("Highest Volume", volume(history["Volume"].max()))
    vol2 = st.columns(2)
    vol2[0].metric("Lowest Volume", volume(history["Volume"].min()))
    vol2[1].metric("52-Week Low", num(info.get("fiftyTwoWeekLow")))

# ------------------------------------------------------ Right: price chart
with right:
    st.subheader(f"Price Performance · {choice}")
    fig = go.Figure()
    line_color = "#26A65B" if period_change >= 0 else "#E74C3C"
    fill_color = "rgba(38, 166, 91, 0.12)" if period_change >= 0 else "rgba(231, 76, 60, 0.12)"
    fig.add_trace(
        go.Scatter(
            x=history.index,
            y=history["Close"],
            mode="lines",
            name="Close",
            line=dict(color=line_color, width=2),
            fill="tozeroy",
            fillcolor=fill_color,
        )
    )
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Price ($)",
        hovermode="x unified",
        template="plotly_white",
        height=460,
        margin=dict(t=20, b=40, l=40, r=20),
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------- Comparison
st.divider()
st.subheader(f"Compare Stocks · Normalized to 100 · {choice}")

symbols = list(dict.fromkeys(s.strip().upper() for s in compare if s.strip()))
if len(symbols) < 2:
    st.info("Select at least 2 stocks in the sidebar to compare their performance.")
else:
    cfig = go.Figure()
    plotted = 0
    for sym in symbols:
        h = yf.Ticker(sym).history(period=PERIODS[choice])
        if h.empty:
            st.warning(f"No data for '{sym}' — skipping.")
            continue
        # Index every stock to 100 at the start so % moves are directly comparable.
        norm = h["Close"] / h["Close"].iloc[0] * 100
        cfig.add_trace(go.Scatter(x=h.index, y=norm, mode="lines", name=sym, line=dict(width=2)))
        plotted += 1

    if plotted:
        cfig.add_hline(y=100, line_dash="dash", line_color="gray", opacity=0.5)
        cfig.update_layout(
            xaxis_title="Date",
            yaxis_title="Normalized price (start = 100)",
            hovermode="x unified",
            template="plotly_white",
            height=460,
            margin=dict(t=20, b=40, l=40, r=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        st.plotly_chart(cfig, use_container_width=True)

# ---------------------------------------------------------------- News
st.divider()
st.subheader("Latest News")

articles = stock.news or []
if not articles:
    st.info("No recent news found for this stock.")
else:
    for item in articles:
        content = item.get("content", {})
        title = content.get("title")
        url = (content.get("canonicalUrl") or content.get("clickThroughUrl") or {}).get("url")
        source = (content.get("provider") or {}).get("displayName", "")
        date = (content.get("pubDate") or "")[:10]

        if not title:
            continue

        if url:
            st.markdown(f"**[{title}]({url})**")
        else:
            st.markdown(f"**{title}**")

        caption = " · ".join(part for part in [source, date] if part)
        if caption:
            st.caption(caption)
