import time
import json
from typing import Optional, Dict, Any, List, Union
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
import csv
import os
from agent import BaseAgent
from utils import get_logger

logger = get_logger("data_agent")

def _is_float(value):
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False

def _compute_column_stats(values: List[str]) -> Dict[str, Any]:
    """Compute stats for a column of string values."""
    # Convert to floats where possible
    numeric_vals = []
    missing = 0
    for v in values:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            missing += 1
            continue
        if _is_float(v):
            numeric_vals.append(float(v))
        else:
            # Non-numeric value, treat as missing for numeric stats
            missing += 1
    if not numeric_vals:
        return {
            "type": "non-numeric",
            "count": len(values),
            "missing": missing,
            "unique_values": len(set(values)) if values else 0
        }
    # Compute stats
    import math
    mean = sum(numeric_vals) / len(numeric_vals)
    sorted_vals = sorted(numeric_vals)
    n = len(sorted_vals)
    if n % 2 == 0:
        median = (sorted_vals[n//2 - 1] + sorted_vals[n//2]) / 2
    else:
        median = sorted_vals[n//2]
    # population std dev
    variance = sum((x - mean) ** 2 for x in numeric_vals) / n
    std = math.sqrt(variance) if n >= 2 else 0.0
    return {
        "type": "numeric",
        "count": len(numeric_vals),
        "missing": missing,
        "min": min(numeric_vals),
        "max": max(numeric_vals),
        "mean": mean,
        "median": median,
        "std": std,
        "sum": sum(numeric_vals)
    }

class DataAgent(BaseAgent):
    def __init__(self, agent_id: Optional[str] = None, message_bus = None):
        super().__init__(agent_id or f"data_{int(time.time())}", message_bus)
        self.capabilities = ["data_analysis", "statistics", "file_processing"]

    def initialize(self):
        super().initialize()
        self.logger.info("Data agent initialized")
        self.publish_state("agent_capabilities", {
            "agent_id": self.agent_id,
            "capabilities": self.capabilities,
            "timestamp": time.time()
        })

    def execute_task(self, payload: Dict[str, Any]):
        """Execute a data processing task"""
        task_id = payload.get("task_id", "unknown")
        operation = payload.get("operation", "analyze")
        file_path = payload.get("file_path")
        data = payload.get("data", [])
        try:
            self.logger.info(f"Executing data task {task_id}: {operation}")
            self.logger.info(f"HAS_PANDAS: {HAS_PANDAS}")
            self.logger.info(f"file_path: {file_path!r}, type: {type(file_path)}")
            self.logger.info(f"data: {data!r}, type: {type(data)}")
            self.logger.info(f"Checking file_path: {file_path!r}")
            self.logger.info(f"os.path.exists(file_path): {os.path.exists(file_path)}")

            # Initialize result structure
            result = {
                "task_id": task_id,
                "operation": operation,
                "status": "completed",
                "timestamp": time.time()
            }

            # Determine data source
            if file_path and isinstance(file_path, str) and os.path.exists(file_path):
                # Load from file
                self.logger.info(f"Loading data from file: {file_path}")
                if file_path.lower().endswith('.json'):
                    # Handle JSON file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                    result["input_size"] = 1
                    result["output"] = {
                        "summary": f"Loaded JSON file with {len(json_data)} top-level keys from {os.path.basename(file_path)}",
                        "statistics": {
                            "json_keys": list(json_data.keys()),
                            "key_count": len(json_data)
                        }
                    }
                elif HAS_PANDAS:
                    # Use pandas for CSV and Excel
                    try:
                        if file_path.lower().endswith('.csv'):
                            df = pd.read_csv(file_path)
                        elif file_path.lower().endswith(('.xls', '.xlsx')):
                            df = pd.read_excel(file_path)
                        else:
                            # Try CSV as fallback
                            df = pd.read_csv(file_path)
                    except Exception as pandas_error:
                        self.logger.warning(f"Failed to read with pandas: {pandas_error}. Falling back to CSV module.")
                        df = None
                    if df is not None:
                        # Basic info
                        result["input_size"] = len(df)
                        result["output"] = {
                            "summary": f"Loaded {len(df)} rows and {len(df.columns)} columns from {os.path.basename(file_path)}",
                            "statistics": {
                                "row_count": int(len(df)),
                                "column_count": int(len(df.columns)),
                                "columns": {}
                            }
                        }
                        # Compute stats for each column
                        for col in df.columns:
                            col_data = df[col].dropna()
                            if len(col_data) == 0:
                                # All NaN
                                result["output"]["statistics"]["columns"][str(col)] = {
                                    "type": "empty",
                                    "count": 0,
                                    "missing": int(df[col].isna().sum())
                                }
                                continue
                            # Try to detect if numeric
                            if pd.api.types.is_numeric_dtype(df[col]):
                                # Numeric column
                                vals = col_data.tolist()
                                mean = float(vals.mean()) if len(vals) > 0 else 0.0
                                median = float(vals.median()) if len(vals) > 0 else 0.0
                                std = float(vals.std()) if len(vals) > 1 else 0.0
                                result["output"]["statistics"]["columns"][str(col)] = {
                                    "type": "numeric",
                                    "count": int(len(vals)),
                                    "missing": int(df[col].isna().sum()),
                                    "min": float(vals.min()) if len(vals) > 0 else None,
                                    "max": float(vals.max()) if len(vals) > 0 else None,
                                    "mean": mean,
                                    "median": median,
                                    "std": std
                                }
                            else:
                                # Treat as categorical / string
                                # Convert to string for stats
                                str_vals = col_data.astype(str).tolist()
                                result["output"]["statistics"]["columns"][str(col)] = _compute_column_stats(str_vals)
                    else:
                        # Fallback to CSV only
                        if not file_path.lower().endswith('.csv'):
                            raise ValueError(f"File format not supported without pandas: {file_path}. Please install pandas for Excel support.")
                        # Read CSV with csv module
                        rows = []
                        with open(file_path, 'r', encoding='utf-8') as f:
                            reader = csv.reader(f)
                            for row in reader:
                                rows.append(row)
                        if not rows:
                            raise ValueError("CSV file is empty")
                        # Assume first row is header
                        headers = rows[0]
                        data_rows = rows[1:] if len(rows) > 1 else []
                        result["input_size"] = len(data_rows)
                        result["output"] = {
                            "summary": f"Loaded {len(data_rows)} rows and {len(headers)} columns from {os.path.basename(file_path)}",
                            "statistics": {
                                "row_count": int(len(data_rows)),
                                "column_count": int(len(headers)),
                                "columns": {}
                            }
                        }
                        # For each column, collect values
                        for col_idx, header in enumerate(headers):
                            col_vals = [row[col_idx] if col_idx < len(row) else "" for row in data_rows]
                            result["output"]["statistics"]["columns"][str(header)] = _compute_column_stats(col_vals)
                else:
                    # Fallback to CSV only
                    if not file_path.lower().endswith('.csv'):
                        raise ValueError(f"File format not supported without pandas: {file_path}. Please install pandas for Excel support.")
                    # Read CSV with csv module
                    rows = []
                    with open(file_path, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        for row in reader:
                            rows.append(row)
                    if not rows:
                        raise ValueError("CSV file is empty")
                    # Assume first row is header
                    headers = rows[0]
                    data_rows = rows[1:] if len(rows) > 1 else []
                    result["input_size"] = len(data_rows)
                    result["output"] = {
                        "summary": f"Loaded {len(data_rows)} rows and {len(headers)} columns from {os.path.basename(file_path)}",
                        "statistics": {
                            "row_count": int(len(data_rows)),
                            "column_count": int(len(headers)),
                            "columns": {}
                        }
                    }
                    # For each column, collect values
                    for col_idx, header in enumerate(headers):
                        col_vals = [row[col_idx] if col_idx < len(row) else "" for row in data_rows]
                        result["output"]["statistics"]["columns"][str(header)] = _compute_column_stats(col_vals)
            elif data and isinstance(data, list) and len(data) > 0:
                # Use provided data list (backward compatibility)
                self.logger.info(f"Using provided data list with {len(data)} items")
                # Assume data is list of dicts or list of lists
                if isinstance(data[0], dict):
                    # List of dicts
                    if not data:
                        raise ValueError("Data list is empty")
                    # Convert to rows
                    headers = list(data[0].keys())
                    rows = []
                    for item in data:
                        row = [item.get(h) for h in headers]
                        rows.append(row)
                elif isinstance(data[0], list):
                    # List of lists, assume first row is header?
                    # We'll treat as raw data without header
                    headers = [f"col_{i}" for i in range(len(data[0]))]
                    rows = data
                else:
                    # Flat list of values
                    headers = ["value"]
                    rows = [[v] for v in data]
                result["input_size"] = len(rows)
                result["output"] = {
                    "summary": f"Processed {len(rows)} rows and {len(headers)} columns from provided data",
                    "statistics": {
                        "row_count": int(len(rows)),
                        "column_count": int(len(headers)),
                        "columns": {}
                    }
                }
                for col_idx, header in enumerate(headers):
                    col_vals = [row[col_idx] if col_idx < len(row) else None for row in rows]
                    # Convert None to empty string for stats
                    col_vals_str = ["" if v is None else str(v) for v in col_vals]
                    result["output"]["statistics"]["columns"][str(header)] = _compute_column_stats(col_vals_str)
            else:
                # No data source
                raise ValueError("No file_path or data provided in payload")

            # If operation is something else, we could extend
            if operation != "analyze":
                self.logger.warning(f"Operation '{operation}' not specifically handled, defaulting to analyze")

        except Exception as e:
            self.logger.error(f"Error processing data task {task_id}: {e}", exc_info=True)
            task_type = payload.get("task_type", "data_processing")
            description = payload.get("description", "")
            result = {
                "task_id": task_id,
                "task_type": task_type,
                "description": description,
                "status": "failed",
                "error": str(e),
                "_timestamp": time.time()
            }
            # Still provide some output
            result["output"] = {
                "summary": f"Failed to process data: {str(e)}",
                "statistics": {}
            }

        # Add timestamp to result (if not already set in error case)
        if "_timestamp" not in result:
            result["_timestamp"] = time.time()

        # Publish result
        self.publish_state(f"data_result_{task_id}", result)

        # Notify supervisor
        completion_message = {
            "task_id": task_id,
            "agent_id": self.agent_id,
            "result": result,
            "timestamp": time.time()
        }
        self.message_bus.publish("task_completed", completion_message)

        self.logger.info(f"Data task {task_id} completed with status: {result.get('status')}")

    def handle_query(self, payload: Dict[str, Any]):
        """Handle data-related queries"""
        query_type = payload.get("type")
        if query_type == "stats":
            # Return some cached stats
            pass