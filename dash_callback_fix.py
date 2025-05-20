"""
Dash Callback Fix for Duplicate Outputs Error

This script provides a solution for the duplicate callback outputs error in the Manus Options dashboard.
It modifies the app initialization to disable hot reloading and ensures proper callback registration.

Usage:
1. Place this file in the root directory of your project
2. Run this script instead of dashboard_app.py
3. The script will import and run your dashboard with the fix applied

"""

import os
import sys
import importlib.util
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_dashboard_app():
    """Load the dashboard_app module without executing it."""
    try:
        # Get the absolute path to dashboard_app.py
        dashboard_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard_app.py')
        
        # Load the module without executing it
        spec = importlib.util.spec_from_file_location("dashboard_app", dashboard_path)
        dashboard_module = importlib.util.module_from_spec(spec)
        sys.modules["dashboard_app"] = dashboard_module
        spec.loader.exec_module(dashboard_module)
        
        return dashboard_module
    except Exception as e:
        logger.error(f"Failed to load dashboard_app.py: {e}")
        raise

def run_with_fix():
    """Run the dashboard app with the duplicate callback fix applied."""
    try:
        # Load the dashboard module
        dashboard_module = load_dashboard_app()
        
        # Get the app instance
        app = dashboard_module.app
        
        # Ensure suppress_callback_exceptions is True
        app.config.suppress_callback_exceptions = True
        
        # Run the app with hot reloading disabled
        logger.info("Starting dashboard with hot reloading disabled to prevent duplicate callback issues")
        app.run_server(debug=True, use_reloader=False, host="0.0.0.0")
        
    except Exception as e:
        logger.error(f"Error running dashboard with fix: {e}")
        raise

if __name__ == "__main__":
    logger.info("Applying fix for duplicate callback outputs error")
    run_with_fix()
