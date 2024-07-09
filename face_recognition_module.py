import cv2
import numpy as np
import face_recognition
import os
from datetime import datetime
from database import get_db_connection

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

# Fungsi untuk menghasilkan frame dari kamera
def generate_frames():
    cam = cv2.VideoCapture(0)
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
