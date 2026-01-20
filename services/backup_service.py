import os
import shutil
from datetime import datetime
import pytz
from flask import current_app

class BackupService:
    def __init__(self, app=None):
        if app:
            self.init_app(app)

    def init_app(self, app):
        self.backup_folder = app.config.get('BACKUP_FOLDER', 'backups')
        self.db_path = app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
        
        if not os.path.exists(self.backup_folder):
            os.makedirs(self.backup_folder)

    def _get_db_path(self):
        db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if db_uri.startswith('sqlite:///'):
            path = db_uri.replace('sqlite:///', '')
            return path
        return None

    def create_backup(self, description=None):
        """Creates a backup of the current sqlite database."""
        source = self._get_db_path()
        if not source or not os.path.exists(source):
            raise FileNotFoundError(f"Database file not found at {source}")

        # Use Paris time for the filename
        paris_tz = pytz.timezone('Europe/Paris')
        now_paris = datetime.now(paris_tz)
        timestamp = now_paris.strftime('%Y%m%d_%H%M%S')
        
        filename = f"backup_{timestamp}"
        if description:
             safe_desc = "".join([c for c in description if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(" ", "_")
             filename += f"_{safe_desc}"
        
        filename += ".db"
        
        backup_dir = current_app.config.get('BACKUP_FOLDER', 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        destination = os.path.join(backup_dir, filename)
        
        try:
            shutil.copy2(source, destination)
            return filename
        except Exception as e:
            current_app.logger.error(f"Backup creation failed: {str(e)}")
            raise e

    def list_backups(self, start_date=None, end_date=None):
        """Returns a list of dicts describing available backups, optionally filtered by date."""
        backup_dir = current_app.config.get('BACKUP_FOLDER', 'backups')
        if not os.path.exists(backup_dir):
            return []

        backups = []
        paris_tz = pytz.timezone('Europe/Paris')
        
        # Parse filter dates if provided
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                start_dt = paris_tz.localize(start_dt)
            except ValueError:
                pass
                
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                # Set to end of day
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                end_dt = paris_tz.localize(end_dt)
            except ValueError:
                pass

        for filename in os.listdir(backup_dir):
            if filename.endswith(".db") and filename.startswith("backup_"):
                filepath = os.path.join(backup_dir, filename)
                stats = os.stat(filepath)
                
                # Convert creation time to Paris time
                created_utc = datetime.utcfromtimestamp(stats.st_ctime)
                created_utc = pytz.utc.localize(created_utc)
                created_at = created_utc.astimezone(paris_tz)
                
                # Filter Logic
                if start_dt and created_at < start_dt:
                    continue
                if end_dt and created_at > end_dt:
                    continue
                
                size_mb = round(stats.st_size / (1024 * 1024), 2)
                
                backups.append({
                    'filename': filename,
                    'created_at': created_at,
                    'size_mb': size_mb,
                    'path': filepath
                })
        
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        return backups

    def restore_backup(self, filename):
        """Restores the database from a given backup filename."""
        backup_dir = current_app.config.get('BACKUP_FOLDER', 'backups')
        source = os.path.join(backup_dir, filename)
        
        if not os.path.exists(source):
            raise FileNotFoundError(f"Backup file {filename} not found.")

        destination = self._get_db_path()
        if not destination:
             raise ValueError("Could not determine database path.")

        try:
            shutil.copy2(source, destination)
            return True
        except Exception as e:
            current_app.logger.error(f"Restore failed: {str(e)}")
            raise e

    def delete_backup(self, filename):
        """Deletes a backup file."""
        backup_dir = current_app.config.get('BACKUP_FOLDER', 'backups')
        filepath = os.path.join(backup_dir, filename)
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Backup file {filename} not found.")
            
        try:
            os.remove(filepath)
            return True
        except Exception as e:
            current_app.logger.error(f"Delete backup failed: {str(e)}")
            raise e

    def get_schedule_config(self):
        config_path = os.path.join(current_app.instance_path, 'backup_config.json')
        if not os.path.exists(config_path):
            return {'enabled': False, 'hour': 2, 'minute': 0, 'start_date': ''}
        
        import json
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                if 'start_date' not in config:
                    config['start_date'] = ''
                return config
        except:
            return {'enabled': False, 'hour': 2, 'minute': 0, 'start_date': ''}

    def set_schedule_config(self, enabled, hour=2, minute=0, start_date=''):
        config = {'enabled': enabled, 'hour': int(hour), 'minute': int(minute), 'start_date': start_date}
        config_path = os.path.join(current_app.instance_path, 'backup_config.json')
        
        import json
        with open(config_path, 'w') as f:
            json.dump(config, f)
            
        self.apply_schedule(config)
        return config

    def apply_schedule(self, config=None):
        if config is None:
            config = self.get_schedule_config()
            
        from extensions import scheduler
        job_id = 'daily_backup'
        
        if config.get('enabled'):
            trigger_args = {
                'trigger': 'cron',
                'hour': config['hour'],
                'minute': config['minute'],
                'id': job_id,
                'replace_existing': True
            }
            
            if config.get('start_date'):
                # start_date needs to be a string or datetime. 
                # APScheduler supports ISO 8601 string.
                trigger_args['start_date'] = config['start_date']
            
            # Note: scheduler uses SCHEDULER_TIMEZONE from config automatically for cron triggers
            
            try:
                scheduler.add_job(func='services.backup_service:run_scheduled_backup', **trigger_args)
                current_app.logger.info(f"Backup scheduled for {config['hour']:02d}:{config['minute']:02d} starting {config.get('start_date', 'now')}")
            except Exception as e:
                 current_app.logger.error(f"Failed to schedule backup: {e}")
            current_app.logger.info(f"Backup scheduled for {config['hour']:02d}:{config['minute']:02d}")
        else:
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
                current_app.logger.info("Backup schedule removed.")

    def get_next_run_time(self):
        """Returns the next scheduled run time as a formatted string in Paris time."""
        from extensions import scheduler
        job = scheduler.get_job('daily_backup')
        if job and job.next_run_time:
            # next_run_time is already timezone aware if SCHEDULER_TIMEZONE is set
            # But let's ensure it's displayed in Paris time anyway
            paris_tz = pytz.timezone('Europe/Paris')
            next_run_local = job.next_run_time.astimezone(paris_tz)
            return next_run_local.strftime('%d/%m/%Y %H:%M:%S')
        return None

def run_scheduled_backup():
    # from flask import current_app # Cannot use current_app here
    from extensions import scheduler
    from services.backup_service import BackupService
    
    # Use the app instance attached to the scheduler
    with scheduler.app.app_context():
        try:
            service = BackupService(scheduler.app)
            filename = service.create_backup(description="auto")
            scheduler.app.logger.info(f"Auto-backup created: {filename}")
        except Exception as e:
            scheduler.app.logger.error(f"Auto-backup failed: {e}")
