import os
import time
import html
import json
import logging
import ollama
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, Optional, List
from dataclasses import dataclass
from dotenv import load_dotenv
from mastodon import Mastodon
from dateutil import parser as date_parser

# --- CONFIGURATION ---
@dataclass
class Config:
    """Centralized configuration with validation"""
    dry_run: bool = True
    allowlist: List[str] = None
    ollama_model: str = "llama3:8b"
    ollama_host: str = "http://localhost:11434"
    poll_interval: int = 300
    processed_ids_file: str = "processed_notification_ids.txt"
    log_file: str = "mastodon_filter.log"
    max_retries: int = 3
    retry_delay: int = 5
    
    # New: Action escalation - require multiple infractions before blocking
    mute_threshold: int = 1  # Mute after 1 mildly negative post
    block_threshold: int = 3  # Block after 3 total infractions
    infractions_file: str = "user_infractions.json"
    send_warnings: bool = True  # Send educational DMs to users
    warning_visibility: str = "direct"  # 'direct', 'unlisted', or 'private'
    
    # New account handling - likely harassment alts
    new_account_days: int = 30  # Accounts newer than this are "new"
    new_account_instant_block: bool = True  # Block new accounts immediately if hostile
    new_account_no_warning: bool = True  # Skip warnings for new hostile accounts
    
    def __post_init__(self):
        if self.allowlist is None:
            self.allowlist = [
                "friend@mastodon.social",
                "another_friend@example.com",
                "news_bot_i_like@botsin.space"
            ]

# --- LOGGING SETUP ---
def setup_logging(log_file: str):
    """Configure structured logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# --- INFRACTION TRACKING ---
class InfractionTracker:
    """Track user infractions over time"""
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.infractions = self._load()
    
    def _load(self) -> Dict:
        if not self.file_path.exists():
            return {}
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    
    def _save(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.infractions, f, indent=2)
    
    def add_infraction(self, user_acct: str, classification: str, reason: str):
        if user_acct not in self.infractions:
            self.infractions[user_acct] = {
                'count': 0,
                'history': []
            }
        
        self.infractions[user_acct]['count'] += 1
        self.infractions[user_acct]['history'].append({
            'timestamp': datetime.now().isoformat(),
            'classification': classification,
            'reason': reason
        })
        self._save()
    
    def get_count(self, user_acct: str) -> int:
        return self.infractions.get(user_acct, {}).get('count', 0)
    
    def reset(self, user_acct: str):
        if user_acct in self.infractions:
            del self.infractions[user_acct]
            self._save()

# --- AI ANALYSIS ---
class AIAnalyzer:
    """Handles AI-based content analysis with retry logic"""
    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.client = ollama.Client(host=config.ollama_host)
    
    def analyze(self, text: str) -> Dict:
        """Analyze text with retry logic and better error handling"""
        system_prompt = """
You are a content moderation AI. Analyze the social media post objectively.
Classify the post's tone and intent into one of three categories:

1. 'NEUTRAL': Normal conversation, questions, constructive criticism, positive remarks, or neutral statements.
2. 'MILDLY_NEGATIVE': Grumpy, sarcastic, dismissive, or passive-aggressive, but not directly abusive.
3. 'SEVERELY_NEGATIVE': Direct insults, harassment, hate speech, threats, toxic behavior, or aggressive spam.

IMPORTANT: Consider context. Political disagreement, criticism of ideas, or debate is NOT negative.
Focus on personal attacks, toxicity, and harassment.

Respond with valid JSON containing:
- "classification": One of the three categories above.
- "reason": A brief explanation (max 100 chars).
- "confidence": A number from 0.0 to 1.0 indicating your confidence.

Example:
{
  "classification": "SEVERELY_NEGATIVE",
  "reason": "Direct personal insult and threat",
  "confidence": 0.95
}
"""
        
        for attempt in range(self.config.max_retries):
            try:
                response = self.client.chat(
                    model=self.config.ollama_model,
                    messages=[
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': text},
                    ],
                    options={'temperature': 0.1},
                    format="json"
                )
                
                response_text = response['message']['content']
                ai_decision = json.loads(response_text)
                
                # Validate response structure
                required_keys = {'classification', 'reason', 'confidence'}
                if not required_keys.issubset(ai_decision.keys()):
                    raise ValueError(f"Missing required keys: {required_keys - set(ai_decision.keys())}")
                
                # Validate classification value
                valid_classifications = {'NEUTRAL', 'MILDLY_NEGATIVE', 'SEVERELY_NEGATIVE'}
                if ai_decision['classification'] not in valid_classifications:
                    raise ValueError(f"Invalid classification: {ai_decision['classification']}")
                
                self.logger.info(f"AI classified as: {ai_decision['classification']} "
                               f"(confidence: {ai_decision['confidence']:.2f})")
                self.logger.info(f"Reason: {ai_decision['reason']}")
                
                return ai_decision
                
            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1}/{self.config.max_retries} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
                else:
                    self.logger.error("All retry attempts exhausted")
        
        # Fail-safe: default to neutral if AI completely fails
        return {
            'classification': 'NEUTRAL',
            'reason': 'AI analysis failed - defaulting to safe classification',
            'confidence': 0.0
        }

# --- ACTION HANDLER ---
class ActionHandler:
    """Handles moderation actions with escalation logic"""
    def __init__(self, config: Config, logger: logging.Logger, tracker: InfractionTracker):
        self.config = config
        self.logger = logger
        self.tracker = tracker
    
    def _is_new_account(self, author: Dict) -> bool:
        """Check if account was created recently"""
        try:
            created_at = date_parser.parse(author['created_at'])
            account_age = (datetime.now(created_at.tzinfo) - created_at).days
            is_new = account_age <= self.config.new_account_days
            
            if is_new:
                self.logger.info(f"Account @{author['acct']} is {account_age} days old (NEW)")
            
            return is_new
        except Exception as e:
            self.logger.error(f"Error checking account age: {e}")
            return False  # Fail safe: treat as established account
    
    def take_action(self, mastodon: Mastodon, author: Dict, decision: Dict, status_id: str = None):
        """Execute moderation action based on AI decision and infraction history"""
        author_id = author['id']
        author_acct = author['acct']
        classification = decision.get('classification', 'NEUTRAL')
        confidence = decision.get('confidence', 0.0)
        
        # Skip if neutral or low confidence
        if classification == 'NEUTRAL':
            self.logger.info(f"No action needed for @{author_acct}")
            return
        
        if confidence < 0.6:
            self.logger.warning(f"Low confidence ({confidence:.2f}) - skipping action for @{author_acct}")
            return
        
        # Check allowlist
        if author_acct in self.config.allowlist:
            self.logger.info(f"@{author_acct} is allowlisted - no action taken")
            return
        
        # Check if this is a new account being hostile (likely harassment alt)
        is_new = self._is_new_account(author)
        if is_new and self.config.new_account_instant_block and classification in ['MILDLY_NEGATIVE', 'SEVERELY_NEGATIVE']:
            self.logger.warning(f"🚨 NEW ACCOUNT being hostile: @{author_acct} - instant block (no warnings)")
            if not self.config.dry_run:
                try:
                    mastodon.account_block(author_id)
                    self.logger.info(f"✅ Blocked new hostile account @{author_acct}")
                except Exception as e:
                    self.logger.error(f"Failed to block @{author_acct}: {e}")
            else:
                self.logger.info(f"DRY RUN: Would have instantly blocked new account @{author_acct}")
            return
        
        # Record infraction (for established accounts)
        if classification in ['MILDLY_NEGATIVE', 'SEVERELY_NEGATIVE']:
            self.tracker.add_infraction(author_acct, classification, decision['reason'])
        
        infraction_count = self.tracker.get_count(author_acct)
        
        # Send warning if enabled (skip for new accounts if configured)
        if self.config.send_warnings and status_id:
            if not (is_new and self.config.new_account_no_warning):
                self._send_warning(mastodon, author_acct, status_id, infraction_count, classification)
        
        # Determine action based on severity and history
        action = self._determine_action(classification, infraction_count)
        
        if action == 'none':
            self.logger.info(f"Tracking infraction #{infraction_count} for @{author_acct}, no action yet")
            return
        
        # Execute action
        self._execute_action(mastodon, author_id, author_acct, action, infraction_count)
    
    def _determine_action(self, classification: str, infraction_count: int) -> str:
        """Determine what action to take based on classification and history"""
        if classification == 'SEVERELY_NEGATIVE':
            # Immediate block for severe content
            if infraction_count >= self.config.block_threshold:
                return 'block'
            else:
                return 'mute'
        
        elif classification == 'MILDLY_NEGATIVE':
            # Escalate based on repeat offenses
            if infraction_count >= self.config.block_threshold:
                return 'block'
            elif infraction_count >= self.config.mute_threshold:
                return 'mute'
        
        return 'none'
    
    def _execute_action(self, mastodon: Mastodon, author_id: str, 
                       author_acct: str, action: str, infraction_count: int):
        """Execute the moderation action"""
        action_verb = action.upper()
        
        self.logger.warning(f"{action_verb}ING @{author_acct} (infractions: {infraction_count})")
        
        if self.config.dry_run:
            self.logger.info(f"DRY RUN: Would have {action}ed @{author_acct}")
            return
        
        try:
            if action == 'mute':
                mastodon.account_mute(author_id)
            elif action == 'block':
                mastodon.account_block(author_id)
            
            self.logger.info(f"✅ Successfully {action}ed @{author_acct}")
        except Exception as e:
            self.logger.error(f"Failed to {action} @{author_acct}: {e}")

# --- NOTIFICATION PROCESSOR ---
class NotificationProcessor:
    """Handles notification processing and deduplication"""
    def __init__(self, config: Config):
        self.config = config
        self.processed_ids = self._load_processed_ids()
    
    def _load_processed_ids(self) -> Set[str]:
        file_path = Path(self.config.processed_ids_file)
        if not file_path.exists():
            return set()
        with open(file_path, 'r') as f:
            return set(line.strip() for line in f)
    
    def mark_processed(self, notification_id: str):
        self.processed_ids.add(notification_id)
        with open(self.config.processed_ids_file, 'a') as f:
            f.write(f"{notification_id}\n")
    
    def is_processed(self, notification_id: str) -> bool:
        return str(notification_id) in self.processed_ids

# --- MAIN APPLICATION ---
class MastodonFilter:
    """Main application class"""
    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logging(config.log_file)
        self.tracker = InfractionTracker(config.infractions_file)
        self.analyzer = AIAnalyzer(config, self.logger)
        self.action_handler = ActionHandler(config, self.logger, self.tracker)
        self.processor = NotificationProcessor(config)
        self.mastodon = None
    
    def connect(self):
        """Establish Mastodon connection"""
        load_dotenv()
        try:
            self.mastodon = Mastodon(
                access_token=os.getenv('MASTODON_ACCESS_TOKEN'),
                api_base_url=os.getenv('MASTODON_API_BASE_URL')
            )
            username = self.mastodon.me()['username']
            self.logger.info(f"Connected to Mastodon as @{username}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Mastodon: {e}")
            return False
    
    def process_notification(self, notif: Dict):
        """Process a single notification"""
        status = notif['status']
        author = status['account']
        content = html.unescape(
            status['content']
            .replace('<p>', '')
            .replace('</p>', ' ')
            .replace('<br>', ' ')
            .replace('<br/>', ' ')
        ).strip()
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Processing mention from @{author['acct']} (ID: {notif['id']})")
        self.logger.info(f"Content: \"{content[:200]}{'...' if len(content) > 200 else ''}\"")
        
        # Analyze with AI
        ai_decision = self.analyzer.analyze(content)
        
        # Take appropriate action (pass status ID for warning replies)
        self.action_handler.take_action(self.mastodon, author, ai_decision, status['id'])
        
        # Mark as processed
        self.processor.mark_processed(str(notif['id']))
    
    def run(self):
        """Main run loop"""
        self.logger.info("="*60)
        self.logger.info("Mastodon AI Content Filter v3")
        if self.config.dry_run:
            self.logger.warning("⚠️  DRY RUN MODE - No actions will be performed")
        else:
            self.logger.warning("🔴 LIVE MODE - Actions WILL be performed")
        self.logger.info("="*60)
        
        if not self.connect():
            return
        
        while True:
            try:
                self.logger.info(f"\nChecking for new notifications...")
                notifications = self.mastodon.notifications(mentions_only=True)
                
                new_notifications = [
                    n for n in notifications 
                    if not self.processor.is_processed(str(n['id']))
                ]
                
                if not new_notifications:
                    self.logger.info("No new mentions found")
                else:
                    self.logger.info(f"Found {len(new_notifications)} new mention(s)")
                    for notif in reversed(new_notifications):
                        self.process_notification(notif)
                
            except KeyboardInterrupt:
                self.logger.info("\nShutdown requested by user")
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}", exc_info=True)
            
            self.logger.info(f"Sleeping for {self.config.poll_interval} seconds...")
            time.sleep(self.config.poll_interval)

# --- ENTRY POINT ---
def main():
    config = Config()
    app = MastodonFilter(config)
    app.run()

if __name__ == "__main__":
    main()
