import os
import time
import logging
from roblox_friend_bot import RobloxFriendBot

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("replit_bot.log"),
        logging.StreamHandler()
    ]
)

# Main entry point for Replit
def main():
    print("Roblox Friend Request Auto-Accepter Bot")
    print("======================================")
    print("Starting bot...")
    
    # Check if ROBLOSECURITY is set
    if not os.environ.get('ROBLOSECURITY'):
        print("\nWARNING: ROBLOSECURITY environment variable not found!")
        print("Please set your .ROBLOSECURITY cookie in the Secrets tab (lock icon)")
        print("The bot will not work until you set this.")
        
        # In Replit, we'll keep the script running so users can set the env var
        while not os.environ.get('ROBLOSECURITY'):
            print("Waiting for ROBLOSECURITY to be set... (checking every 30 seconds)")
            time.sleep(30)
    
    try:
        # Create and run the bot
        print("Initializing bot with your security token...")
        bot = RobloxFriendBot()
        print(f"Successfully logged in as {bot.username} (ID: {bot.user_id})")
        print("Bot is now running and will accept all friend requests automatically")
        print("Keep this Replit running to continue accepting friend requests")
        print("======================================")
        
        # Run the bot forever
        bot.run_forever()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please set your .ROBLOSECURITY cookie correctly and try again.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        print("The bot has crashed. Please check the logs for details.")

if __name__ == "__main__":
    main()
