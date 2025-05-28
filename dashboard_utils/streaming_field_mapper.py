"""
Streaming field mapper for options chain data.

This module provides mapping functionality between streaming data contract fields
and options chain DataFrame columns, ensuring consistent data representation.
"""

import logging

# Configure logging
logger = logging.getLogger(__name__)

class StreamingFieldMapper:
    """
    Maps streaming data fields to options chain DataFrame columns.
    
    This class provides a robust mapping between the numeric field IDs in the 
    streaming data contract and the column names in the options chain DataFrame.
    """
    
    # Complete mapping of streamer field numbers to field names
    STREAMER_FIELD_MAP = {
        0: "symbol",
        1: "description",
        2: "bidPrice",
        3: "askPrice",
        4: "lastPrice",
        5: "highPrice",
        6: "lowPrice",
        7: "closePrice",
        8: "totalVolume",
        9: "openInterest",
        10: "volatility",
        11: "moneyIntrinsicValue",
        12: "expirationYear",
        13: "multiplier",
        14: "digits",
        15: "openPrice",
        16: "bidSize",
        17: "askSize",
        18: "lastSize",
        19: "netChange",
        20: "strikePrice",
        21: "contractType",  # C or P
        22: "underlying",
        23: "expirationMonth",
        24: "deliverables",
        25: "timeValue",
        26: "expirationDay",
        27: "daysToExpiration",
        28: "delta",
        29: "gamma",
        30: "theta",
        31: "vega",
        32: "rho",
        33: "securityStatus",
        34: "theoreticalOptionValue",
        35: "underlyingPrice",
        36: "uvExpirationType",
        37: "markPrice",
        38: "quoteTimeInLong",
        39: "tradeTimeInLong",
        40: "exchange",
        41: "exchangeName",
        42: "lastTradingDay",
        43: "settlementType",
        44: "netPercentChange",
        45: "markPriceNetChange",
        46: "markPricePercentChange",
        47: "impliedYield",
        48: "isPennyPilot",
        49: "optionRoot",
        50: "fiftyTwoWeekHigh",
        51: "fiftyTwoWeekLow",
        52: "indicativeAskPrice",
        53: "indicativeBidPrice",
        54: "indicativeQuoteTime",
        55: "exerciseType"
    }
    
    # Mapping of streamer field names to DataFrame column names
    # This handles cases where the field name in the streaming data
    # doesn't match the column name in the DataFrame
    FIELD_TO_COLUMN_MAP = {
        # Direct mappings (same name)
        "symbol": "symbol",
        "description": "description",
        "bidPrice": "bidPrice",
        "askPrice": "askPrice",
        "lastPrice": "lastPrice",
        "highPrice": "highPrice",
        "lowPrice": "lowPrice",
        "closePrice": "closePrice",
        "totalVolume": "totalVolume",
        "openInterest": "openInterest",
        "volatility": "volatility",
        "strikePrice": "strikePrice",
        "delta": "delta",
        "gamma": "gamma",
        "theta": "theta",
        "vega": "vega",
        "rho": "rho",
        "underlyingPrice": "underlyingPrice",
        
        # Mappings where names differ
        "contractType": "putCall",  # C/P to CALL/PUT
        "moneyIntrinsicValue": "intrinsicValue",
        "timeValue": "timeValue",
        "daysToExpiration": "daysToExpiration",
        "netChange": "netChange",
        "bidSize": "bidSize",
        "askSize": "askSize",
        "lastSize": "lastSize",
        "markPrice": "mark",
        "theoreticalOptionValue": "theoreticalOptionValue",
        "expirationDay": "expirationDay",
        "expirationMonth": "expirationMonth",
        "expirationYear": "expirationYear",
        "underlying": "underlying",
        "deliverables": "optionDeliverablesList",
        "exchangeName": "exchangeName",
        "securityStatus": "securityStatus",
        "netPercentChange": "percentChange",
        "multiplier": "multiplier",
        "fiftyTwoWeekHigh": "high52Week",
        "fiftyTwoWeekLow": "low52Week"
    }
    
    @classmethod
    def get_field_name(cls, field_id):
        """
        Get the field name for a given field ID.
        
        Args:
            field_id: The field ID (int or str)
            
        Returns:
            str: The field name or None if not found
        """
        # Handle both string and numeric field IDs
        if isinstance(field_id, str) and field_id.isdigit():
            field_id = int(field_id)
            
        return cls.STREAMER_FIELD_MAP.get(field_id)
    
    @classmethod
    def get_column_name(cls, field_name):
        """
        Get the DataFrame column name for a given field name.
        
        Args:
            field_name: The field name from streaming data
            
        Returns:
            str: The column name or the original field name if no mapping exists
        """
        return cls.FIELD_TO_COLUMN_MAP.get(field_name, field_name)
    
    @classmethod
    def map_streaming_fields(cls, streaming_data):
        """
        Map streaming data fields to DataFrame column names.
        
        Args:
            streaming_data (dict): The streaming data for a contract
            
        Returns:
            dict: A dictionary mapping DataFrame column names to values
        """
        mapped_data = {}
        
        for field_name, value in streaming_data.items():
            # Skip the key field
            if field_name == "key":
                continue
                
            # Get the corresponding column name
            column_name = cls.get_column_name(field_name)
            
            # Special handling for contractType (C/P to CALL/PUT)
            if field_name == "contractType":
                if value == "C":
                    value = "CALL"
                elif value == "P":
                    value = "PUT"
            
            # Add to mapped data
            mapped_data[column_name] = value
            
        return mapped_data
    
    @classmethod
    def map_streaming_data_to_dataframe(cls, streaming_data, options_df):
        """
        Map streaming data to DataFrame columns.
        
        Args:
            streaming_data (dict): The streaming data for a contract
            options_df (DataFrame): The options chain DataFrame
            
        Returns:
            dict: A dictionary mapping DataFrame column names to values
        """
        return cls.map_streaming_fields(streaming_data)
    
    @classmethod
    def map_field_id_to_column(cls, field_id):
        """
        Map a field ID directly to a DataFrame column name.
        
        Args:
            field_id: The field ID (int or str)
            
        Returns:
            str: The column name or None if no mapping exists
        """
        field_name = cls.get_field_name(field_id)
        if field_name:
            return cls.get_column_name(field_name)
        return None
