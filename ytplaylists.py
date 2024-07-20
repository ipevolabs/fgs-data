import os
import googleapiclient.discovery

# Load API key from .env file
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file
api_key = os.getenv('YOUTUBE_API_KEY')

# Set up YouTube Data API client
youtube = googleapiclient.discovery.build(
    'youtube', 'v3', developerKey=api_key
)

def getchannel():
    request = youtube.channels().list(part='id', forUsername='FGSBLTV')  
    response = request.execute()  
    if 'items' in response:  
        channel_id = response['items'][0]['id']  
        print(f"Channel ID: {channel_id}")  
    else:
        print("Channel not found.")

def getplaylist( channel_id):
	# Define the channel ID
	channel_id = 'YOUR_CHANNEL_ID'  # Replace with your channel ID
	# Define the request parameters
	request = youtube.playlists().list(
	    part='snippet',
	    channelId=channel_id,
	    maxResults=50  # Adjust as needed
	)
	# Execute the request and get the response
	response = request.execute()
	# Print the playlist titles
	for item in response['items']:
	    print(item['snippet']['title'])

getchannel()
 
