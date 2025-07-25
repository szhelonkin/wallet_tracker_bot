from pycoingecko import CoinGeckoAPI

def get_prices(ids, vs_currencies):
	cg = CoinGeckoAPI()
	return cg.get_price(ids, vs_currencies)


#print(get_prices("bitcoin", "usd,rub")["bitcoin"]['usd'])
