from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3, json, os
from datetime import datetime

app = Flask(__name__, static_folder='static')
CORS(app)
ADMIN_PASSWORD = 'quality2025'
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'quality.db')

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS team (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL);
        CREATE TABLE IF NOT EXISTS assignments (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, member_name TEXT NOT NULL, section_id TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS rounds (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, section_id TEXT NOT NULL, time TEXT NOT NULL, inspector TEXT NOT NULL, results TEXT NOT NULL, notes TEXT NOT NULL, saved_at TEXT NOT NULL);
    ''')
    for m in ['أحمد محمود','سارة علي','خالد إبراهيم','منى حسن','محمد أحمد','فاطمة علي','عمر خالد','نور محمد','ياسمين حسن','كريم عمر']:
        try: conn.execute('INSERT INTO team (name) VALUES (?)', (m,))
        except: pass
    conn.commit(); conn.close()

init_db()

@app.route('/')
def index(): return send_from_directory('static', 'index.html')

@app.route('/api/team', methods=['GET'])
def get_team():
    conn = get_db()
    rows = conn.execute('SELECT id, name FROM team ORDER BY name').fetchall()
    conn.close()
    return jsonify([{'id': r['id'], 'name': r['name']} for r in rows])

@app.route('/api/team', methods=['POST'])
def update_team():
    data = request.json or {}
    if data.get('password') != ADMIN_PASSWORD: return jsonify({'error': 'غير مصرح'}), 403
    conn = get_db()
    if data.get('action') == 'add':
        try: conn.execute('INSERT INTO team (name) VALUES (?)', (data['name'],)); conn.commit()
        except: conn.close(); return jsonify({'error': 'الاسم موجود'}), 400
    elif data.get('action') == 'delete':
        conn.execute('DELETE FROM team WHERE id=?', (data['id'],)); conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/assignments/<string:day>', methods=['GET'])
def get_assignments(day):
    conn = get_db()
    rows = conn.execute('SELECT member_name, section_id FROM assignments WHERE date=?', (day,)).fetchall()
    conn.close()
    result = {}
    for r in rows:
        if r['member_name'] not in result: result[r['member_name']] = []
        result[r['member_name']].append(r['section_id'])
    return jsonify(result)

@app.route('/api/assignments', methods=['POST'])
def save_assignments():
    data = request.json or {}
    if data.get('password') != ADMIN_PASSWORD: return jsonify({'error': 'غير مصرح'}), 403
    day = data.get('date'); assignments = data.get('assignments', {})
    conn = get_db()
    conn.execute('DELETE FROM assignments WHERE date=?', (day,))
    for member, sections in assignments.items():
        for sec in sections:
            conn.execute('INSERT INTO assignments (date, member_name, section_id) VALUES (?,?,?)', (day, member, sec))
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/rounds/<string:day>', methods=['GET'])
def get_rounds(day):
    conn = get_db()
    rows = conn.execute('SELECT * FROM rounds WHERE date=?', (day,)).fetchall()
    conn.close()
    result = {}
    for r in rows:
        sid = r['section_id']
        if sid not in result: result[sid] = []
        result[sid].append({'time': r['time'], 'inspector': r['inspector'], 'results': json.loads(r['results']), 'notes': json.loads(r['notes']), 'saved_at': r['saved_at']})
    return jsonify(result)

@app.route('/api/rounds', methods=['POST'])
def save_round():
    data = request.json or {}
    conn = get_db()
    try:
        conn.execute('DELETE FROM rounds WHERE date=? AND section_id=? AND time=?', (data['date'], data['section_id'], data['time']))
        conn.execute('INSERT INTO rounds (date, section_id, time, inspector, results, notes, saved_at) VALUES (?,?,?,?,?,?,?)',
            (data['date'], data['section_id'], data['time'], data['inspector'], json.dumps(data['results']), json.dumps(data['notes']), datetime.now().strftime('%H:%M')))
        conn.commit()
    except Exception as e: conn.close(); return jsonify({'error': str(e)}), 500
    conn.close()
    return jsonify({'success': True})

@app.route('/api/stats/<string:day>', methods=['GET'])
def get_stats(day):
    conn = get_db()
    rows = conn.execute('SELECT * FROM rounds WHERE date=?', (day,)).fetchall()
    conn.close()
    return jsonify({'total_rounds': len(rows), 'total_fails': sum(list(json.loads(r['results']).values()).count('fail') for r in rows), 'sections_done': len(set(r['section_id'] for r in rows)), 'members_active': len(set(r['inspector'] for r in rows))})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
