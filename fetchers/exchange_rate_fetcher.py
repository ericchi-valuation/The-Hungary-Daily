import requests

def get_exchange_rates():
    """
    Fetch the latest EUR to HUF and USD to HUF exchange rates
    using the free Frankfurter API.
    """
    url = "https://api.frankfurter.app/latest?from=EUR&to=HUF,USD"
    
    try:
        print("💱 Fetching exchange rates from Frankfurter API...")
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        rates = data.get("rates", {})
        eur_huf = rates.get("HUF")
        eur_usd = rates.get("USD")
        
        if eur_huf and eur_usd:
            usd_huf = round(eur_huf / eur_usd, 2)
            
            exchange_info = {
                "eur_huf": eur_huf,
                "usd_huf": usd_huf,
                "summary": f"1 EUR = {eur_huf} HUF | 1 USD = {usd_huf} HUF"
            }
            print(f"  ✔️ Rates: {exchange_info['summary']}")
            return exchange_info
            
    except Exception as e:
        print(f"  ⚠️ Could not fetch exchange rates: {e}")
        
    return {
        "eur_huf": None,
        "usd_huf": None,
        "summary": "Exchange rate data is currently unavailable."
    }

if __name__ == "__main__":
    rates = get_exchange_rates()
    for k, v in rates.items():
        print(f"  {k}: {v}")
