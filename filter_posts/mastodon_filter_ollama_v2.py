import os
import time
import html
import json
import ollama
from dotenv import load_dotenv
from mastodon import Mastodon

# --- CONFIGURATION ---
# ------------------------------------------------------------------------------------
# -- Safety Settings --
DRY_RUN = True  # SET TO FALSE to enable actual muting and blocking.
ALLOWLIST = [
    "friend@mastodon.social", 
    "another_friend@example.com",
    "news_bot_i_like@botsin.space"
] # Usernames (@user@instance) that will NEVER be muted or blocked.

# -- AI & Action Settings --
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# -- Script Behavior --
POLL_INTERVAL_SECONDS = 300  # 300 seconds = 5 minutes
PROCESSED_IDS_FILE = "processed_notification_ids.txt"
# ------------------------------------------------------------------------------------

# --- AI Analysis Section for Ollama (V2 with JSON output) ---
def analyze_with_ollama(text):
    """
    Analyzes text using Ollama and expects a structured JSON response.
    Returns a dictionary like {'classification': 'NEUTRAL', 'reason': '...'}
    """
    # This prompt is the "brain" of the operation. It's engineered to return structured JSON.
    system_prompt = """
    You are a content moderation AI. Analyze the social media post.
    Classify the post's tone and intent into one of three categories:
    1.  'NEUTRAL': Normal conversation, questions, positive remarks, or neutral statements.
    2.  'MILDLY_NEGATIVE': Grumpy, sarcastic, dismissive, or passive-aggressive, but not directly abusive.
    3.  'SEVERELY_NEGATIVE': Direct insults, harassment, hate speech, toxic behavior, or aggressive spam.

    You MUST respond with a valid JSON object containing two keys:
    - "classification": One of the three categories above.
    - "reason": A brief, one-sentence explanation for your classification.

    Example Response:
    {
      "classification": "SEVERELY_NEGATIVE",
      "reason": "The post contains a direct personal insult."
    }
    """
    try:
        client = ollama.Client(host=OLLAMA_HOST)
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': text},
            ],
            options={'temperature': 0.0}, # Lower temperature for more deterministic output
            format="json" # Tell Ollama to strictly output JSON
        )
        
        response_text = response['message']['content']
        ai_decision = json.loads(response_text)
        
        # Validate the received data
        if 'classification' in ai_decision and 'reason' in ai_decision:
            print(f"  -> Ollama classified as: {ai_decision['classification']}")
            print(f"  -> Reason: {ai_decision['reason']}")
            return ai_decision
        else:
            raise ValueError("JSON response is missing required keys.")

    except Exception as e:
        print(f"  !! Error processing Ollama response: {e}")
        # Fail safe: if AI fails or returns malformed data, take no action.
        return {'classification': 'NEUTRAL', 'reason': 'AI analysis failed.'}

# --- Action & Safety Section ---
def take_action(mastodon, author, decision):
    """Decides whether to mute, block, or do nothing based on AI decision and allowlist."""
    author_id = author['id']
    author_acct = author['acct']
    classification = decision.get('classification', 'NEUTRAL')

    # SAFETY CHECK: Is the user on the allowlist?
    if author_acct in ALLOWLIST:
        print(f"  - Author @{author_acct} is on the allowlist. No action taken.")
        return

    action_taken = None
    if classification == 'MILDLY_NEGATIVE':
        print(f"  MODERATE ACTION: Muting user @{author_acct}.")
        if not DRY_RUN:
            mastodon.account_mute(author_id)
            action_taken = "Muted"
        else:
            action_taken = "Would have Muted"
            
    elif classification == 'SEVERELY_NEGATIVE':
        print(f"  SEVERE ACTION: Blocking user @{author_acct}.")
        if not DRY_RUN:
            mastodon.account_block(author_id)
            action_taken = "Blocked"
        else:
            action_taken = "Would have Blocked"
    else:
        print("  - Content seems okay. No action taken.")
        return

    if DRY_RUN:
        print(f"  DRY RUN: {action_taken} @{author_acct}.")
    else:
        print(f"  ✅ SUCCESS: {action_taken} @{author_acct}.")


# --- Main Script Logic ---
def load_processed_ids():
    if not os.path.exists(PROCESSED_IDS_FILE): return set()
    with open(PROCESSED_IDS_FILE, 'r') as f: return set(line.strip() for line in f)

def save_processed_id(notification_id):
    with open(PROCESSED_IDS_FILE, 'a') as f: f.write(str(notification_id) + '\n')

def main():
    print("--- Mastodon AI Content Filter v2 (Mute/Block) ---")
    if DRY_RUN:
        print("⚠️  WARNING: Running in DRY RUN mode. No actions will be performed.")
    else:
        print("🔴  LIVE MODE: The script WILL mute and block accounts.")
    print("-----------------------------------------------------")

    load_dotenv()
    try:
        mastodon = Mastodon(
            access_token=os.getenv('MASTODON_ACCESS_TOKEN'),
            api_base_url=os.getenv('MASTODON_API_BASE_URL')
        )
        print(f"Successfully connected to Mastodon as '{mastodon.me()['username']}'.")
    except Exception as e:
        print(f"❌ Failed to connect to Mastodon. Check your .env settings. Error: {e}")
        return

    processed_ids = load_processed_ids()

    while True:
        try:
            print(f"\nChecking for new notifications...")
            notifications = mastodon.notifications(mentions_only=True)
            new_notifications = [n for n in notifications if str(n['id']) not in processed_ids]

            if not new_notifications:
                print("No new mentions found since last check.")
            
            for notif in reversed(new_notifications):
                status = notif['status']
                author = status['account']
                content = html.unescape(status['content'].replace('<p>', '').replace('</p>', ''))

                print(f"\nProcessing mention from @{author['acct']} (ID: {notif['id']}):")
                print(f"  Content: \"{content[:100].strip()}...\"")

                ai_decision = analyze_with_ollama(content)
                take_action(mastodon, author, ai_decision)
                
                processed_ids.add(str(notif['id']))
                save_processed_id(notif['id'])

        except Exception as e:
            print(f"\nAn error occurred in the main loop: {e}")
        
        print(f"\nSleeping for {POLL_INTERVAL_SECONDS} seconds...")
        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
