from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"

# ---------- DB INIT ----------
def init_db():
    conn = sqlite3.connect('expense.db')
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            amount REAL,
            category TEXT,
            user_id INTEGER
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# ---------- REGISTER ----------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']

        conn = sqlite3.connect('expense.db')
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username,password) VALUES (?,?)",(u,p))
        conn.commit()
        conn.close()
        return redirect('/login')

    return render_template('register.html')

# ---------- LOGIN ----------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']

        conn = sqlite3.connect('expense.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?",(u,p))
        user = cur.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            return redirect('/')
        else:
            return "Invalid login"

    return render_template('login.html')

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---------- HOME ----------
@app.route('/', methods=['GET'])
def index():
    if 'user_id' not in session:
        return redirect('/login')

    search = request.args.get('search', '')
    category = request.args.get('category', '')

    conn = sqlite3.connect('expense.db')
    cur = conn.cursor()

    query = "SELECT * FROM expenses WHERE user_id=?"
    params = [session['user_id']]

    if search:
        query += " AND title LIKE ?"
        params.append('%' + search + '%')

    if category:
        query += " AND category=?"
        params.append(category)

    cur.execute(query, params)
    data = cur.fetchall()

    cur.execute("SELECT category, SUM(amount) FROM expenses WHERE user_id=? GROUP BY category",
                (session['user_id'],))
    summary = cur.fetchall()

    conn.close()
    return render_template('index.html', expenses=data, summary=summary)

# ---------- ADD ----------
@app.route('/add', methods=['GET','POST'])
def add():
    if request.method == 'POST':
        t = request.form['title']
        a = request.form['amount']
        c = request.form['category']

        conn = sqlite3.connect('expense.db')
        cur = conn.cursor()
        cur.execute("INSERT INTO expenses (title,amount,category,user_id) VALUES (?,?,?,?)",
                    (t,a,c,session['user_id']))
        conn.commit()
        conn.close()

        return redirect('/')

    return render_template('add.html')

# ---------- DELETE ----------
@app.route('/delete/<int:id>')
def delete(id):
    conn = sqlite3.connect('expense.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE id=?",(id,))
    conn.commit()
    conn.close()
    return redirect('/')

# ---------- EDIT ----------
@app.route('/edit/<int:id>', methods=['GET','POST'])
def edit(id):
    conn = sqlite3.connect('expense.db')
    cur = conn.cursor()

    if request.method == 'POST':
        t = request.form['title']
        a = request.form['amount']
        c = request.form['category']

        cur.execute("UPDATE expenses SET title=?,amount=?,category=? WHERE id=?",
                    (t,a,c,id))
        conn.commit()
        conn.close()
        return redirect('/')

    cur.execute("SELECT * FROM expenses WHERE id=?",(id,))
    data = cur.fetchone()
    conn.close()

    return render_template('edit.html', expense=data)

if __name__ == '__main__':
    app.run(debug=True)