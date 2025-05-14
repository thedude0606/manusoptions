import json
import datetime
from collections import defaultdict

INPUT_FILE = "AAPL_minute_data_last_90_days.json"
HOURLY_OUTPUT_FILE = "AAPL_hourly_data_last_90_days.json"
DAILY_OUTPUT_FILE = "AAPL_daily_data_last_90_days.json"

def aggregate_data():
    try:
        with open(INPUT_FILE, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file {INPUT_FILE} not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {INPUT_FILE}.")
        return

    if not data.get("candles"):
        print("Error: No 'candles' found in the input data.")
        return

    minute_candles = data["candles"]
    if not minute_candles:
        print("No minute candles to aggregate.")
        return

    # Sort candles by datetime just in case they are not already sorted
    minute_candles.sort(key=lambda x: x["datetime"])

    hourly_aggregated = defaultdict(lambda: {"open": None, "high": float('-inf'), "low": float('inf'), "close": None, "volume": 0, "datetime": None, "count": 0})
    daily_aggregated = defaultdict(lambda: {"open": None, "high": float('-inf'), "low": float('inf'), "close": None, "volume": 0, "datetime": None, "count": 0})

    for candle in minute_candles:
        dt_object = datetime.datetime.fromtimestamp(candle["datetime"] / 1000, tz=datetime.timezone.utc)
        
        # Hourly aggregation
        hour_key = dt_object.strftime("%Y-%m-%d %H:00:00")
        if hourly_aggregated[hour_key]["open"] is None:
            hourly_aggregated[hour_key]["open"] = candle["open"]
            hourly_aggregated[hour_key]["datetime"] = int(dt_object.replace(minute=0, second=0, microsecond=0).timestamp() * 1000)
        hourly_aggregated[hour_key]["high"] = max(hourly_aggregated[hour_key]["high"], candle["high"])
        hourly_aggregated[hour_key]["low"] = min(hourly_aggregated[hour_key]["low"], candle["low"])
        hourly_aggregated[hour_key]["close"] = candle["close"] # Will be overwritten by the last candle in the hour
        hourly_aggregated[hour_key]["volume"] += candle["volume"]
        hourly_aggregated[hour_key]["count"] += 1

        # Daily aggregation
        day_key = dt_object.strftime("%Y-%m-%d")
        if daily_aggregated[day_key]["open"] is None:
            daily_aggregated[day_key]["open"] = candle["open"]
            # Store daily datetime as start of the day in UTC milliseconds
            daily_aggregated[day_key]["datetime"] = int(dt_object.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
        daily_aggregated[day_key]["high"] = max(daily_aggregated[day_key]["high"], candle["high"])
        daily_aggregated[day_key]["low"] = min(daily_aggregated[day_key]["low"], candle["low"])
        daily_aggregated[day_key]["close"] = candle["close"] # Will be overwritten by the last candle in the day
        daily_aggregated[day_key]["volume"] += candle["volume"]
        daily_aggregated[day_key]["count"] += 1

    # Convert defaultdict to list of dicts
    final_hourly_candles = []
    for key in sorted(hourly_aggregated.keys()): # Sort by time
        # Ensure high/low are not inf/-inf if no data points were processed (should not happen if count > 0)
        if hourly_aggregated[key]["count"] > 0:
            if hourly_aggregated[key]["high"] == float("-inf"): hourly_aggregated[key]["high"] = None
            if hourly_aggregated[key]["low"] == float("inf"): hourly_aggregated[key]["low"] = None
            final_hourly_candles.append({
                "datetime": hourly_aggregated[key]["datetime"],
                "open": hourly_aggregated[key]["open"],
                "high": hourly_aggregated[key]["high"],
                "low": hourly_aggregated[key]["low"],
                "close": hourly_aggregated[key]["close"],
                "volume": hourly_aggregated[key]["volume"]
            })

    final_daily_candles = []
    for key in sorted(daily_aggregated.keys()): # Sort by time
        if daily_aggregated[key]["count"] > 0:
            if daily_aggregated[key]["high"] == float("-inf"): daily_aggregated[key]["high"] = None
            if daily_aggregated[key]["low"] == float("inf"): daily_aggregated[key]["low"] = None
            final_daily_candles.append({
                "datetime": daily_aggregated[key]["datetime"],
                "open": daily_aggregated[key]["open"],
                "high": daily_aggregated[key]["high"],
                "low": daily_aggregated[key]["low"],
                "close": daily_aggregated[key]["close"],
                "volume": daily_aggregated[key]["volume"]
            })

    with open(HOURLY_OUTPUT_FILE, "w") as f:
        json.dump({"symbol": data.get("symbol", "UNKNOWN"), "candles": final_hourly_candles}, f, indent=2)
    print(f"Hourly aggregated data saved to {HOURLY_OUTPUT_FILE}")
    print(f"Number of hourly candles: {len(final_hourly_candles)}")
    if final_hourly_candles:
        print("First hourly candle:", final_hourly_candles[0])

    with open(DAILY_OUTPUT_FILE, "w") as f:
        json.dump({"symbol": data.get("symbol", "UNKNOWN"), "candles": final_daily_candles}, f, indent=2)
    print(f"Daily aggregated data saved to {DAILY_OUTPUT_FILE}")
    print(f"Number of daily candles: {len(final_daily_candles)}")
    if final_daily_candles:
        print("First daily candle:", final_daily_candles[0])

if __name__ == "__main__":
    aggregate_data()

