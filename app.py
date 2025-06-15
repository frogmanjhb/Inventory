import streamlit as st
import pandas as pd
import requests
import io
import time

FOREX_API = 'https://api.frankfurter.app/latest?from=USD&to=ZAR'

def get_usd_to_zar():
    response = requests.get(FOREX_API)
    try:
        data = response.json()
        return data['rates']['ZAR']
    except Exception as e:
        st.error(f"Error fetching forex rate: {e}\nResponse: {response.text}")
        return None

def get_card_data(card_name):
    url = f"https://api.scryfall.com/cards/named?exact={card_name}"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    return response.json()

def enrich_card(card_name, quantity, usd_to_zar):
    data = get_card_data(card_name)
    if not data:
        return {
            'Card Name': card_name,
            'Set': '',
            'Rarity': '',
            'Color': '',
            'Tags': '',
            'USD Price': '',
            'ZAR Price': '',
            'Quantity': quantity
        }
    set_name = data.get('set', '')
    rarity = data.get('rarity', '')
    colors = ','.join(data.get('colors', [])) or 'Colorless'
    card_types = data.get('type_line', '')
    tags = f"Set: {set_name}, Rarity: {rarity}, Color: {colors}, Types: {card_types}"
    usd_price = data.get('prices', {}).get('usd')
    if usd_price is None:
        usd_price = 0.0
    else:
        usd_price = float(usd_price)
    zar_price = round(usd_price * usd_to_zar, 2)
    return {
        'Card Name': card_name,
        'Set': set_name,
        'Rarity': rarity,
        'Color': colors,
        'Tags': tags,
        'USD Price': usd_price,
        'ZAR Price': zar_price,
        'Quantity': quantity
    }

st.title("MTG Inventory Manager")

st.write("""
Upload a CSV with your card names and quantities.  
The app will fetch card details from Scryfall, add tags, and price them in ZAR.
""")

uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    if 'Card Name' not in df.columns:
        st.error("CSV must have a 'Card Name' column.")
    else:
        st.success("CSV loaded! Processing...")
        usd_to_zar = get_usd_to_zar()
        if usd_to_zar is None:
            st.stop()  # Stop the app if the rate couldn't be fetched
        st.write(f"Current USD to ZAR rate: {usd_to_zar:.2f}")

        enriched = []
        progress = st.progress(0)
        for idx, row in df.iterrows():
            card_name = row['Card Name']
            quantity = row.get('Quantity', 1)
            enriched.append(enrich_card(card_name, quantity, usd_to_zar))
            progress.progress((idx + 1) / len(df))
            time.sleep(0.1)  # Be nice to Scryfall

        out_df = pd.DataFrame(enriched)
        st.write("Preview of results:", out_df.head())

        # Download button
        csv_buffer = io.StringIO()
        out_df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="Download enriched CSV",
            data=csv_buffer.getvalue(),
            file_name="enriched_cards.csv",
            mime="text/csv"
        )