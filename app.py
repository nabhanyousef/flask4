from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import os
import base64
import cv2
import numpy as np
import csv
import uuid
import pandas as pd
import io
from fpdf import FPDF  # For PDF generation
from datetime import datetime  # For adding date to the PDF

app = Flask(__name__, static_url_path='/static')
app.secret_key = 'your_secret_key'  # Change this to a secure key in production
app.config['UPLOAD_FOLDER'] = 'static/uploads/'

# Increase the maximum allowed payload size to 16 MB (or adjust as needed)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Dummy user database (replace with a real database in production)
hospitals = {}
patients = {}

# CSV file to store hospital and patient data
HOSPITAL_CSV = 'hospitals.csv'
PATIENT_CSV = 'patients.csv'

# Ensure the CSV files exist
if not os.path.exists(HOSPITAL_CSV):
    with open(HOSPITAL_CSV, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Hospital Name', 'Address', 'Contact Person', 'Mobile No', 'Email', 'Password'])

if not os.path.exists(PATIENT_CSV):
    with open(PATIENT_CSV, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Patient ID', 'Patient Name', 'Height', 'Weight', 'Gender', 'Image', 'Symptoms', 'Diagnosis', 'Review'])

# Welcome route (Login and Signup)
@app.route('/')
def welcome():
    return render_template('welcome.html')

# Signup route for hospitals
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        hospital_name = request.form['hospital_name']
        address = request.form['address']
        contact_person = request.form['contact_person']
        mobile_no = request.form['mobile_no']
        email = request.form['email']
        password = request.form['password']

        # Check if email contains "master"
        if "master" not in email:
            flash('Email must contain the word "master" to register.', 'error')
            return redirect(url_for('signup'))

        if email in hospitals:
            flash('Email already registered. Please use another email.', 'error')
        else:
            hospitals[email] = {
                'hospital_name': hospital_name,
                'address': address,
                'contact_person': contact_person,
                'mobile_no': mobile_no,
                'password': password
            }
            with open(HOSPITAL_CSV, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([hospital_name, address, contact_person, mobile_no, email, password])
            flash('Hospital registered successfully! Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('signup.html')

# Login route for hospitals
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email in hospitals and hospitals[email]['password'] == password:
            session['email'] = email
            session['hospital_name'] = hospitals[email]['hospital_name']
            return redirect(url_for('hospital_master'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('login.html')

# Hospital Master route
@app.route('/hospital_master')
def hospital_master():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('hospital_master.html', hospital_name=session['hospital_name'])

# Patient Registration route
@app.route('/patient_registration', methods=['GET', 'POST'])
def patient_registration():
    if 'email' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        patient_id = request.form['patient_id']  # Get patient ID from the form
        patient_name = request.form['patient_name']
        height = request.form['height']
        weight = request.form['weight']
        gender = request.form['gender']

        if patient_id in patients:
            flash('Patient ID already exists. Please use a different ID.', 'error')
        else:
            patients[patient_id] = {
                'patient_id': patient_id,  # Ensure patient_id is stored in the dictionary
                'hospital_name': session['hospital_name'],
                'patient_name': patient_name,
                'height': height,
                'weight': weight,
                'gender': gender,
                'image': '',
                'symptoms': '',
                'diagnosis': '',
                'review': ''
            }

            session['patient_id'] = patient_id
            return redirect(url_for('camera'))

    return render_template('patient_registration.html', hospital_name=session['hospital_name'])

# Camera route
@app.route('/camera', methods=['GET', 'POST'])
def camera():
    if 'email' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        image_data = request.form['image']
        image_data = image_data.split(',')[1]  # Remove the "data:image/png;base64," prefix
        image_bytes = base64.b64decode(image_data)
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        # Crop the image to the ellipse area
        h, w = image.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.ellipse(mask, (w//2, h//2), (200, 150), 0, 0, 360, 255, -1)  # Draw ellipse
        cropped_image = cv2.bitwise_and(image, image, mask=mask)

        # Save the cropped image
        filename = f"{session['patient_id']}_capture.png"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        cv2.imwrite(filepath, cropped_image)

        patients[session['patient_id']]['image'] = filename
        flash('Image saved successfully!', 'success')
        return redirect(url_for('report'))

    return render_template('camera.html')

# Report route
@app.route('/report')
def report():
    if 'email' not in session:
        return redirect(url_for('login'))

    patient_id = session.get('patient_id')
    if not patient_id or patient_id not in patients:
        return redirect(url_for('hospital_master'))

    patient = patients[patient_id]
    return render_template('report.html', patient=patient)

# Download Report route (CSV)
@app.route('/download_report/<patient_id>', methods=['GET'])
def download_report(patient_id):
    if 'email' not in session:
        return redirect(url_for('login'))

    if patient_id not in patients:
        flash('Patient not found.', 'error')
        return redirect(url_for('hospital_master'))

    # Get patient data
    patient = patients[patient_id]

    # Create a DataFrame for the report (only include required fields)
    report_data = {
        'Patient ID': [patient_id],
        'Patient Name': [patient['patient_name']],
        'Height': [patient['height']],
        'Weight': [patient['weight']],
        'Gender': [patient['gender']]
    }
    df = pd.DataFrame(report_data)

    # Create a CSV file in memory
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    # Return the CSV file as a downloadable response
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"report_{patient_id}.csv"
    )

# Admin Login route
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'nabhan' and password == 'nabhan':
            session['admin'] = True
            return redirect(url_for('doctor_page'))
        else:
            flash('Invalid admin credentials.', 'error')
    return render_template('admin_login.html')

# Doctor Page route
@app.route('/doctor_page', methods=['GET', 'POST'])
def doctor_page():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    patient_id = session.get('patient_id')
    if not patient_id or patient_id not in patients:
        return redirect(url_for('hospital_master'))

    patient = patients[patient_id]

    if request.method == 'POST':
        symptoms = request.form['symptoms']
        diagnosis = request.form['diagnosis']
        review = request.form['review']

        # Update patient data
        patients[patient_id].update({
            'symptoms': symptoms,
            'diagnosis': diagnosis,
            'review': review
        })

        flash('Report saved successfully!', 'success')

    return render_template('doctor.html', patient=patient)

# Download PDF route
@app.route('/download_pdf/<patient_id>', methods=['GET'])
def download_pdf(patient_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    if patient_id not in patients:
        flash('Patient not found.', 'error')
        return redirect(url_for('hospital_master'))

    patient = patients[patient_id]

    # Generate PDF in memory
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Patient Report", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Patient Name: {patient['patient_name']}", ln=True)
    pdf.cell(200, 10, txt=f"Symptoms: {patient['symptoms']}", ln=True)
    pdf.cell(200, 10, txt=f"Diagnosis: {patient['diagnosis']}", ln=True)
    pdf.cell(200, 10, txt=f"Review: {patient['review']}", ln=True)

    # Save PDF to a temporary file
    pdf_filename = f"report_{patient_id}.pdf"
    pdf_filepath = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
    pdf.output(pdf_filepath)

    # Return the PDF file as a downloadable response
    return send_file(
        pdf_filepath,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=pdf_filename
    )

# Logout route
@app.route('/logout')
def logout():
    # Check if the request is coming from the report page
    if request.referrer and 'report' in request.referrer:
        session.clear()  # Clear the session
        return redirect(url_for('patient_registration'))  # Redirect to the patient registration page
    else:
        session.clear()  # Clear the session
        return redirect(url_for('welcome'))  # Redirect to the welcome page (default behavior)

if __name__ == '__main__':
    app.run(debug=True)
