import requests
import time
import json
import os
import logging
import traceback
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
        methods = [
            {
                "name": "Account settings endpoint",
                "url": "https://accountsettings.roblox.com/v1/email",
                "method": "POST",
                "data": {}
            },
            {
                "name": "Friends endpoint",
                "url": "https://friends.roblox.com/v1/users/1/request-friendship",
                "method": "POST",
                "data": {}
            },
            {
                "name": "Avatar endpoint",
                "url": "https://avatar.roblox.com/v1/avatar/set-wearing-assets",
                "method": "POST",
                "data": {"assetIds":[]}
            },
            {
                "name": "Groups endpoint",
                "url": "https://groups.roblox.com/v1/groups/search",
                "method": "POST",
                "data": {"keyword":"", "limit":10}
            }
        ]
        
        for method in methods:
            try:
                print(f"Trying to get CSRF token from {method['name']}...")
                response = self.session.post(method['url'], json=method['data'], allow_redirects=False)
                print(f"Response status: {response.status_code}")
                
                if 'x-csrf-token' in response.headers:
                    self.csrf_token = response.headers['x-csrf-token']
                    self.session.headers['X-CSRF-TOKEN'] = self.csrf_token
                    print(f"✅ CSRF token obtained successfully from {method['name']}: {self.csrf_token[:5]}...")
                    logging.info(f"CSRF token refreshed successfully using {method['name']}")
                    return True
                else:
                    print(f"❌ Failed to get CSRF token from {method['name']}. Status: {response.status_code}")
                    logging.warning(f"Failed to get CSRF token from {method['name']}. Status: {response.status_code}")
            except Exception as e:
                print(f"❌ Error refreshing CSRF token via {method['name']}: {e}")
                logging.warning(f"Error refreshing CSRF token via {method['name']}: {e}")
        
        print("❌ Failed to get CSRF token from all methods")
        logging.error("Failed to get CSRF token from all methods")
        return False
            
    def _get_user_info(self):
        """Get current user information to verify login"""
        try:
            print("Verifying login by getting user info...")
            response = self.session.get('https://users.roblox.com/v1/users/authenticated')
            print(f"User info response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.user_id = data.get('id')
                self.username = data.get('name')
                print(f"✅ Successfully logged in as {self.username} (ID: {self.user_id})")
                logging.info(f"Logged in as {self.username} (ID: {self.user_id})")
                return True
            elif response.status_code == 401:
                print("❌ Authentication failed. Please check your .ROBLOSECURITY cookie.")
                logging.error("Authentication failed. Please check your .ROBLOSECURITY cookie.")
                return False
            else:
                print(f"❌ Failed to get user info: {response.status_code} - {response.text}")
                logging.error(f"Failed to get user info: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error getting user info: {e}")
            logging.error(f"Error getting user info: {e}")
            return False
            
    def get_friend_requests(self):
        """Get all pending friend requests"""
        try:
            print("Fetching friend requests...")
            response = self.session.get('https://friends.roblox.com/v1/my/friends/requests')
            print(f"Friend requests response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Print the full JSON response for debugging
                print("FULL JSON RESPONSE:")
                print(json.dumps(data, indent=2))
                
                requests_data = data.get('data', [])
                print(f"✅ Found {len(requests_data)} pending friend requests")
                logging.info(f"Found {len(requests_data)} pending friend requests")
                
                # Extract request information with proper error handling
                processed_requests = []
                for i, request in enumerate(requests_data):
                    # Try multiple possible field names for user ID
                    requester_id = None
                    for field in ['requesterUserId', 'userId', 'id', 'requesterId', 'sourceUserId']:
                        if field in request:
                            requester_id = request.get(field)
                            if requester_id:
                                break
                    
                    # If no ID found in direct fields, check nested objects
                    if not requester_id:
                        if 'requester' in request and isinstance(request['requester'], dict):
                            requester_id = request['requester'].get('id') or request['requester'].get('userId')
                        elif 'user' in request and isinstance(request['user'], dict):
                            requester_id = request['user'].get('id') or request['user'].get('userId')
                    
                    # Try multiple possible field names for username
                    requester_name = 'Unknown'
                    for field in ['requesterUsername', 'username', 'name', 'displayName']:
                        if field in request:
                            name = request.get(field)
                            if name:
                                requester_name = name
                                break
                    
                    # If no name found in direct fields, check nested objects
                    if requester_name == 'Unknown':
                        if 'requester' in request and isinstance(request['requester'], dict):
                            requester_name = request['requester'].get('name') or request['requester'].get('username') or request['requester'].get('displayName') or 'Unknown'
                        elif 'user' in request and isinstance(request['user'], dict):
                            requester_name = request['user'].get('name') or request['user'].get('username') or request['user'].get('displayName') or 'Unknown'
                    
                    # If we still don't have an ID but have an originSourceType, this might be a different type of request
                    if not requester_id and 'originSourceType' in request:
                        print(f"⚠️ This appears to be a different type of request with originSourceType: {request.get('originSourceType')}")
                        
                        # For requests with originSourceType, try to find the ID in different locations
                        if 'sourceUserId' in request:
                            requester_id = request.get('sourceUserId')
                        elif 'userId' in request:
                            requester_id = request.get('userId')
                    
                    # If we have an ID, add to processed requests
                    if requester_id:
                        print(f"  Request {i+1}: User {requester_name} (ID: {requester_id})")
                        logging.info(f"Request {i+1}: User {requester_name} (ID: {requester_id})")
                        processed_requests.append({
                            'requesterUserId': requester_id,
                            'requesterUsername': requester_name,
                            'originalData': request  # Keep original data for reference
                        })
                    else:
                        print(f"  ⚠️ Request {i+1}: Could not extract user ID from request data")
                        print(f"  Raw request data: {request}")
                
                return processed_requests
            elif response.status_code in [401, 403]:
                print(f"❌ Authentication failed ({response.status_code}), refreshing CSRF token")
                logging.warning(f"Authentication failed ({response.status_code}), refreshing CSRF token")
                
                if 'x-csrf-token' in response.headers:
                    self.csrf_token = response.headers['x-csrf-token']
                    self.session.headers['X-CSRF-TOKEN'] = self.csrf_token
                    print(f"✅ CSRF token refreshed from error response: {self.csrf_token[:5]}...")
                    logging.info("CSRF token refreshed from error response")
                    time.sleep(1)  # Brief pause before retry
                    return self.get_friend_requests()
                else:
                    print("❌ No CSRF token in response, trying refresh method")
                    self._refresh_csrf_token()
                    time.sleep(1)  # Brief pause before retry
                    return self.get_friend_requests()
            else:
                print(f"❌ Failed to get friend requests: {response.status_code} - {response.text}")
                logging.error(f"Failed to get friend requests: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"❌ Error getting friend requests: {e}")
            logging.error(f"Error getting friend requests: {e}")
            traceback.print_exc()
            return []
    
    def accept_friend_request_direct(self, requester_id):
        """Accept a friend request using direct API call with multiple retries"""
        max_retries = 3
        
        for attempt in range(1, max_retries + 1):
            try:
                print(f"Direct accept attempt {attempt}/{max_retries} for user ID: {requester_id}")
                
                # Ensure we have a valid CSRF token
                if not self.csrf_token:
                    print("No CSRF token available, refreshing before accepting request")
                    self._refresh_csrf_token()
                
                url = f'https://friends.roblox.com/v1/users/{requester_id}/accept-friend-request'
                print(f"Sending accept request to: {url}")
                print(f"Using CSRF token: {self.csrf_token[:5]}...")
                
                # Print all headers for debugging
                print(f"Request headers: X-CSRF-TOKEN: {self.session.headers.get('X-CSRF-TOKEN', 'None')}")
                
                response = self.session.post(url, json={})
                
                # Log the complete response for debugging
                print(f"Accept response status: {response.status_code}")
                print(f"Accept response body: {response.text}")
                
                if response.status_code == 200:
                    print(f"✅ Successfully accepted friend request from user ID: {requester_id}")
                    logging.info(f"Successfully accepted friend request from user ID: {requester_id}")
                    return True
                elif response.status_code == 403:
                    print(f"❌ Received 403 when accepting request. Response: {response.text}")
                    
                    if 'x-csrf-token' in response.headers:
                        print("CSRF token expired, refreshing from response headers")
                        self.csrf_token = response.headers['x-csrf-token']
                        self.session.headers['X-CSRF-TOKEN'] = self.csrf_token
                        print(f"New token: {self.csrf_token[:5]}...")
                        time.sleep(1)  # Brief pause before retry
                    else:
                        print("No token in response headers, refreshing via method")
                        self._refresh_csrf_token()
                        time.sleep(1)  # Brief pause before retry
                else:
                    print(f"❌ Failed with status {response.status_code}: {response.text}")
                    time.sleep(1)  # Brief pause before retry
                    
            except Exception as e:
                print(f"❌ Error in accept attempt {attempt}: {e}")
                traceback.print_exc()
                time.sleep(1)  # Brief pause before retry
        
        # If we get here, try the alternative method
        return self.accept_friend_request_alternative(requester_id)
    
    def accept_friend_request_alternative(self, requester_id):
        """Alternative method to accept friend requests if the primary method fails"""
        alternative_endpoints = [
            f'https://friends.roblox.com/v1/users/{requester_id}/accept-request',
            f'https://friends.roblox.com/v1/users/{requester_id}/request/accept',
            f'https://friends.roblox.com/v1/user/{requester_id}/accept-friend-request'
        ]
        
        for endpoint in alternative_endpoints:
            try:
                print(f"Trying alternative accept endpoint: {endpoint}")
                
                response = self.session.post(endpoint, json={})
                print(f"Alternative accept response status: {response.status_code}")
                print(f"Alternative accept response body: {response.text}")
                
                if response.status_code == 200:
                    print(f"✅ Successfully accepted friend request using alternative endpoint from user ID: {requester_id}")
                    logging.info(f"Successfully accepted friend request using alternative endpoint from user ID: {requester_id}")
                    return True
                else:
                    print(f"❌ Alternative endpoint failed: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"❌ Error in alternative accept method: {e}")
                traceback.print_exc()
        
        # If all alternatives fail, try the web-based approach
        return self.accept_friend_request_web_based(requester_id)
    
    def accept_friend_request_web_based(self, requester_id):
        """Web-based approach to accept friend requests by simulating browser behavior"""
        try:
            print(f"Trying web-based approach for user ID: {requester_id}")
            
            # First, get the CSRF token from the web page
            response = self.session.get('https://www.roblox.com/home')
            if response.status_code != 200:
                print(f"❌ Failed to load home page: {response.status_code}")
                return False
            
            # Now try the web-based accept endpoint
            url = f'https://www.roblox.com/api/friends/acceptfriendrequest'
            payload = {
                'targetUserID': requester_id
            }
            
            response = self.session.post(url, data=payload)
            print(f"Web-based accept response status: {response.status_code}")
            print(f"Web-based accept response body: {response.text}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('success'):
                        print(f"✅ Successfully accepted friend request using web-based approach from user ID: {requester_id}")
                        logging.info(f"Successfully accepted friend request using web-based approach from user ID: {requester_id}")
                        return True
                except:
                    pass
            
            print(f"❌ Web-based approach failed: {response.status_code} - {response.text}")
            return False
            
        except Exception as e:
            print(f"❌ Error in web-based accept method: {e}")
            traceback.print_exc()
            return False
    
    def accept_friend_request(self, requester_id):
        """Master method to accept a friend request using all available methods"""
        print(f"\n==== ACCEPTING FRIEND REQUEST FROM USER ID: {requester_id} ====")
        
        # Try the direct method first
        result = self.accept_friend_request_direct(requester_id)
        
        # If successful, return True
        if result:
            print(f"✅ SUCCESSFULLY ACCEPTED FRIEND REQUEST FROM USER ID: {requester_id}")
            return True
        
        # If we get here, all methods failed
        print(f"❌ ALL METHODS FAILED TO ACCEPT FRIEND REQUEST FROM USER ID: {requester_id}")
        return False
            
    def run_forever(self, check_interval=5):  # Reduced interval for faster response
        """
        Run the bot continuously, checking for and accepting friend requests
        
        Args:
            check_interval (int): How often to check for new friend requests, in seconds
        """
        print("\n==================================================")
        print("🤖 ROBLOX FRIEND REQUEST AUTO-ACCEPTER BOT STARTED")
        print("==================================================\n")
        print(f"⏱️ Checking for friend requests every {check_interval} seconds")
        logging.info(f"Bot started. Checking for friend requests every {check_interval} seconds")
        
        if self.username:
            print(f"👤 Logged in as {self.username} (ID: {self.user_id})")
        else:
            print("❌ Not logged in! Please check your security token.")
        
        retry_count = 0
        max_retries = 5
        
        while True:
            try:
                print("\n--------------------------------------------------")
                print("🔄 CHECKING FOR NEW FRIEND REQUESTS...")
                print("--------------------------------------------------")
                
                # Check if we're still logged in
                if not self._get_user_info():
                    print("❌ Session may have expired, refreshing login")
                    logging.warning("Session may have expired, refreshing login")
                    self._refresh_csrf_token()
                    retry_count += 1
                    
                    if retry_count >= max_retries:
                        print(f"❌ Failed to authenticate after {max_retries} attempts. Waiting longer before retry.")
                        logging.error(f"Failed to authenticate after {max_retries} attempts. Waiting longer before retry.")
                        time.sleep(check_interval * 2)  # Wait longer before next attempt
                        retry_count = 0
                    
                    continue
                
                # Reset retry count on successful authentication
                retry_count = 0
                
                # Get and process friend requests
                requests = self.get_friend_requests()
                
                if not requests:
                    print("ℹ️ No pending friend requests found.")
                else:
                    print(f"🎉 Found {len(requests)} pending friend requests!")
                
                for request in requests:
                    requester_id = request.get('requesterUserId')
                    requester_name = request.get('requesterUsername', 'Unknown')
                    
                    if requester_id:
                        print(f"\n👥 Processing friend request from {requester_name} (ID: {requester_id})")
                        logging.info(f"Processing friend request from {requester_name} (ID: {requester_id})")
                        success = self.accept_friend_request(requester_id)
                        if success:
                            print(f"✅ Successfully accepted friend request from {requester_name}")
                            logging.info(f"Successfully accepted friend request from {requester_name}")
                        else:
                            print(f"❌ Failed to accept friend request from {requester_name}")
                            logging.warning(f"Failed to accept friend request from {requester_name}")
                
                # Wait before checking again
                print(f"\n⏱️ Waiting {check_interval} seconds before checking again...")
                time.sleep(check_interval)
                
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                logging.error(f"Error in main loop: {e}")
                traceback.print_exc()
                retry_count += 1
                
                if retry_count >= max_retries:
                    print(f"❌ Too many errors ({max_retries}). Waiting longer before retry.")
                    logging.error(f"Too many errors ({max_retries}). Waiting longer before retry.")
                    time.sleep(check_interval * 2)  # Wait longer before next attempt
                    retry_count = 0
                else:
                    # Don't exit the loop, just wait and try again
                    time.sleep(check_interval)


if __name__ == "__main__":
    # Instructions for Railway
    print("\n==================================================")
    print("🤖 ROBLOX FRIEND REQUEST AUTO-ACCEPTER BOT")
    print("==================================================\n")
    print("This bot will automatically accept all friend requests.")
    print("To use this bot, you need to set your .ROBLOSECURITY cookie.")
    print("\nYou can set it as an environment variable in Railway:")
    print("Add a variable named 'ROBLOSECURITY' with your cookie as the value")
    
    # Check if ROBLOSECURITY is set
    if not os.environ.get('ROBLOSECURITY'):
        print("\n❌ WARNING: ROBLOSECURITY environment variable not found!")
        print("The bot will not work until you set this.")
        print("Waiting for 10 seconds before attempting to start anyway...")
        time.sleep(10)
    
    try:
        # Create and run the bot
        bot = RobloxFriendBot()
        bot.run_forever()
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("Please set your .ROBLOSECURITY cookie and try again.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()
        print("The bot has crashed. Please check the logs for details.")
