import os
import logging
import aiohttp
import asyncio
from flask import Flask, render_template, request, send_file
import pandas as pd

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the async functions
async def fetch_address_info(session, address, max_retries=3):
    headers = {
        'Accept': '*/*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'X-OYL-API-KEY': 'd6aebfed1769128379aca7d215f0b689',
    }
    json_data = {'address': address}

    for attempt in range(max_retries):
        try:
            async with session.post(
                'https://mainnet-api.oyl.gg/get-whitelist-leaderboard', 
                headers=headers, 
                json=json_data
            ) as response:
                if response.status == 200:
                    logging.info(f"Response received for address {address}")
                    return await response.json()
                
            await asyncio.sleep(1)
            logging.info(f"Request made for address {address}: Status Code {response.status}")

        except Exception as e:
            logging.error(f"Attempt {attempt + 1} failed for address {address}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
                continue
            return None

    return None

async def process_addresses(addresses):
    data = []
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_address_info(session, address) for address in addresses]
        responses = await asyncio.gather(*tasks)

        for address, info in zip(addresses, responses):
            if info:
                data.append({
                    'address': address,
                    'wallet_rank': info.get('walletRank'),
                    'whale': info.get('whale'),
                    'priority': info.get('priority'),
                    'fatMeter': info.get('fatMeter'),
                    'guaranteedMint': info.get('guaranteedMint'),
                })
    
    return data

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
async def process():
    if request.method == 'POST':
        addresses_text = request.form['addresses']
        addresses = addresses_text.splitlines()

        # Process addresses asynchronously
        data = await process_addresses(addresses)

        # Convert the data list to a DataFrame and save it to Excel
        df = pd.DataFrame(data)
        output_excel = '/tmp/results.xlsx'  # Save in temporary folder for Vercel deployment
        try:
            df.to_excel(output_excel, index=False)
            logging.info(f"Data successfully saved to {output_excel}")
        except Exception as e:
            logging.error(f"Failed to save data to {output_excel}: {e}")
            return "Error saving data", 500

        return send_file(output_excel, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)