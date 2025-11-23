#!/usr/bin/env python3
"""
Test script to verify stock tickers are available in Twelve Data API
"""

import os
import sys
import requests

# Your tickers from stocks.csv
TICKERS = ["CRM", "AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "AMD"]

def test_tickers():
    """Test if all tickers are available in Twelve Data"""

    # Get API key from environment
    api_key = os.getenv("TWELVE_DATA_API_KEY")

    if not api_key:
        print("❌ ERROR: TWELVE_DATA_API_KEY not found in environment")
        print("\nTo set it:")
        print("  export TWELVE_DATA_API_KEY='your_api_key_here'")
        return False

    print(f"Testing {len(TICKERS)} tickers with Twelve Data API...\n")

    # Test batch request (all symbols at once)
    symbols_str = ",".join(TICKERS)
    url = f"https://api.twelvedata.com/quote?symbol={symbols_str}&apikey={api_key}"

    try:
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            print(f"❌ HTTP Error {response.status_code}")
            print(f"Response: {response.text}")
            return False

        data = response.json()

        # Handle both single and batch responses
        quotes = data if isinstance(data, list) else [data]

        print("Results:")
        print("-" * 60)

        success_count = 0
        failed_symbols = []

        for quote in quotes:
            symbol = quote.get("symbol", "UNKNOWN")

            # Check for errors
            if "status" in quote and quote["status"] == "error":
                print(f"❌ {symbol:6s} - ERROR: {quote.get('message', 'Unknown error')}")
                failed_symbols.append(symbol)
                continue

            # Extract data
            name = quote.get("name", "N/A")
            price = quote.get("close", "N/A")
            change = quote.get("percent_change", "N/A")

            print(f"✅ {symbol:6s} - {name:20s} ${price:>8s} ({change:>6s}%)")
            success_count += 1

        print("-" * 60)
        print(f"\nSummary: {success_count}/{len(TICKERS)} tickers available")

        if failed_symbols:
            print(f"\n⚠️  Failed tickers: {', '.join(failed_symbols)}")
            print("Consider replacing these with alternative symbols.")
        else:
            print("\n✅ All tickers are available!")

        # Check rate limit info if available
        if 'X-RateLimit-Remaining' in response.headers:
            remaining = response.headers['X-RateLimit-Remaining']
            print(f"\nAPI Calls Remaining Today: {remaining}")

        return success_count == len(TICKERS)

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_tickers()
    sys.exit(0 if success else 1)
