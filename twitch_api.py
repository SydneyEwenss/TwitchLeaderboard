import requests

TWITCH_CLIENT_ID = 'ecdpc7s5fb0lgue3b93lig6ayxvcia'  # Replace with your Twitch Client ID
TWITCH_CLIENT_SECRET = '0zxck8bu8h1gjc2n28cdfwcyh4k79k'  # Replace with your Twitch Client Secret

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

# Function to check if the streamer is live
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
        if stream_data['data']:
            return True  # Streamer is live
    return False  # Streamer is not live
