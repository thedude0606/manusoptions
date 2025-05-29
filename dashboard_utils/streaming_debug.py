"""
Enhanced debugging module for streaming data updates.

This module provides additional debugging capabilities for the streaming data
functionality, helping to diagnose issues with data updates not being reflected
in the UI or recommendations.
"""

import logging
import json
import os
import datetime
import time
import threading

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create logs directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)

# Create a file handler for the debug log
debug_log_file = os.path.join(log_dir, f"streaming_debug_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
file_handler = logging.FileHandler(debug_log_file)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Also add a console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class StreamingDebugMonitor:
    """
    Monitors streaming data updates and provides detailed debugging information.
    """
    
    def __init__(self, streaming_manager):
        """
        Initialize the streaming debug monitor.
        
        Args:
            streaming_manager: The StreamingManager instance to monitor
        """
        self.streaming_manager = streaming_manager
        self.is_monitoring = False
        self.monitor_thread = None
        self.last_data_count = 0
        self.last_update_time = None
        self.update_interval = 1.0  # seconds
        self.debug_info = {
            "monitoring_start_time": None,
            "last_data_update_time": None,
            "data_update_count": 0,
            "streaming_status": "Not started",
            "error_messages": [],
            "data_samples": []
        }
        logger.info(f"StreamingDebugMonitor initialized. Debug logs will be written to: {debug_log_file}")
    
    def start_monitoring(self):
        """
        Start monitoring streaming data updates.
        """
        if self.is_monitoring:
            logger.warning("Monitoring is already active")
            return
        
        self.is_monitoring = True
        self.debug_info["monitoring_start_time"] = datetime.datetime.now().isoformat()
        self.debug_info["streaming_status"] = "Monitoring started"
        
        # Start the monitoring thread
        self.monitor_thread = threading.Thread(
            target=self._monitor_worker,
            name="StreamingDebugMonitor"
        )
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("Streaming debug monitoring started")
    
    def stop_monitoring(self):
        """
        Stop monitoring streaming data updates.
        """
        if not self.is_monitoring:
            logger.warning("Monitoring is not active")
            return
        
        self.is_monitoring = False
        self.debug_info["streaming_status"] = "Monitoring stopped"
        logger.info("Streaming debug monitoring stopped")
    
    def _monitor_worker(self):
        """
        Worker thread for monitoring streaming data updates.
        """
        logger.info("Monitor worker thread started")
        
        while self.is_monitoring:
            try:
                # Check if streaming manager is running
                if hasattr(self.streaming_manager, "is_running"):
                    is_running = getattr(self.streaming_manager, "is_running")
                    self.debug_info["streaming_status"] = f"Streaming {'active' if is_running else 'inactive'}"
                
                # Check for data updates
                if hasattr(self.streaming_manager, "latest_data_store"):
                    data_store = getattr(self.streaming_manager, "latest_data_store")
                    current_data_count = len(data_store) if data_store else 0
                    
                    if current_data_count > self.last_data_count:
                        # Data has been updated
                        self.last_update_time = datetime.datetime.now()
                        self.debug_info["last_data_update_time"] = self.last_update_time.isoformat()
                        self.debug_info["data_update_count"] += 1
                        
                        # Log the update
                        new_items = current_data_count - self.last_data_count
                        logger.info(f"Data update detected: {new_items} new items, total: {current_data_count}")
                        
                        # Sample some data for debugging
                        if data_store:
                            sample_keys = list(data_store.keys())[:3]
                            sample_data = {}
                            for key in sample_keys:
                                if key in data_store:
                                    sample_data[key] = {
                                        "bidPrice": data_store[key].get("bidPrice", "N/A"),
                                        "askPrice": data_store[key].get("askPrice", "N/A"),
                                        "lastPrice": data_store[key].get("lastPrice", "N/A"),
                                        "timestamp": datetime.datetime.now().isoformat()
                                    }
                            
                            if sample_data:
                                self.debug_info["data_samples"].append(sample_data)
                                # Keep only the last 10 samples
                                if len(self.debug_info["data_samples"]) > 10:
                                    self.debug_info["data_samples"] = self.debug_info["data_samples"][-10:]
                                
                                logger.info(f"Sample data: {json.dumps(sample_data)}")
                    
                    self.last_data_count = current_data_count
                
                # Check for error messages
                if hasattr(self.streaming_manager, "error_message"):
                    error_message = getattr(self.streaming_manager, "error_message")
                    if error_message and error_message not in self.debug_info["error_messages"]:
                        self.debug_info["error_messages"].append(error_message)
                        logger.error(f"Streaming error: {error_message}")
                
                # Sleep for the update interval
                time.sleep(self.update_interval)
            
            except Exception as e:
                logger.error(f"Error in monitor worker: {e}", exc_info=True)
                self.debug_info["error_messages"].append(f"Monitor error: {str(e)}")
                time.sleep(5)  # Sleep longer on error
        
        logger.info("Monitor worker thread stopped")
    
    def get_debug_info(self):
        """
        Get the current debug information.
        
        Returns:
            dict: The current debug information
        """
        # Add current time and data count
        current_info = self.debug_info.copy()
        current_info["current_time"] = datetime.datetime.now().isoformat()
        current_info["current_data_count"] = self.last_data_count
        
        # Calculate time since last update
        if self.last_update_time:
            time_since_update = (datetime.datetime.now() - self.last_update_time).total_seconds()
            current_info["seconds_since_last_update"] = time_since_update
        
        return current_info
    
    def log_debug_info(self):
        """
        Log the current debug information.
        """
        debug_info = self.get_debug_info()
        logger.info(f"Current debug info: {json.dumps(debug_info)}")
        return debug_info

def create_debug_monitor(streaming_manager):
    """
    Create and start a new streaming debug monitor.
    
    Args:
        streaming_manager: The StreamingManager instance to monitor
        
    Returns:
        StreamingDebugMonitor: The created and started monitor
    """
    monitor = StreamingDebugMonitor(streaming_manager)
    monitor.start_monitoring()
    return monitor
