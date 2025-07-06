"""
Mastodon CLI Poster - Python version using requests (equivalent to curl)
Usage: python mastodon_post.py "Your message here"
       python mastodon_post.py --setup
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests library not found.")
    print("Install it with: pip install requests")
    sys.exit(1)

CONFIG_FILE = Path.home() / ".config" / "mastodon_cli.conf"

def setup():
    """Setup Mastodon credentials"""
    print("Setting up Mastodon CLI poster...")
    
    instance_url = input("Enter your Mastodon instance URL (e.g., https://mastodon.social): ").strip()
    
    print(f"To get your access token:")
    print(f"1. Go to {instance_url}/settings/applications")
    print(f"2. Click 'New Application'")
    print(f"3. Give it a name like 'CLI Poster'")
    print(f"4. Leave the scopes as default")
    print(f"5. Click 'Submit'")
    print(f"6. Copy the 'Your access token' value")
    
    access_token = input("Paste your access token here: ").strip()
    
    # Create config directory
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Save config in bash format (same as bash script)
    with open(CONFIG_FILE, 'w') as f:
        f.write(f'INSTANCE_URL="{instance_url}"\n')
        f.write(f'ACCESS_TOKEN="{access_token}"\n')
    
    print(f"Setup complete! Config saved to {CONFIG_FILE}")
    print(f"Now you can post with: python {sys.argv[0]} 'Your message'")

def load_config():
    """Load configuration from bash format"""
    if not CONFIG_FILE.exists():
        print("No config found. Run: python mastodon_post.py --setup")
        sys.exit(1)
    
    try:
        config = {}
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        # Remove quotes if present
                        value = value.strip('"\'')
                        config[key.lower()] = value
        
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

def post_message(message):
    """Post message to Mastodon"""
    config = load_config()
    
    url = f"{config['instance_url']}/api/v1/statuses"
    
    headers = {
        "Authorization": f"Bearer {config['access_token']}",
        "Content-Type": "application/json",
        "User-Agent": "MastodonCLI/1.0"
    }
    
    data = {
        "status": message
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            print("✓ Posted successfully!")
            print(f"URL: {result['url']}")
        else:
            print("Error posting:")
            print(f"Status code: {response.status_code}")
            print(response.text)
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Post to Mastodon from command line')
    parser.add_argument('message', nargs='?', help='Message to post')
    parser.add_argument('--setup', action='store_true', help='Setup Mastodon credentials')
    
    args = parser.parse_args()
    
    if args.setup:
        setup()
    elif args.message:
        post_message(args.message)
    else:
        print("Usage: python mastodon_post.py 'Your message here'")
        print("       python mastodon_post.py --setup")

if __name__ == "__main__":
    main()
