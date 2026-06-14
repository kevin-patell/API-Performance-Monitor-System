import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from config import Config
from database import init_database, db_pool
from auth import login_required, verify_user
from scheduler import MonitoringScheduler
from reporting import ReportingEngine

def bootstrap_application():
    os.makedirs(Config.LOG_DIR, exist_ok=True)
    os.makedirs(Config.EXPORT_DIR, exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), 'templates'), exist_ok=True)
    
    logging.basicConfig(
        filename=os.path.join(Config.LOG_DIR, 'app.log'),
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s'
    )
    init_database()

bootstrap_application()

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# Secure Startup Execution Flow outside request loops
with app.app_context():
    MonitoringScheduler.reconfigure_jobs()

@app.route('/')
def index_route():
    return redirect(url_for('dashboard_route')) if 'logged_in' in session else redirect(url_for('login_route'))

@app.route('/login', methods=['GET', 'POST'])
def login_route():
    if request.method == 'POST':
        user = request.form.get('username')
        passwd = request.form.get('password')
        if verify_user(user, passwd):
            session['logged_in'] = True
            session['username'] = user
            return redirect(url_for('dashboard_route'))
        flash("Invalid operator signature credentials.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout_route():
    session.clear()
    return redirect(url_for('login_route'))

@app.route('/dashboard')
@login_required
def dashboard_route():
    with db_pool.acquire() as cursor:
        cursor.execute("SELECT COUNT(*) as total FROM apis")
        total_apis = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as active FROM apis WHERE is_active = 1")
        active_apis = cursor.fetchone()['active']
        
        cursor.execute("SELECT COUNT(*) as checks, AVG(response_time_ms) as avg_lat FROM api_checks WHERE is_success = 1")
        check_stats = cursor.fetchone()
        total_checks = check_stats['checks'] or 0
        avg_latency = round(check_stats['avg_lat'] or 0, 1)
        
        cursor.execute("SELECT COUNT(*) as total_runs FROM api_checks")
        total_runs = cursor.fetchone()['total_runs'] or 0
        cursor.execute("SELECT COUNT(*) as success FROM api_checks WHERE is_success = 1")
        success_checks = cursor.fetchone()['success'] or 0
        success_rate = round((success_checks / total_runs * 100), 2) if total_runs > 0 else 100.0
        
        cursor.execute('''
            SELECT c.id, a.name, a.method, c.status_code, c.response_time_ms, c.is_success, c.checked_at 
            FROM api_checks c JOIN apis a ON c.api_id = a.id 
            ORDER BY c.checked_at DESC LIMIT 10
        ''')
        recent_checks = cursor.fetchall()
        
    return render_template('dashboard.html', total_apis=total_apis, active_apis=active_apis,
                           total_checks=total_checks, avg_latency=avg_latency, 
                           success_rate=success_rate, recent_checks=recent_checks)

@app.route('/api/metrics-chart')
@login_required
def chart_data_api():
    with db_pool.acquire() as cursor:
        cursor.execute('''
            SELECT checked_at, response_time_ms FROM api_checks 
            WHERE is_success = 1 ORDER BY checked_at DESC LIMIT 20
        ''')
        rows = list(reversed(cursor.fetchall()))
    return jsonify({
        'labels': [r['checked_at'].split()[1] for r in rows],
        'values': [r['response_time_ms'] for r in rows]
    })

@app.route('/api/anomalies')
@login_required
def trace_anomalies_api():
    with db_pool.acquire() as cursor:
        cursor.execute('''
            SELECT c.checked_at, a.name, c.response_time_ms 
            FROM api_checks c JOIN apis a ON c.api_id = a.id
            WHERE c.is_anomaly = 1 ORDER BY c.checked_at DESC LIMIT 1
        ''')
        row = cursor.fetchone()
    return jsonify([dict(row)] if row else [])

@app.route('/manage', methods=['GET', 'POST'])
@login_required
def manage_apis_route():
    with db_pool.acquire() as cursor:
        if request.method == 'POST':
            name = request.form.get('name')
            url = request.form.get('url')
            method = request.form.get('method', 'GET')
            headers = request.form.get('headers', '{}')
            timeout = int(request.form.get('timeout', 10))
            interval = int(request.form.get('interval', 60))
            
            cursor.execute('''
                INSERT INTO apis (name, url, method, headers, timeout, interval_seconds)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, url, method, headers, timeout, interval))
            
            flash(f"Endpoint '{name}' has been successfully mapped.", "success")
            MonitoringScheduler.reconfigure_jobs()
            return redirect(url_for('manage_apis_route'))
            
        cursor.execute("SELECT * FROM apis ORDER BY created_at DESC")
        all_apis = cursor.fetchall()
    return render_template('manage_apis.html', apis=all_apis)

@app.route('/manage/delete/<int:api_id>')
@login_required
def delete_api_action(api_id):
    with db_pool.acquire() as cursor:
        cursor.execute("DELETE FROM apis WHERE id = ?", (api_id,))
    flash("Selected monitoring field removed.", "warning")
    MonitoringScheduler.reconfigure_jobs()
    return redirect(url_for('manage_apis_route'))

@app.route('/reports/export/<string:fmt>')
@login_required
def trigger_export(fmt):
    if fmt == 'csv': path = ReportingEngine.generate_csv()
    elif fmt == 'xlsx': path = ReportingEngine.generate_excel()
    elif fmt == 'pdf': path = ReportingEngine.generate_pdf()
    else: return "Unsupported file format query.", 400
    return send_file(path, as_attachment=True)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)