import requests
import time
import json
import os
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("roblox_bot.log"),
        logging.StreamHandler()
    ]
)

class RobloxFriendBot:
    def __init__(self, cookie=None):
        """
        Initialize the Roblox Friend Bot
        
        Args:
            cookie (str, optional): The .ROBLOSECURITY cookie. If not provided, will look for ROBLOSECURITY env var.
        """
        self.session = requests.Session()
        self.csrf_token = None
        self.user_id = None
        self.username = None
        
        # Set the cookie from parameter or environment variable
        if cookie:
            self.cookie = cookie
        else:
            self.cookie = os.environ.get('ROBLOSECURITY')
            
        if not self.cookie:
            raise ValueError("No ROBLOSECURITY cookie provided. Please set it as an environment variable or pass it to the constructor.")
            
        # Set the cookie in the session
        self.session.cookies['.ROBLOSECURITY'] = self.cookie
        
        # Common headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.roblox.com/',
            'Origin': 'https://www.roblox.com',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json'
        })
        
        # Initialize CSRF token and verify login
        self._refresh_csrf_token()
        self._get_user_info()
        
    def _refresh_csrf_token(self):
        """Get a new CSRF token using multiple methods for reliability"""
        # Method 1: Account settings endpoint
        try:
            response = self.session.post('https://accountsettings.roblox.com/v1/email', json={}, allow_redirects=False)
            if 'x-csrf-token' in response.headers:
                self.csrf_token = response.headers['x-csrf-token']
                self.session.headers['X-CSRF-TOKEN'] = self.csrf_token
                logging.info("CSRF token refreshed successfully using account settings endpoint")
                return True
            else:
                logging.warning(f"Failed to get CSRF token from account settings endpoint. Status: {response.status_code}")
                logging.debug(f"Response headers: {dict(response.headers)}")
        except Exception as e:
            logging.warning(f"Error refreshing CSRF token via account settings endpoint: {e}")
            
        # Method 2: Friends endpoint
        try:
            response = self.session.post('https://friends.roblox.com/v1/users/1/request-friendship', json={}, allow_redirects=False)
            if 'x-csrf-token' in response.headers:
                self.csrf_token = response.headers['x-csrf-token']
                self.session.headers['X-CSRF-TOKEN'] = self.csrf_token
                logging.info("CSRF token refreshed successfully using friends endpoint")
                return True
            else:
                logging.warning(f"Failed to get CSRF token from friends endpoint. Status: {response.status_code}")
                logging.debug(f"Response headers: {dict(response.headers)}")
        except Exception as e:
            logging.warning(f"Error refreshing CSRF token via friends endpoint: {e}")
            
        # Method 3: Avatar endpoint
        try:
            response = self.session.post('https://avatar.roblox.com/v1/avatar/set-wearing-assets', json={"assetIds":[]}, allow_redirects=False)
            if 'x-csrf-token' in response.headers:
                self.csrf_token = response.headers['x-csrf-token']
                self.session.headers['X-CSRF-TOKEN'] = self.csrf_token
                logging.info("CSRF token refreshed successfully using avatar endpoint")
                return True
            else:
                logging.warning(f"Failed to get CSRF token from avatar endpoint. Status: {response.status_code}")
                logging.debug(f"Response headers: {dict(response.headers)}")
        except Exception as e:
            logging.warning(f"Error refreshing CSRF token via avatar endpoint: {e}")
            
        # Method 4: Groups endpoint
        try:
            response = self.session.post('https://groups.roblox.com/v1/groups/search', json={"keyword":"", "limit":10}, allow_redirects=False)
            if 'x-csrf-token' in response.headers:
                self.csrf_token = response.headers['x-csrf-token']
                self.session.headers['X-CSRF-TOKEN'] = self.csrf_token
                logging.info("CSRF token refreshed successfully using groups endpoint")
                return True
            else:
                logging.error("Failed to get CSRF token from all methods")
                logging.debug(f"Response headers: {dict(response.headers)}")
                return False
        except Exception as e:
            logging.error(f"Error refreshing CSRF token via groups endpoint: {e}")
            return False
            
    def _get_user_info(self):
        """Get current user information to verify login"""
        try:
            response = self.session.get('https://users.roblox.com/v1/users/authenticated')
            if response.status_code == 200:
                data = response.json()
                self.user_id = data.get('id')
                self.username = data.get('name')
                logging.info(f"Logged in as {self.username} (ID: {self.user_id})")
                return True
            elif response.status_code == 401:
                logging.error("Authentication failed. Please check your .ROBLOSECURITY cookie.")
                logging.debug(f"Response: {response.text}")
                return False
            else:
                logging.error(f"Failed to get user info: {response.status_code} - {response.text}")
                logging.debug(f"Response headers: {dict(response.headers)}")
                return False
        except Exception as e:
            logging.error(f"Error getting user info: {e}")
            return False
            
    def get_friend_requests(self):
        """Get all pending friend requests"""
        try:
            response = self.session.get('https://friends.roblox.com/v1/my/friends/requests')
            if response.status_code == 200:
                data = response.json()
                requests_data = data.get('data', [])
                logging.info(f"Found {len(requests_data)} pending friend requests")
                # Print detailed information about each request for debugging
                for i, request in enumerate(requests_data):
                    requester_id = request.get('requesterUserId')
                    requester_name = request.get('requesterUsername', 'Unknown')
                    logging.info(f"Request {i+1}: User {requester_name} (ID: {requester_id})")
                return requests_data
            elif response.status_code in [401, 403]:
                logging.warning(f"Authentication failed ({response.status_code}), refreshing CSRF token")
                if 'x-csrf-token' in response.headers:
                    self.csrf_token = response.headers['x-csrf-token']
                    self.session.headers['X-CSRF-TOKEN'] = self.csrf_token
                    logging.info("CSRF token refreshed from error response")
                    time.sleep(1)  # Brief pause before retry
                    return self.get_friend_requests()
                else:
                    self._refresh_csrf_token()
                    time.sleep(1)  # Brief pause before retry
                    return self.get_friend_requests()
            else:
                logging.error(f"Failed to get friend requests: {response.status_code} - {response.text}")
                logging.debug(f"Response headers: {dict(response.headers)}")
                return []
        except Exception as e:
            logging.error(f"Error getting friend requests: {e}")
            return []
            
    def accept_friend_request(self, requester_id):
        """Accept a friend request from a specific user"""
        try:
            # Ensure we have a valid CSRF token before attempting to accept
            if not self.csrf_token:
                logging.warning("No CSRF token available, refreshing before accepting request")
                self._refresh_csrf_token()
                
            url = f'https://friends.roblox.com/v1/users/{requester_id}/accept-friend-request'
            logging.info(f"Sending accept request to: {url}")
            logging.info(f"Using CSRF token: {self.csrf_token}")
            
            # Print all headers for debugging
            logging.debug(f"Request headers: {dict(self.session.headers)}")
            
            response = self.session.post(url, json={})
            
            # Log the complete response for debugging
            logging.info(f"Accept response status: {response.status_code}")
            logging.info(f"Accept response body: {response.text}")
            
            if response.status_code == 200:
                logging.info(f"Successfully accepted friend request from user ID: {requester_id}")
                return True
            elif response.status_code == 403:
                logging.warning(f"Received 403 when accepting request. Response: {response.text}")
                if 'x-csrf-token' in response.headers:
                    logging.warning("CSRF token expired, refreshing from response headers")
                    self.csrf_token = response.headers['x-csrf-token']
                    self.session.headers['X-CSRF-TOKEN'] = self.csrf_token
                    time.sleep(1)  # Brief pause before retry
                    return self.accept_friend_request(requester_id)
                else:
                    logging.warning("CSRF token expired, refreshing via method")
                    self._refresh_csrf_token()
                    time.sleep(1)  # Brief pause before retry
                    return self.accept_friend_request(requester_id)
            else:
                logging.error(f"Failed to accept friend request from {requester_id}: {response.status_code} - {response.text}")
                logging.debug(f"Response headers: {dict(response.headers)}")
                
                # Try an alternative endpoint as a fallback
                return self._accept_friend_request_alternative(requester_id)
        except Exception as e:
            logging.error(f"Error accepting friend request: {e}")
            return False
    
    def _accept_friend_request_alternative(self, requester_id):
        """Alternative method to accept friend requests if the primary method fails"""
        try:
            # Try the alternative endpoint
            url = f'https://friends.roblox.com/v1/users/{requester_id}/accept-request'
            logging.info(f"Trying alternative accept endpoint: {url}")
            
            response = self.session.post(url, json={})
            logging.info(f"Alternative accept response status: {response.status_code}")
            logging.info(f"Alternative accept response body: {response.text}")
            
            if response.status_code == 200:
                logging.info(f"Successfully accepted friend request using alternative endpoint from user ID: {requester_id}")
                return True
            else:
                logging.error(f"Alternative endpoint also failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logging.error(f"Error in alternative accept method: {e}")
            return False
            
    def run_forever(self, check_interval=10):  # Reduced interval for faster response
        """
        Run the bot continuously, checking for and accepting friend requests
        
        Args:
            check_interval (int): How often to check for new friend requests, in seconds
        """
        logging.info(f"Bot started. Checking for friend requests every {check_interval} seconds")
        print(f"Bot started. Checking for friend requests every {check_interval} seconds")
        print(f"Logged in as {self.username} (ID: {self.user_id})")
        
        retry_count = 0
        max_retries = 5
        
        while True:
            try:
                # Check if we're still logged in
                if not self._get_user_info():
                    logging.warning("Session may have expired, refreshing login")
                    print("Session may have expired, refreshing login")
                    self._refresh_csrf_token()
                    retry_count += 1
                    
                    if retry_count >= max_retries:
                        logging.error(f"Failed to authenticate after {max_retries} attempts. Waiting longer before retry.")
                        print(f"Failed to authenticate after {max_retries} attempts. Waiting longer before retry.")
                        time.sleep(check_interval * 2)  # Wait longer before next attempt
                        retry_count = 0
                    
                    continue
                
                # Reset retry count on successful authentication
                retry_count = 0
                
                # Get and process friend requests
                print("Checking for new friend requests...")
                requests = self.get_friend_requests()
                
                if not requests:
                    print("No pending friend requests found.")
                else:
                    print(f"Found {len(requests)} pending friend requests!")
                
                for request in requests:
                    requester_id = request.get('requesterUserId')
                    requester_name = request.get('requesterUsername', 'Unknown')
                    
                    if requester_id:
                        print(f"Processing friend request from {requester_name} (ID: {requester_id})")
                        logging.info(f"Processing friend request from {requester_name} (ID: {requester_id})")
                        success = self.accept_friend_request(requester_id)
                        if success:
                            print(f"✅ Successfully accepted friend request from {requester_name}")
                            logging.info(f"Successfully accepted friend request from {requester_name}")
                        else:
                            print(f"❌ Failed to accept friend request from {requester_name}")
                            logging.warning(f"Failed to accept friend request from {requester_name}")
                
                # Wait before checking again
                print(f"Waiting {check_interval} seconds before checking again...")
                time.sleep(check_interval)
                
            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                print(f"Error in main loop: {e}")
                retry_count += 1
                
                if retry_count >= max_retries:
                    logging.error(f"Too many errors ({max_retries}). Waiting longer before retry.")
                    print(f"Too many errors ({max_retries}). Waiting longer before retry.")
                    time.sleep(check_interval * 2)  # Wait longer before next attempt
                    retry_count = 0
                else:
                    # Don't exit the loop, just wait and try again
                    time.sleep(check_interval)


if __name__ == "__main__":
    # Instructions for Replit
    print("Roblox Friend Request Auto-Accepter Bot")
    print("======================================")
    print("This bot will automatically accept all friend requests.")
    print("To use this bot, you need to set your .ROBLOSECURITY cookie.")
    print("\nYou can set it as an environment variable in Replit:")
    print("1. Click on the lock icon in the left sidebar")
    print("2. Add a new secret with key 'ROBLOSECURITY' and your cookie as the value")
    print("\nAlternatively, you can modify this script to hardcode your cookie (not recommended)")
    
    # Check if ROBLOSECURITY is set
    if not os.environ.get('ROBLOSECURITY'):
        print("\nWARNING: ROBLOSECURITY environment variable not found!")
        print("The bot will not work until you set this.")
        print("Waiting for 10 seconds before attempting to start anyway...")
        time.sleep(10)
    
    try:
        # Create and run the bot
        bot = RobloxFriendBot()
        bot.run_forever()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please set your .ROBLOSECURITY cookie and try again.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        print("The bot has crashed. Please check the logs for details.")
