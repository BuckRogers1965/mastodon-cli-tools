#!/bin/bash

# Simple Mastodon poster using curl
# Usage: ./mastodon_post.sh "Your message here"

CONFIG_FILE="$HOME/.config/mastodon_cli.conf"

setup() {
    echo "Setting up Mastodon CLI poster..."
    
    read -p "Enter your Mastodon instance URL (e.g., https://mastodon.social): " INSTANCE_URL
    
    echo "To get your access token:"
    echo "1. Go to $INSTANCE_URL/settings/applications"
    echo "2. Click 'New Application'"
    echo "3. Give it a name like 'CLI Poster'"
    echo "4. Leave the scopes as default"
    echo "5. Click 'Submit'"
    echo "6. Copy the 'Your access token' value"
    
    read -p "Paste your access token here: " ACCESS_TOKEN
    
    # Create config directory
    mkdir -p "$(dirname "$CONFIG_FILE")"
    
    # Save config
    cat > "$CONFIG_FILE" << EOF
INSTANCE_URL="$INSTANCE_URL"
ACCESS_TOKEN="$ACCESS_TOKEN"
EOF
    
    echo "Setup complete! Config saved to $CONFIG_FILE"
    echo "Now you can post with: $0 'Your message'"
}

post_message() {
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "No config found. Run: $0 --setup"
        exit 1
    fi
    
    source "$CONFIG_FILE"
    
    MESSAGE="$1"
    if [ -z "$MESSAGE" ]; then
        echo "Usage: $0 'Your message here'"
        exit 1
    fi
    
    # Post to Mastodon
    RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -H "User-Agent: MastodonCLI/1.0" \
        -d "{\"status\": \"$MESSAGE\"}" \
        "$INSTANCE_URL/api/v1/statuses")
    
    # Check if successful
    if echo "$RESPONSE" | grep -q '"url"'; then
        URL=$(echo "$RESPONSE" | grep -o '"url":"[^"]*' | cut -d'"' -f4)
        echo "✓ Posted successfully!"
        echo "URL: $URL"
    else
        echo "Error posting:"
        echo "$RESPONSE"
        exit 1
    fi
}

case "$1" in
    --setup)
        setup
        ;;
    *)
        post_message "$1"
        ;;
esac
