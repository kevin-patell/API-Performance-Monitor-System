import time
import json
import requests
import logging
import os
import pandas as pd
from config import Config
from database import db_pool

logger = logging.getLogger('MonitorEngine')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(os.path.join(Config.LOG_DIR, 'monitor.log'))
handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s'))
logger.addHandler(handler)

class AdvancedEngineWorker:
    """Dispatches asynchronous performance traces and measures statistical anomalies via rolling Z-scores."""
    
    @staticmethod
    def calculate_anomaly(api_id: int, current_latency: float) -> int:
        with db_pool.acquire() as cursor:
            cursor.execute('''
                SELECT response_time_ms FROM api_checks 
                WHERE api_id = ? AND is_success = 1 
                ORDER BY checked_at DESC LIMIT 30
            ''', (api_id,))
            rows = cursor.fetchall()
            
        if len(rows) < 10:
            return 0
            
        latencies = [r['response_time_ms'] for r in rows]
        df = pd.Series(latencies)
        mean = df.mean()
        std_dev = df.std()
        
        if std_dev == 0:
            return 0
            
        z_score = abs(current_latency - mean) / std_dev
        return 1 if z_score > 2.5 else 0

    @classmethod
    def execute_check(cls, api_id: int):
        with db_pool.acquire() as cursor:
            cursor.execute("SELECT * FROM apis WHERE id = ? AND is_active = 1", (api_id,))
            api = cursor.fetchone()
            
        if not api:
            return

        headers = {}
        if api['headers']:
            try:
                headers = json.loads(api['headers'])
            except:
                pass

        status_code = None
        response_time_ms = 0.0
        is_success = 0
        is_anomaly = 0
        error_message = None

        start_time = time.perf_counter()
        try:
            res = requests.request(
                method=api['method'],
                url=api['url'],
                headers=headers,
                timeout=api['timeout'],
                allow_redirects=True
            )
            response_time_ms = (time.perf_counter() - start_time) * 1000
            status_code = res.status_code
            is_success = 1 if 200 <= status_code < 400 else 0
            if not is_success:
                error_message = f"Bad HTTP Response Signature: {status_code}"
        except requests.exceptions.Timeout:
            response_time_ms = (time.perf_counter() - start_time) * 1000
            error_message = "Target connection frame timed out."
        except Exception as ex:
            error_message = str(ex)

        if is_success:
            is_anomaly = cls.calculate_anomaly(api_id, response_time_ms)

        with db_pool.acquire() as cursor:
            cursor.execute('''
                INSERT INTO api_checks (api_id, status_code, response_time_ms, is_success, is_anomaly, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (api_id, status_code, round(response_time_ms, 2), is_success, is_anomaly, error_message))
            
            if is_anomaly:
                cursor.execute("INSERT INTO activity_logs (category, message) VALUES (?, ?)",
                               ('ANOMALY', f"Outlier registered on '{api['name']}': Variance spike detected ({round(response_time_ms, 1)}ms)"))
                logger.warning(f"ANOMALY: {api['name']} latency baseline drift detected -> {round(response_time_ms, 2)}ms")