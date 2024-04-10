from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from flask_socketio import SocketIO
import csv
from itertools import count
from geopy.distance import geodesic
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

@app.route("/")
def index():
    return render_template("login.html")

@app.route('/login')
def login(): 
    return render_template('login.html', message='Please log in')

@app.route('/auth', methods=['POST', 'GET']) 
def auth():
    if request.method == 'POST':
        registration_number = request.form['registration_number']
        password = request.form['password']
        vtop_df = pd.read_csv('C:\\Users\\Eshwar\\Desktop\\PassPool\\data\\vtop.csv')
        dict_records = vtop_df.to_dict(orient='records')
    
        for i in dict_records:
            if registration_number == i['registration_number'] and password == i['vtop_password']:
                student_df = pd.read_csv('C:\\Users\\Eshwar\\Desktop\\PassPool\\data\\student.csv')
                stud_records = student_df.to_dict(orient='records')
                for j in stud_records:
                    if i['registration_number'] == j['registration_number']:
                        student_name = j['student_name']
                        phone_number = j['phone_number']
                        session['student_name'] = student_name
                        session['reg_number'] = registration_number
                        session['phone_number'] = phone_number
                return redirect(url_for('home'))  # Redirect to home page after successful authentication

# If authentication fails, render login page with error message
    return login("Incorrect registration number or password")

@app.route('/home')
def home():
    student_name = session.get('student_name')
    reg_number = session.get('reg_number')
    return render_template(
        'home.html',
        title='Home Page',
        year=datetime.now().year, 
        student_name=student_name,
        reg_number=reg_number
    )

@app.route('/generate_outpass', methods=['POST', 'GET'])
def generate_outpass():
    reg_number = session.get('reg_number')
    if request.method == 'POST':
        out_date = request.form['out_date']
        out_time = request.form['out_time']
        in_date = request.form['in_date']
        in_time = request.form['in_time']
        reason = request.form['reason']
        leave_type = request.form['leave_type']
        
        # Create a unique outpass_id
        outpass_id = len(pd.read_csv('C:\\Users\\Eshwar\\Desktop\\PassPool\\data\\outpass.csv')) + 1
        session['outpass_id']=outpass_id

        
        # Create a DataFrame with the new outpass data
        new_outpass = pd.DataFrame({
            'outpass_id': [outpass_id],
            'registration_number': [reg_number],
            'out_date': [out_date],
            'out_time': [out_time],
            'in_date': [in_date],
            'in_time': [in_time],
            'reason': [reason],
            'leave_type': [leave_type],
            'status': 0
        })
        
        # Append the new outpass data to the outpass.csv file
        new_outpass.to_csv('C:\\Users\\Eshwar\\Desktop\\PassPool\\data\\outpass.csv', mode='a', header=False, index=False)
        
        return redirect(url_for('under_review'))

    return render_template (
        'generate_outpass.html',
        title='Outpass Generator',
        year=datetime.now().year, 
        reg_number=reg_number
    )

@app.route('/success')
def success():
    return render_template (
        'success.html',
        title='Success',
        year=datetime.now().year,
    )

@app.route('/under_review')
def under_review():
    return render_template (    
        'under_review.html',
        title='Under Review',
        year=datetime.now().year, 
    )

@app.route('/rejected')
def rejected():
    return render_template (
        'rejected.html',
        title='Rejected',
        year=datetime.now().year, 
    )

@app.route('/carpool')
def carpool():
    global trip_id_counter
    reg_number = session.get('reg_number')
    outpass_number = session.get('outpass_id')
    if request.method == 'POST':
        travel_date = request.form['travel_date']
        travel_time = request.form['travel_time']
        from_location = request.form['from_location']
        to_location = request.form['to_location']
        
        # Increment trip ID counter to generate a unique trip ID
        trip_id_counter = len(pd.read_csv('C:\\Users\\Eshwar\\Desktop\\PassPool\\data\\trip.csv')) + 1
        
        # Create a dictionary with the trip details including the generated trip ID
        new_trip_data = pd.DataFrame({
            'trip_id': trip_id_counter,
            'registration_number':reg_number,
            'outpass_number': outpass_number,
            'date': travel_date,
            'source': from_location,
            'destination': to_location,
            'time': travel_time
        })
        
        # Append the trip data to the trip.csv file
        new_trip_data.to_csv('C:\\Users\\Eshwar\\Desktop\\PassPool\\data\\trip.csv', mode='a', header=False, index=False)
        
        return redirect(url_for('available'))

    return render_template(
        'carpool.html',
        title='Carpool',
        year=datetime.now().year
    )

@app.route('/profile')
def profile():
    reg_number = session.get('reg_number')
    student_name = session.get('student_name')
    phone_number = session.get('phone_number')
    
    # Read the outpass data from the CSV file
    outpass_df = pd.read_csv('C:\\Users\\Eshwar\\Desktop\\PassPool\\data\\outpass.csv')
    
    # Filter outpasses based on registration number
    user_outpasses = outpass_df[outpass_df['student_registration_number'] == reg_number]
    
    # Filter outpasses based on status (0 for under review, 1 for approved)
    outpasses_under_review = user_outpasses[user_outpasses['status'] == 0]
    outpasses_approved = user_outpasses[user_outpasses['status'] == 1]
    
    # Pass student and outpass details to the profile template
    return render_template(
        'profile.html',
        reg_number=reg_number,
        student_name=student_name,
        phone_number=phone_number,
        outpasses_under_review=outpasses_under_review.to_dict(orient='records'),
        outpasses_approved=outpasses_approved.to_dict(orient='records')
    )
def calculate_distance(coord1, coord2):
    return geodesic(coord1, coord2).kilometers

def within_time_range(time1, time2):
    time_format = "%H:%M"
    dt1 = datetime.strptime(time1, time_format)
    dt2 = datetime.strptime(time2, time_format)
    time_diff = abs((dt2 - dt1).total_seconds()) / 3600
    return time_diff <= 2

def filter_rides(your_coordinates, rides, your_time):
    priority1 = []
    priority2 = []
    priority3 = []

    for ride in rides:
        ride_coordinates = (float(ride['latitude']), float(ride['longitude']))
        distance = calculate_distance(your_coordinates, ride_coordinates)
        time_match = within_time_range(your_time, ride['time'])

        if distance <= 5 and time_match:
            priority1.append(ride)
        elif distance <= 5 and not time_match:
            priority2.append(ride)
        elif distance > 5 and time_match:
            priority3.append(ride)

    return priority1, priority2, priority3

def filter_available_trips(trip_data, travel_time, destination):
    # Filter trip data based on time and destination
    filtered_trip_data = trip_data[(trip_data['time'] == travel_time) & (trip_data['destination'] == destination)]
    
    # Assign priority to each trip based on some criteria
    # Example: Assign higher priority to trips with fewer seats available if 'total_seats' is available
    if 'total_seats' in filtered_trip_data.columns:
        filtered_trip_data['priority'] = filtered_trip_data['total_seats'] - filtered_trip_data['booked_seats']
    else:
        # Handle the case where 'total_seats' column is not present
        filtered_trip_data['priority'] = 0

    # Sort the trips based on priority in descending order
    filtered_trip_data = filtered_trip_data.sort_values(by='priority', ascending=False)

    # Convert filtered trip data to a list of dictionaries
    available_trips = filtered_trip_data.to_dict(orient='records')

    return available_trips

@app.route('/available')
def available():
    # Assuming you have the trip details (time and destination) from the form submission
    # For example, you can get them from request.args or request.form
    
    # Fetch trip details (time and destination) from the form submission
    travel_time = request.args.get('travel_time')
    destination = request.args.get('destination')
    
    # Read the trip data from trip.csv
    trip_data = pd.read_csv('C:\\Users\\Eshwar\\Desktop\\PassPool\\data\\trip.csv')

    # Filter and prioritize available trips
    available_trips = filter_available_trips(trip_data, travel_time, destination)
    
    # Pass the available trip data to the template for rendering
    return render_template('available.html', available_trips=available_trips)

@app.route('/trip-details', methods=['POST'])
def trip_details():
    registration_number = request.form.get('registration_number')

    with open('trip.csv', 'r') as file:
        csv_reader = csv.DictReader(file)
        trip_data = [row for row in csv_reader if row['registration_number'] == registration_number]

    if len(trip_data) == 0:
        return "Registration number not found!"

    your_coordinates = (float(request.form.get('latitude')), float(request.form.get('longitude')))
    your_time = request.form.get('time')

    your_trip_details = trip_data[0]

    available_rides_priority1, available_rides_priority2, available_rides_priority3 = filter_rides(your_coordinates, trip_data, your_time)

    return render_template('trip_details.html', trip=your_trip_details, available_rides_priority1=available_rides_priority1, available_rides_priority2=available_rides_priority2, available_rides_priority3=available_rides_priority3)

if __name__ == '__main__':
    app.run(debug=True)