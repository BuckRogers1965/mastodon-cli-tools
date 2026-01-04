import os
import time
import html
import ollama
from dotenv import load_dotenv
from mastodon import Mastodon

# --- AI Analysis Section for Ollama ---
# Pro: Free, private, fast. Con: Requires running Ollama locally.
def analyze_with_ollama(text):
    """
    Analyzes text using a local Ollama instance and returns True if negative.
    """
    try:
        # This is the "prompt". The quality of your results depends heavily on this.
        # Be very specific and ask for a one-word response to make parsing easy.
        system_prompt = """
        You are a content moderation AI. Analyze the social media post.
        Classify it strictly as one of the following: 'POSITIVE', 'NEUTRAL', or 'NEGATIVE'.
        A 'NEGATIVE' classification is for posts that are insulting, harassing, toxic, aggressive, spam, or hateful.
        Your entire response must be ONLY ONE WORD: POSITIVE, NEUTRAL, or NEGATIVE.
        """

        client = ollama.Client(host=os.getenv("OLLAMA_HOST"))

        response = client.chat(
            model=os.getenv("OLLAMA_MODEL"),
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': text},
            ],
            stream=False # Get the whole response at once
        )
        
        classification = response['message']['content'].strip().upper()
        print(f"  -> Ollama classified as: {classification}")

        # Check if the response is one of the expected words before deciding
        if classification == 'NEGATIVE':
            return True
        elif classification not in ['POSITIVE', 'NEUTRAL']:
            # The model didn't follow instructions, so we play it safe
            print("  -> Warning: Model gave an unexpected response. Treating as non-negative.")
            return False
        
        return False

    except Exception as e:
        print(f"  !! Error connecting to or querying Ollama: {e}")
        print("  !! Is the Ollama application running? Is the model name in .env correct?")
        return False # Fail safe: if AI fails, don't block.

# --- Main Script ---

# Load configuration from .env file
load_dotenv()

# --- CONFIGURATION ---
DRY_RUN = True  # SET TO FALSE TO ACTUALLY BLOCK ACCOUNTS
AI_ANALYZER = analyze_with_ollama # This script is hard-coded for Ollama
PROCESSED_IDS_FILE = "processed_notification_ids.txt"

def load_processed_ids():
    """Loads the set of already processed notification IDs from a file."""
    if not os.path.exists(PROCESSED_IDS_FILE):
        return set()
    with open(PROCESSED_IDS_FILE, 'r') as f:
        return set(line.strip() for line in f)

def save_processed_id(notification_id):
    """Appends a new processed notification ID to the file."""
    with open(PROCESSED_IDS_FILE, 'a') as f:
        f.write(str(notification_id) + '\n')

def main():
    print("--- Mastodon AI Filter Script (Ollama Edition) ---")
    if DRY_RUN:
        print("⚠️  WARNING: Running in DRY RUN mode. No accounts will be blocked.")
    else:
        print("🔴  LIVE MODE: The script WILL block accounts.")
    print(f"Using Ollama model: {os.getenv('OLLAMA_MODEL')} at {os.getenv('OLLAMA_HOST')}")
    print("-----------------------------------------------------")

    # Initialize Mastodon API
    try:
        mastodon = Mastodon(
            client_id=os.getenv('MASTODON_CLIENT_KEY'),
            client_secret=os.getenv('MASTODON_CLIENT_SECRET'),
            access_token=os.getenv('MASTODON_ACCESS_TOKEN'),
            api_base_url=os.getenv('MASTODON_API_BASE_URL')
        )
        my_account = mastodon.me()
        print(f"Successfully connected to Mastodon as '{my_account['username']}'.")
    except Exception as e:
        print(f"❌ Failed to connect to Mastodon. Check your .env settings. Error: {e}")
        return

    processed_ids = load_processed_ids()
    print(f"Loaded {len(processed_ids)} previously processed notification IDs.")

    while True:
        try:
            print("\nChecking for new notifications...")
            notifications = mastodon.notifications(mentions_only=True)
            
            new_notifications = [n for n in notifications if n['id'] not in processed_ids]
            
            if not new_notifications:
                 print("No new mentions found since last check.")

            for notif in reversed(new_notifications): # Process oldest first
                status = notif['status']
                author = status['account']
                # Basic HTML stripping to clean the content for the AI
                content = html.unescape(status['content'].replace('<p>', '').replace('</p>', ''))
                
                print(f"\nProcessing mention from @{author['acct']} (ID: {notif['id']}):")
                print(f"  Content: \"{content[:100].strip()}...\"")

                # Analyze the content using our Ollama function
                is_negative = AI_ANALYZER(content)

                if is_negative:
                    print(f"  🚨 NEGATIVE content detected from @{author['acct']}.")
                    if not DRY_RUN:
                        try:
                            mastodon.account_block(author['id'])
                            print(f"  ✅ SUCCESS: Blocked account @{author['acct']}.")
                        except Exception as e:
                            print(f"  ❌ FAILED to block account @{author['acct']}. Error: {e}")
                    else:
                        print(f"  DRY RUN: Would have blocked account @{author['acct']}.")
                else:
                    print("  - Content seems okay. No action taken.")

                # Mark this notification as processed
                processed_ids.add(notif['id'])
                save_processed_id(notif['id'])

        except Exception as e:
            print(f"\nAn error occurred: {e}")
            print("Waiting for a bit before retrying...")
        
        # Wait for 5 minutes before checking again
        sleep_duration = 300 
        print(f"\nSleeping for {sleep_duration / 60:.0f} minutes...")
        time.sleep(sleep_duration)

if __name__ == "__main__":
    main()
