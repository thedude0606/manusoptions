"""
Data fetching utilities for the dashboard application.
"""

import os
import datetime
import logging
import pandas as pd
import schwabdev
from config import APP_KEY, APP_SECRET, CALLBACK_URL, TOKEN_FILE_PATH

# Configure logging
logger = logging.getLogger(__name__)

def get_minute_data(client, symbol, days=30):
    """
    Fetch minute data for a symbol.
    
    Args:
        client: Schwab API client
        symbol: Stock symbol to fetch data for
        days: Number of days of data to fetch
        
    Returns:
        tuple: (minute_data, error_message)
    """
    logger.info(f"Fetching minute data for {symbol} for the last {days} days")
    
    try:
        # Calculate start and end dates
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days)
        
        # Fetch minute data
        response = client.price_history(
            symbol=symbol,
            frequencyType="minute",
            frequency=1,
            startDate=start_date,
            endDate=end_date,
            needExtendedHoursData=False
        )
        
        if response.ok:
            price_data = response.json()
            if price_data.get("candles"):
                logger.info(f"Successfully fetched {len(price_data['candles'])} minute data points for {symbol}")
                return price_data["candles"], None
            elif price_data.get("empty") == True:
                logger.warning(f"No minute data available for {symbol}")
                return [], f"No minute data available for {symbol}"
            else:
                logger.error(f"Unexpected response format for minute data: {price_data}")
                return [], "Unexpected response format for minute data"
        else:
            logger.error(f"Error fetching minute data: {response.status_code} - {response.text}")
            return [], f"Error fetching minute data: {response.status_code}"
    
    except Exception as e:
        logger.error(f"Exception while fetching minute data for {symbol}: {e}", exc_info=True)
        return [], f"Exception while fetching minute data: {str(e)}"

def get_options_chain_data(client, symbol):
    """
    Fetch options chain data for a symbol.
    
    Args:
        client: Schwab API client
        symbol: Stock symbol to fetch options for
        
    Returns:
        tuple: (options_df, expiration_dates, underlying_price, error_message)
    """
    logger.info(f"Fetching options chain for {symbol}")
    
    try:
        # Fetch options chain
        response = client.option_chains(
            symbol=symbol,
            contractType="ALL",
            strikeCount=20,
            includeUnderlyingQuote=True,
            strategy="SINGLE",
            range="ALL",
            optionType="ALL"
        )
        
        if not response.ok:
            logger.error(f"Error fetching options chain: {response.status_code} - {response.text}")
            return pd.DataFrame(), [], 0, f"Error fetching options chain: {response.status_code}"
        
        options_data = response.json()
        
        # Extract underlying price
        underlying_price = options_data.get("underlyingPrice", 0)
        
        # Extract options and expiration dates
        all_options = []
        expiration_dates = []
        
        # Process call options
        call_exp_date_map = options_data.get("callExpDateMap", {})
        for exp_date, strikes in call_exp_date_map.items():
            # Extract expiration date (format: YYYY-MM-DD:DTE)
            exp_date = exp_date.split(":")[0]
            if exp_date not in expiration_dates:
                expiration_dates.append(exp_date)
            
            # Process each strike price
            for strike_price, contracts in strikes.items():
                for contract in contracts:
                    contract["putCall"] = "CALL"
                    contract["expirationDate"] = exp_date
                    contract["strikePrice"] = float(strike_price)
                    
                    # Check for alternative field names that might contain price data
                    if "lastPrice" not in contract and "last" in contract:
                        contract["lastPrice"] = contract["last"]
                    
                    if "bidPrice" not in contract and "bid" in contract:
                        contract["bidPrice"] = contract["bid"]
                    
                    if "askPrice" not in contract and "ask" in contract:
                        contract["askPrice"] = contract["ask"]
                    
                    # Only add default values if fields are completely missing
                    if "lastPrice" not in contract:
                        contract["lastPrice"] = None
                    
                    if "bidPrice" not in contract:
                        contract["bidPrice"] = None
                    
                    if "askPrice" not in contract:
                        contract["askPrice"] = None
                    
                    all_options.append(contract)
        
        # Process put options
        put_exp_date_map = options_data.get("putExpDateMap", {})
        for exp_date, strikes in put_exp_date_map.items():
            # Extract expiration date (format: YYYY-MM-DD:DTE)
            exp_date = exp_date.split(":")[0]
            if exp_date not in expiration_dates:
                expiration_dates.append(exp_date)
            
            # Process each strike price
            for strike_price, contracts in strikes.items():
                for contract in contracts:
                    contract["putCall"] = "PUT"
                    contract["expirationDate"] = exp_date
                    contract["strikePrice"] = float(strike_price)
                    
                    # Check for alternative field names that might contain price data
                    if "lastPrice" not in contract and "last" in contract:
                        contract["lastPrice"] = contract["last"]
                    
                    if "bidPrice" not in contract and "bid" in contract:
                        contract["bidPrice"] = contract["bid"]
                    
                    if "askPrice" not in contract and "ask" in contract:
                        contract["askPrice"] = contract["ask"]
                    
                    # Only add default values if fields are completely missing
                    if "lastPrice" not in contract:
                        contract["lastPrice"] = None
                    
                    if "bidPrice" not in contract:
                        contract["bidPrice"] = None
                    
                    if "askPrice" not in contract:
                        contract["askPrice"] = None
                    
                    all_options.append(contract)
        
        # Convert to DataFrame
        options_df = pd.DataFrame(all_options)
        
        # Sort expiration dates
        expiration_dates.sort()
        
        if not options_df.empty:
            sample_row = options_df.iloc[0]
            logger.info(f"Sample option data - Symbol: {sample_row.get('symbol')}, Last: {sample_row.get('lastPrice')}, Bid: {sample_row.get('bidPrice')}, Ask: {sample_row.get('askPrice')}")
            
            # Count how many contracts have non-None price fields
            non_none_last = options_df['lastPrice'].notna().sum()
            non_none_bid = options_df['bidPrice'].notna().sum()
            non_none_ask = options_df['askPrice'].notna().sum()
            logger.info(f"Price field statistics - Total contracts: {len(options_df)}, With lastPrice: {non_none_last}, With bidPrice: {non_none_bid}, With askPrice: {non_none_ask}")
        
        logger.info(f"Successfully fetched options chain for {symbol} with {len(options_df)} contracts across {len(expiration_dates)} expiration dates")
        return options_df, expiration_dates, underlying_price, None
    
    except Exception as e:
        logger.error(f"Exception while fetching options chain for {symbol}: {e}", exc_info=True)
        return pd.DataFrame(), [], 0, f"Exception while fetching options chain: {str(e)}"

def get_option_contract_keys(client, symbol, expiration_date=None, option_type=None):
    """
    Get a list of option contract keys for a given symbol, optionally filtered by expiration date and option type.
    
    Args:
        client: Schwab API client
        symbol: Stock symbol to fetch options for
        expiration_date: Optional expiration date to filter by (format: YYYY-MM-DD)
        option_type: Optional option type to filter by ('CALL' or 'PUT')
        
    Returns:
        List of option contract keys, error message (if any)
    """
    options_df, expiration_dates, underlying_price, error = get_options_chain_data(client, symbol)
    
    if error:
        return [], error
    
    if options_df.empty:
        return [], "No options data available"
    
    # Filter by expiration date if provided
    if expiration_date:
        if expiration_date not in expiration_dates:
            return [], f"Expiration date {expiration_date} not found in available dates: {expiration_dates}"
        options_df = options_df[options_df['expirationDate'] == expiration_date]
    
    # Filter by option type if provided
    if option_type:
        if option_type not in ['CALL', 'PUT']:
            return [], f"Invalid option type: {option_type}. Must be 'CALL' or 'PUT'."
        options_df = options_df[options_df['putCall'] == option_type]
    
    # Extract contract keys (symbols)
    if 'symbol' in options_df.columns:
        contract_keys = options_df['symbol'].tolist()
        return contract_keys, None
    else:
        return [], "Symbol column not found in options data"
