import time
import threading
from flask import Flask, render_template, jsonify, request
import sqlite3
from datetime import datetime
from twitch_api import is_streamer_live, get_oauth_token  # Import the correct functions
import requests

app = Flask(__name__)

TWITCH_CLIENT_ID = 'ecdpc7s5fb0lgue3b93lig6ayxvcia'  # Replace with your Twitch Client ID
TWITCH_CLIENT_SECRET = '0zxck8bu8h1gjc2n28cdfwcyh4k79k'  # Replace with your Twitch Client Secret

DATABASE = 'twitch_tracker.db'

# Global cache dictionary to store follower counts
follower_cache = {}

# List of streamers to monitor
streamers_to_track = ['sydderslmao', 'sharpwells', 'led_mobile', 'zobo07', 'antioscar_', 'damian8134']

def get_user_id(username):
    oauth_token = get_oauth_token()
    url = f'https://api.twitch.tv/helix/users'
    headers = {
        'Client-ID': TWITCH_CLIENT_ID,
        'Authorization': f'Bearer {oauth_token}'
    }
    params = {
        'login': username  # The Twitch username
    }
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        user_data = response.json()
        if user_data['data']:
            user_id = user_data['data'][0]['id']
            return user_id
    return None

# Function to check if a streamer is live and add a stream (only once per day)
def check_and_add_stream(streamer_name):
    try:
        if is_streamer_live(streamer_name):
            add_stream(streamer_name)
        else:
            print(f"{streamer_name} is not live.")
    except Exception as e:
        print(f"Error checking {streamer_name}: {e}")

# Function to add a stream to the database
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

# Function to get the database connection
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # This helps retrieve data as a dictionary
    return conn

# Function to get follower count with caching
def get_follower_count(username):
    """Fetch follower count from Twitch API."""
    if username in follower_cache:
        # Return the cached value if available
        return follower_cache[username]

    try:
        oauth_token = get_oauth_token()
        user_id = get_user_id(username)
        if not user_id:
            return 0  # Return 0 if user ID is not found
        
        url = f'https://api.twitch.tv/helix/channels/followers?broadcaster_id={user_id}'
        headers = {
            'Client-ID': TWITCH_CLIENT_ID,
            'Authorization': f'Bearer {oauth_token}'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            user_data = response.json()
            follower_count = user_data.get('total', 0)
            
            # Cache the result for future use
            follower_cache[username] = follower_count
            return follower_count
    except Exception as e:
        print(f"Error in get_follower_count for {username}: {e}")
    
    return 0  # Default value in case of an error

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

@app.route('/')
def home():
    conn = get_db()
    cursor = conn.cursor()

    # Retrieve all streamers and their streams count
    cursor.execute('SELECT name, streams_this_year FROM streamers')
    streamers_data = cursor.fetchall()

    # Create a list to hold the final data
    streamers = []
    
    for row in streamers_data:
        name = row["name"]
        streams_this_year = row["streams_this_year"]
        
        # Fetch follower count using the get_follower_count function
        follower_count = get_follower_count(name)
        
        streamers.append({
            "name": name,
            "streams_this_year": streams_this_year,
            "follower_count": follower_count
        })

    conn.close()

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
