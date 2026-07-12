import streamlit as st
import yfinance as yf

st.title("📈 Stock Price Viewer")

ticker = st.text_input("Enter a stock ticker (e.g. AAPL, MSFT, TSLA)")

if ticker:
    stock = yf.Ticker(ticker)
    data = stock.history(period="1d")

    if data.empty:
        st.error(f"Could not find any data for '{ticker}'. Check the ticker and try again.")
    else:
        price = data["Close"].iloc[-1]
        st.metric(label=f"{ticker.upper()} current price", value=f"${price:,.2f}")
