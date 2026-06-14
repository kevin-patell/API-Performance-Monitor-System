from apscheduler.schedulers.background import BackgroundScheduler
from database import db_pool
from engine import AdvancedEngineWorker

class MonitoringScheduler:
    _scheduler = None

    @classmethod
    def get_scheduler(cls):
        if cls._scheduler is None:
            cls._scheduler = BackgroundScheduler(daemon=True)
        return cls._scheduler

    @classmethod
    def reconfigure_jobs(cls):
        scheduler = cls.get_scheduler()
        scheduler.remove_all_jobs()
        
        with db_pool.acquire() as cursor:
            cursor.execute("SELECT id, interval_seconds FROM apis WHERE is_active = 1")
            active_apis = cursor.fetchall()
            
        for api in active_apis:
            scheduler.add_job(
                func=AdvancedEngineWorker.execute_check,
                trigger='interval',
                seconds=api['interval_seconds'],
                id=f"api_{api['id']}",
                args=[api['id']],
                max_instances=1
            )
        
        if not scheduler.running:
            scheduler.start()