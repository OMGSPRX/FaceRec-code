# Mengimpor pustaka yang diperlukan
import cv2
import numpy as np
import face_recognition
import os
import csv
from datetime import datetime
from flask import Flask, render_template, Response, request, redirect, session
from passlib.hash import sha256_crypt
import mysql.connector
import pyttsx3
from queue import Queue
from threading import Thread

# Membuat instance Flask
app = Flask(__name__)
app.secret_key = 'supersecretkey'

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "facerec"

# Fungsi untuk menghubungkan ke database
def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

# Menginisialisasi kamera
cam = cv2.VideoCapture(0)

# Path folder tempat gambar disimpan
path = 'Train'

# Inisialisasi list untuk menyimpan data gambar, nama, dan nomor induk karyawan
images = []
Known_employee_names = []
Known_employee_rolls = []

# Mendapatkan daftar file di dalam folder Train
Known_employee_filenames = os.listdir(path)

# Memproses setiap file gambar
for cl in Known_employee_filenames:
    curImg = cv2.imread(f'{path}/{cl}')
    images.append(curImg)
    Known_employee_names.append(cl.split('_')[0])
    Known_employee_rolls.append(cl.split('_')[1].split('.')[0])

# Fungsi untuk mendapatkan encoding wajah dari gambar
def findEncodings(images):
    encodeList = []
    for img in images:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encode = face_recognition.face_encodings(img)[0]
        encodeList.append(encode)
    return encodeList

# Fungsi untuk mencatat kehadiran ke dalam file database
def markAttendance(name, roll):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Periksa apakah karyawan sudah absen hari ini
    db_conn = get_db_connection()
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM absensi WHERE name = %s AND DATE(check_in) = CURDATE()", (name,))
    result = cursor.fetchone()

    if result is None:
        # Karyawan belum absen hari ini, catat absensi
        cursor.execute("INSERT INTO absensi (name, id_karyawan, check_in) VALUES (%s, %s, %s)", (name, roll, now))
        db_conn.commit()
    
    cursor.close()
    db_conn.close()
    
# Mendapatkan encoding wajah untuk semua gambar karyawan
Known_employee_encodings = findEncodings(images)

# Fungsi untuk menginisialisasi text-to-speech engine
def initialize_text_to_speech_engine():
    engine = pyttsx3.init()
    return engine

# Fungsi untuk menjalankan text-to-speech engine di thread terpisah
def speak_from_queue(queue, engine):
    while True:
        text = queue.get()
        if text is None:
            break
        engine.say(text)
        engine.runAndWait()

# Inisialisasi text-to-speech engine dan antrian
engine = initialize_text_to_speech_engine()
speech_queue = Queue()

# Buat thread terpisah untuk text-to-speech
speech_thread = Thread(target=speak_from_queue, args=(speech_queue, engine))
speech_thread.start()

# Fungsi untuk menghasilkan frame dari kamera
def generate_frames():
    cam.open(0)
    feedback_count = {}
    while True:
        success, img = cam.read()
        if not success:
            break
        else:
            try:
                imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
                imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
                facesCurFrame = face_recognition.face_locations(imgS)
                encodesCurFrame = face_recognition.face_encodings(imgS, facesCurFrame)
                
                for encodeFace, faceLoc in zip(encodesCurFrame, facesCurFrame):
                    matches = face_recognition.compare_faces(Known_employee_encodings, encodeFace, 0.5)
                    faceDis = face_recognition.face_distance(Known_employee_encodings, encodeFace)
                    matchIndex = np.argmin(faceDis)
                    if matches[matchIndex]:
                        name = Known_employee_names[matchIndex].upper()
                        roll = Known_employee_rolls[matchIndex]
                        y1, x2, y2, x1 = faceLoc
                        y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.rectangle(img, (x1, y2 - 35), (x2, y2), (0, 255, 0), cv2.FILLED)
                        cv2.putText(img, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
                        markAttendance(name, roll)
                        
                        # Voice feedback
                        if name not in feedback_count or feedback_count[name] < 1:
                            speech_queue.put(f"Hello, {name}")
                            feedback_count[name] = feedback_count.get(name, 0) + 1

                ret, buffer = cv2.imencode('.jpg', img)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + bytearray(buffer) + b'\r\n')
                cv2.waitKey(1)
            except Exception as e:
                print(f"Error: {e}")
                break
    cam.release()

    
@app.route('/')
def index():
    if 'logged_in' in session:
        try:
            db_conn = get_db_connection()
            cursor = db_conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM login")
            total_pengguna = cursor.fetchone()
            cursor.execute("SELECT * FROM login")
            users = cursor.fetchall()
            cursor.close()
            db_conn.close()
        except Exception as e:
            print(f"Error: {e}")
            total_pengguna = (0,)
            users = []

        return render_template('index.html', nama=session['nama'], username=session['username'], total_pengguna=total_pengguna, users=users)
    else:
        return redirect('/loginsignup')

@app.route('/attendance')
def attendance():
    if 'logged_in' in session:
        return render_template('attendance.html')
    else:
        return redirect('/loginsignup')

@app.route('/video')
def video():
    if 'logged_in' in session:
        return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return redirect('/loginsignup')

@app.route('/table')
def table():
    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        cursor.execute("SELECT name, id_karyawan, check_in FROM absensi")
        absensi_data = cursor.fetchall()
        cursor.close()
        db_conn.close()
    except Exception as e:
        print(f"Error: {e}")
        absensi_data = []
    
    return render_template('table.html', data=absensi_data)

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
                file.save(os.path.join('./Train/', stfilename))
                newImg = cv2.imread(f'{path}/{stfilename}')
                newEncode = face_recognition.face_encodings(cv2.cvtColor(newImg, cv2.COLOR_BGR2RGB))[0]
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

@app.route('/tampil_data')
def tampil_data():
    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        cursor.execute("SELECT name, id_karyawan FROM employee")
        data_list = cursor.fetchall()
        cursor.close()
        db_conn.close()
    except Exception as e:
        print(f"Error: {e}")
        data_list = []
    return render_template('tampil_data.html', data_list=data_list)

@app.route('/loginsignup')
def loginsignup():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['usr']
        password = request.form['pwd']
        try:
            db_conn = get_db_connection()
            cursor = db_conn.cursor()
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

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username_up = request.form['usrup']
        password_up = request.form['pwdup']
        nama = request.form['nama']
        hashed_password = sha256_crypt.hash(password_up)
        try:
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

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect('/loginsignup')

# Menjalankan aplikasi Flask
if __name__ == "__main__":
    app.run(host='127.0.0.1', port=81)