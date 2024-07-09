from flask import Flask, render_template, Response, request, redirect, session
from database import get_db_connection
from face_recognition_module import generate_frames, Known_employee_encodings, Known_employee_names, Known_employee_rolls
from text_to_speech import initialize_text_to_speech_engine, speak_from_queue
from passlib.hash import sha256_crypt
import os
import cv2
from queue import Queue
from threading import Thread

# Inisialisasi aplikasi Flask
app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Inisialisasi text-to-speech engine dan antrian untuk feedback suara
engine = initialize_text_to_speech_engine()
speech_queue = Queue()

# Buat thread terpisah untuk menangani text-to-speech secara asynchronous
speech_thread = Thread(target=speak_from_queue, args=(speech_queue, engine))
speech_thread.start()

# Route utama aplikasi
@app.route('/')
def index():
    if 'logged_in' in session:
        try:
            # Ambil koneksi ke database
            db_conn = get_db_connection()
            cursor = db_conn.cursor()
            
            # Hitung total pengguna
            cursor.execute("SELECT COUNT(*) FROM login")
            total_pengguna = cursor.fetchone()
            
            # Ambil semua data pengguna
            cursor.execute("SELECT * FROM login")
            users = cursor.fetchall()
            
            cursor.close()
            db_conn.close()
        except Exception as e:
            print(f"Error: {e}")
            total_pengguna = (0,)
            users = []

        # Render halaman utama dengan data pengguna
        return render_template('index.html', nama=session['nama'], username=session['username'], total_pengguna=total_pengguna, users=users)
    else:
        return redirect('/loginsignup')

# Route untuk halaman absensi
@app.route('/attendance')
def attendance():
    if 'logged_in' in session:
        return render_template('attendance.html')
    else:
        return redirect('/loginsignup')

# Route untuk menampilkan video dari kamera
@app.route('/video')
def video():
    if 'logged_in' in session:
        return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return redirect('/loginsignup')

# Route untuk menampilkan tabel absensi
@app.route('/table')
def table():
    try:
        # Ambil koneksi ke database
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        
        # Ambil data absensi
        cursor.execute("SELECT name, id_karyawan, check_in FROM absensi")
        absensi_data = cursor.fetchall()
        
        cursor.close()
        db_conn.close()
    except Exception as e:
        print(f"Error: {e}")
        absensi_data = []
    
    # Render halaman tabel absensi
    return render_template('table.html', data=absensi_data)

# Route untuk mengunggah gambar pengguna baru
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['image']
        name = request.form['name']
        roll = request.form['roll']
        ext = file.filename.split('.')[-1]
        stfilename = f"{name}_{roll}.{ext}"
        
        if file and name and roll:
            try:
                # Simpan file gambar yang diunggah
                file.save(os.path.join('./Train/', stfilename))
                newImg = cv2.imread(f'./Train/{stfilename}')
                
                # Lakukan encoding pada gambar baru
                newEncode = face_recognition.face_encodings(cv2.cvtColor(newImg, cv2.COLOR_BGR2RGB))[0]
                
                # Tambahkan data baru ke list encoding, nama, dan nomor induk karyawan
                Known_employee_encodings.append(newEncode)
                Known_employee_names.append(name)
                Known_employee_rolls.append(roll)
                
                # Simpan data ke dalam tabel 'employee'
                try:
                    db_conn = get_db_connection()
                    cursor = db_conn.cursor()
                    cursor.execute("INSERT INTO employee (name, id_karyawan) VALUES (%s, %s)", (name, roll))
                    db_conn.commit()
                    cursor.close()
                    db_conn.close()
                except Exception as e:
                    print(f"Error: {e}")
                    return render_template('upload.html', badImage=True)

                return redirect("/")
            except:
                os.remove(f'./Train/{stfilename}')
                return render_template('upload.html', badImage=True)
    return render_template('upload.html')

# Route untuk menampilkan data pengguna
@app.route('/tampil_data')
def tampil_data():
    try:
        # Ambil koneksi ke database
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        
        # Ambil data dari tabel 'employee'
        cursor.execute("SELECT name, id_karyawan FROM employee")
        data_list = cursor.fetchall()
        
        cursor.close()
        db_conn.close()
    except Exception as e:
        print(f"Error: {e}")
        data_list = []
    
    # Render halaman tampil data
    return render_template('tampil_data.html', data_list=data_list)

# Route untuk halaman login/signup
@app.route('/loginsignup')
def loginsignup():
    return render_template('login.html')

# Route untuk login pengguna
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['usr']
        password = request.form['pwd']
        
        try:
            # Ambil koneksi ke database
            db_conn = get_db_connection()
            cursor = db_conn.cursor()
            
            # Cek pengguna di tabel login
            cursor.execute("SELECT * FROM login WHERE username = %s", (username,))
            user = cursor.fetchone()
            
            if user and sha256_crypt.verify(password, user[3]):
                session['logged_in'] = True
                session['username'] = user[2]
                session['nama'] = user[1]
                
                cursor.close()
                db_conn.close()
                
                return redirect('/')
            else:
                cursor.close()
                db_conn.close()
                return render_template('login.html', error_message='Invalid login')
        except Exception as e:
            print(f"Error: {e}")
            return render_template('login.html', error_message='Database connection error')
    return render_template('login.html')

# Route untuk signup pengguna baru
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username_up = request.form['usrup']
        password_up = request.form['pwdup']
        nama = request.form['nama']
        hashed_password = sha256_crypt.hash(password_up)
        
        try:
            # Simpan pengguna baru ke tabel login
            db_conn = get_db_connection()
            cursor = db_conn.cursor()
            cursor.execute("INSERT INTO login (nama, username, password) VALUES (%s, %s, %s)", (nama, username_up, hashed_password))
            db_conn.commit()
            cursor.close()
            db_conn.close()
            
            return redirect('/loginsignup')
        except Exception as e:
            print(f"Error: {e}")
            return render_template('login.html', error_message='Database connection error')
    return render_template('login.html')

# Route untuk logout pengguna
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect('/loginsignup')

# Jalankan aplikasi Flask
if __name__ == "__main__":
    app.run(host='127.0.0.1', port=81)
