import time
import threading
import requests
from flask import Flask, render_template, jsonify, request
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)

DATABASE = 'twitch_tracker.db'

# Twitch API credentials
TWITCH_CLIENT_ID = 'ecdpc7s5fb0lgue3b93lig6ayxvcia'  # Replace with your Twitch Client ID
TWITCH_CLIENT_SECRET = '0zxck8bu8h1gjc2n28cdfwcyh4k79k'  # Replace with your actual Client Secret

# Utility function to get the SQLite database connection
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # This helps retrieve data as a dictionary
    return conn

# Function to get OAuth token using Client ID and Secret
def get_oauth_token():
    url = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': TWITCH_CLIENT_ID,
        'client_secret': TWITCH_CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, params=params)
    response_data = response.json()
    return response_data['access_token']

# Function to check if a streamer is live
def add_stream(username):
    conn = get_db()
    cursor = conn.cursor()

    # Get today's date in 'YYYY-MM-DD' format
    today_date = datetime.now().strftime('%Y-%m-%d')

    # Check if the streamer has already streamed today
    cursor.execute('''
    SELECT COUNT(*) FROM streams 
    WHERE username = ? AND strftime("%Y-%m-%d", created_at) = ?
    ''', (username, today_date))

    stream_exists = cursor.fetchone()[0]

    if stream_exists:
        print(f"{username} has already streamed today.")
    else:
        # Insert the new stream into the streams table
        cursor.execute('''
        INSERT INTO streams (username, created_at) 
        VALUES (?, ?)
        ''', (username, datetime.now()))

        # Update the streams_this_year count for the streamer
        cursor.execute('''
        UPDATE streamers 
        SET streams_this_year = streams_this_year + 1 
        WHERE name = ?
        ''', (username,))

        print(f"Stream added for {username}.")

    conn.commit()
    conn.close()

# Function to check if the streamer is live and add a stream (only once per day)
def check_and_add_stream(streamer_name):
    if is_streamer_live(streamer_name):
        add_stream(streamer_name)
    else:
        print(f"{streamer_name} is not live.")

# Function to check if a streamer is live
def is_streamer_live(streamer_name):
    oauth_token = get_oauth_token()
    url = f'https://api.twitch.tv/helix/streams?user_login={streamer_name}'
    headers = {
        'Client-ID': TWITCH_CLIENT_ID,
        'Authorization': f'Bearer {oauth_token}'
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        stream_data = response.json()
        if stream_data['data']:  # If there is data, the streamer is live
            return True
    return False

# List of streamers to monitor
streamers_to_track = ['sydderslmao', 'sharpwells', 'led_mobile', 'zobo07', 'antioscar_', 'tcarver180', 'AuggietheCreature']

# Background thread function to monitor streams
def monitor_streams():
    while True:
        for streamer in streamers_to_track:
            check_and_add_stream(streamer)
        time.sleep(300)  # Sleep for 5 minutes (300 seconds)

# Start the monitoring task in a separate thread
def start_monitoring_thread():
    monitoring_thread = threading.Thread(target=monitor_streams)
    monitoring_thread.daemon = True  # Ensures the thread exits when the main program ends
    monitoring_thread.start()

# Route to display streamers on the webpage
@app.route('/')
def home():
    conn = get_db()
    cursor = conn.cursor()

    # Retrieve all streamers and their streams count
    cursor.execute('SELECT name, streams_this_year FROM streamers')
    streamers = [{"name": row["name"], "streams_this_year": row["streams_this_year"]} for row in cursor.fetchall()]

    conn.close()

    # Render the index.html template and pass streamers data
    return render_template('index.html', streamers=streamers)


# Route to add a streamer (API endpoint)
@app.route('/api/streamers', methods=['POST'])
def add_streamer():
    data = request.json
    username = data.get('username')

    if not username:
        return jsonify({"error": "Username is required"}), 400

    # Check how many streams the user has this year
    stream_count = get_stream_count(username)

    # Connect to DB and add the streamer
    conn = get_db()
    cursor = conn.cursor()

    # Insert the streamer into the streamers table if not already present
    cursor.execute('''
    INSERT OR IGNORE INTO streamers (name, streams_this_year) 
    VALUES (?, ?)
    ''', (username, stream_count))
    
    conn.commit()
    conn.close()

    return jsonify({"message": f"Streamer {username} added with {stream_count} streams."})

# Helper function to get stream count for a user in the current year
def get_stream_count(username):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT COUNT(*) FROM streams 
    WHERE username = ? AND strftime("%Y", created_at) = ?
    ''', (username, str(datetime.now().year)))
    count = cursor.fetchone()[0]

    conn.close()
    return count

# Flask route to handle adding a stream
@app.route('/api/streams', methods=['POST'])
def post_stream():
    data = request.json
    username = data.get('username')

    if not username:
        return jsonify({"error": "Username is required"}), 400

    # Call the add_stream function to add the stream and update the count
    add_stream(username)
    return jsonify({"message": f"Stream added for {username}."})

if __name__ == '__main__':
    start_monitoring_thread()  # Start monitoring the streamers in the background
    app.run(host='0.0.0.0', port=5000)
