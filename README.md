# mastodon-cli-tools
mastodon cli tools



# Mastodon CLI Tools

For now this is a simple command-line tool to post messages to Mastodon instances.
Available in both Bash and Python versions.

## Quick Start

### Bash Version
```bash
chmod +x mastodon_post.sh
./mastodon_post.sh --setup
./mastodon_post.sh "Hello from the command line!"
```

### Python Version
```bash
pip install requests
python mastodon_post.py --setup
python mastodon_post.py "Hello from the command line!"
```

## Setup

Either versions require a one-time setup to get your Mastodon access token but the setup works for both:

1. Run the setup command
2. Enter your Mastodon instance URL (e.g., `https://mastodon.social`)
3. Go to your instance's `/settings/applications` page
4. Create a new application with default scopes, I allowed it to write posts.
5. Copy the access token and paste it when prompted

Configuration is stored in `~/.config/mastodon_cli.conf`

## Usage

```bash
# Post a simple message
./mastodon_post.sh "Just posted from the terminal!"

# Python version
python mastodon_post.py "Just posted from the terminal!"

# Reconfigure
./mastodon_post.sh --setup
```

## Features

- ✅ Simple setup with access token
- ✅ Posts text messages
- ✅ Returns URL of posted message
- ✅ Handles Cloudflare protection with proper User-Agent
- ✅ Cross-platform (Bash for Unix-like systems, Python for anywhere)

## Future Improvements

### Content Features
- [ ] **Media attachments** - Upload and attach images, videos, audio files
- [ ] **Content warnings** - Add CW/spoiler tags to posts
- [ ] **Custom visibility** - Support for public, unlisted, private, direct messages
- [ ] **Reply threading** - Reply to existing posts by ID
- [ ] **Polls** - Create polls with multiple options and expiration times
- [ ] **Scheduled posts** - Schedule posts for later publishing
- [ ] **Hashtag suggestions** - Auto-suggest relevant hashtags
- [ ] **Emoji support** - Custom emoji insertion and Unicode emoji shortcuts

### Input/Output Features
- [ ] **Pipe input** - Read message from stdin: `echo "Hello" | ./mastodon_post.sh`
- [ ] **File input** - Post contents of a file: `./mastodon_post.sh --file message.txt`
- [ ] **Interactive mode** - Multi-line composer with preview
- [ ] **Template support** - Predefined message templates with variables
- [ ] **Draft saving** - Save drafts locally before posting
- [ ] **Post history** - Local log of posted messages
- [ ] **Bulk posting** - Post multiple messages from a file/list

### Timeline Features
- [ ] **Read timeline** - View home, local, federated timelines
- [ ] **Notifications** - Check mentions, favorites, boosts
- [ ] **Search** - Search for posts, users, hashtags
- [ ] **User profiles** - View user information and post history
- [ ] **Bookmarks** - View and manage bookmarked posts

### Account Management
- [ ] **Multi-account support** - Switch between different Mastodon accounts
- [ ] **Profile management** - Update bio, avatar, header, display name
- [ ] **Following/followers** - Manage who you follow
- [ ] **Blocking/muting** - Manage blocked and muted accounts
- [ ] **List management** - Create and manage user lists

### Advanced Features
- [ ] **OAuth flow** - Proper OAuth instead of manual token entry
- [ ] **Rate limiting** - Respect API rate limits with backoff
- [ ] **Retry logic** - Automatic retry on temporary failures
- [ ] **Batch operations** - Efficiently handle multiple requests
- [ ] **Streaming API** - Real-time timeline updates
- [ ] **Webhook support** - Trigger posts from external events

### User Experience
- [ ] **Progress indicators** - Show upload progress for media
- [ ] **Error handling** - Better error messages and recovery suggestions
- [ ] **Validation** - Pre-validate posts (length, media size, etc.)
- [ ] **Confirmation prompts** - Confirm before posting sensitive content
- [ ] **Undo/delete** - Delete recently posted messages
- [ ] **Edit posts** - Edit posts if instance supports it
- [ ] **Preview mode** - Preview how post will look before publishing

### Integration Features
- [ ] **RSS integration** - Post new items from RSS feeds
- [ ] **Git hooks** - Post commit messages, releases, etc.
- [ ] **Cron scheduling** - Built-in cron-like scheduling
- [ ] **Webhook receiver** - Receive and post webhooks from services
- [ ] **API endpoint** - Simple HTTP API for other tools to use
- [ ] **Browser extension** - Share pages directly from browser

### Configuration & Customization
- [ ] **Config profiles** - Multiple configuration profiles
- [ ] **Default settings** - Set default visibility, CW, etc.
- [ ] **Aliases** - Custom command aliases for frequent actions
- [ ] **Plugin system** - Extensible plugin architecture
- [ ] **Themes** - Customizable output formatting and colors
- [ ] **Keyboard shortcuts** - Hotkeys for common actions

### Developer Features
- [ ] **API documentation** - Full API wrapper documentation
- [ ] **Testing suite** - Comprehensive test coverage
- [ ] **Mock server** - Test against fake Mastodon instance
- [ ] **Debug mode** - Verbose logging and API inspection
- [ ] **Performance metrics** - Timing and usage statistics

## Dependencies

### Bash Version
- `curl` - for HTTP requests
- `jq` (optional) - for better JSON parsing

### Python Version
- `requests` - for HTTP requests
- Python 3.6+ - for pathlib and f-strings

## License

MIT License - feel free to use, modify, and distribute.

## Contributing

Pull requests welcome! Pick any feature from the improvements list above or suggest your own.

## Troubleshooting

**"Blocked by Cloudflare"** - The script includes proper User-Agent headers to avoid this

**"Invalid token"** - Run `--setup` again to get a fresh token

**"Permission denied"** - Make sure the bash script is executable: `chmod +x mastodon_post.sh`
