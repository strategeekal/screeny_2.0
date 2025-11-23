#!/usr/bin/env python3
"""
Test script to verify stock tickers are available in Twelve Data API
"""

import os
import sys
import requests

# Your tickers from GitHub stocks.csv
TICKERS = [
    "CRM",          # Salesforce
    "S&P 500",      # Standard & Poors 500 Index (⚠️ INVALID FORMAT - will test alternatives)
    "FIDG",         # Fidelity Crypto Industry and Digital Payments ETF
    "SOXQ",         # Invesco PHLX Semiconductor ETF
    "LUMN",         # Lumen Technologies, Inc.
    "IBT",          # iShares Bitcoin Trust ETF
    "AAPL",         # Apple
    "GOOGL",        # Google
    "MSFT",         # Microsoft
]

# Alternative symbols for S&P 500
SP500_ALTERNATIVES = {
    "SPX": "S&P 500 Index (SPX)",
    "^GSPC": "S&P 500 Index (^GSPC)",
    "SPY": "SPDR S&P 500 ETF Trust",
    "VOO": "Vanguard S&P 500 ETF",
}

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

    # Filter out invalid symbols and test them separately
    valid_tickers = [t for t in TICKERS if t != "S&P 500"]

    # Test main batch request (valid symbols only)
    success_count = 0
    failed_symbols = []

    if valid_tickers:
        symbols_str = ",".join(valid_tickers)
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
            print("-" * 70)

            for quote in quotes:
                symbol = quote.get("symbol", "UNKNOWN")

                # Check for errors
                if "status" in quote and quote["status"] == "error":
                    print(f"❌ {symbol:8s} - ERROR: {quote.get('message', 'Unknown error')}")
                    failed_symbols.append(symbol)
                    continue

                # Extract data
                name = quote.get("name", "N/A")
                price = quote.get("close", "N/A")
                change = quote.get("percent_change", "N/A")

                if price != "N/A":
                    print(f"✅ {symbol:8s} - {name:30s} ${float(price):>8.2f} ({change:>6s}%)")
                else:
                    print(f"✅ {symbol:8s} - {name:30s} {'N/A':>8s} ({change:>6s}%)")
                success_count += 1

            # Check rate limit info if available
            remaining = response.headers.get('X-RateLimit-Remaining', 'Unknown')

        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {e}")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    # Test S&P 500 alternatives
    if "S&P 500" in TICKERS:
        print(f"\n⚠️  'S&P 500' is not a valid ticker symbol format!")
        print(f"Testing alternatives for S&P 500 index...\n")

        for alt_symbol, alt_name in SP500_ALTERNATIVES.items():
            try:
                url = f"https://api.twelvedata.com/quote?symbol={alt_symbol}&apikey={api_key}"
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    data = response.json()

                    if "status" not in data or data["status"] != "error":
                        price = data.get("close", "N/A")
                        change = data.get("percent_change", "N/A")

                        if price != "N/A":
                            print(f"✅ {alt_symbol:8s} - {alt_name:30s} ${float(price):>8.2f} ({change:>6s}%)")
                            print(f"   → Recommendation: Use '{alt_symbol}' instead of 'S&P 500'")
                        else:
                            print(f"⚠️  {alt_symbol:8s} - {alt_name:30s} (No data available)")
                    else:
                        print(f"❌ {alt_symbol:8s} - Not available")

            except Exception as e:
                print(f"❌ {alt_symbol:8s} - Error: {e}")

    print("-" * 70)
    print(f"\nSummary: {success_count}/{len(valid_tickers)} valid tickers available")

    if failed_symbols:
        print(f"\n⚠️  Failed tickers: {', '.join(failed_symbols)}")
        print("Consider replacing these with alternative symbols.")
    else:
        print(f"\n✅ All valid tickers are available!")

    print(f"\nAPI Calls Remaining Today: {remaining}")

    return success_count == len(valid_tickers)

if __name__ == "__main__":
    success = test_tickers()
    sys.exit(0 if success else 1)
