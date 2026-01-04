# Mastodon AI Content Filter

A Python script that uses AI to automatically filter mentions on Mastodon and block accounts that post negative or toxic content. It is designed to be a personal moderation tool to help curate a more positive social media experience.

> ⚠️ **USE AT YOUR OWN RISK** ⚠️
>
> This script automates the blocking of other accounts. An AI model can and will make mistakes (false positives), potentially blocking an account you did not want to block.
>
> It is **highly recommended** to run this script in its default **`DRY_RUN = True`** mode for several days. Observe its behavior and review the accounts it *would have blocked* in the terminal logs. Only when you are confident in its accuracy should you switch to live mode.

## Features

*   **Automatic Monitoring:** Continuously checks for new mentions directed at your account.
*   **AI-Powered Analysis:** Uses a language model to analyze the sentiment and toxicity of incoming posts.
*   **Pluggable AI Backends:** Easily switch between using a private, local [Ollama](https://ollama.com/) instance or a cloud service like [OpenAI](https://openai.com/).
*   **Automated Blocking:** Blocks the author of any post identified as negative.
*   **Safe Dry Run Mode:** A crucial safety feature that reports what actions it *would* take without actually performing them.
*   **Stateful Processing:** Keeps track of processed notifications to avoid re-analyzing the same post.

## How It Works

The script operates in a simple, continuous loop:

1.  **Connect:** Authenticates with the Mastodon API using your credentials.
2.  **Fetch:** Retrieves your latest notifications, specifically looking for mentions.
3.  **Analyze:** For each new mention, the content of the post is sent to your chosen AI backend (e.g., a local Ollama model).
4.  **Classify:** The AI is prompted to classify the content as `POSITIVE`, `NEUTRAL`, or `NEGATIVE`.
5.  **Act:** If the classification is `NEGATIVE`, the script will block the author's account (unless in Dry Run mode).
6.  **Log:** The notification ID is saved to a local file so it won't be processed again.
7.  **Wait:** The script sleeps for a configurable amount of time (default: 5 minutes) before repeating the process.

## Prerequisites

1.  **Python 3.7+**
2.  **A Mastodon Account**
3.  **Mastodon Application Credentials:**
    *   Go to your Mastodon instance's **Preferences -> Development -> New Application**.
    *   Give it a name (e.g., "AI Content Filter").
    *   Under **Scopes**, you **must** check `read:notifications` and `write:blocks`.
    *   Save the application and copy the `Client key`, `Client secret`, and `Your access token`.
4.  **An AI Backend:**
    *   **(Recommended) Ollama:** A free, private, and powerful way to run models locally. [Download Ollama here](https://ollama.com/). After installing, pull a model from your terminal:
        ```bash
        ollama pull llama3:8b
        ```
    *   **(Alternative) OpenAI API Key:** A powerful, paid option. You will need an API key from the [OpenAI Platform](https://platform.openai.com/api-keys).

## Installation

1.  **Clone the repository or download the script:**
    ```bash
    git clone https://github.com/your-username/mastodon-ai-filter.git
    cd mastodon-ai-filter
    ```

2.  **Install the required Python packages:**
    ```bash
    # It's recommended to use a virtual environment
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`

    # Install core libraries and the AI client of your choice
    pip install Mastodon.py python-dotenv ollama openai
    ```

## Mastodon Application Setup

Before the script can interact with your Mastodon account, you must register it as an "application" on your instance. This process generates the secure API keys that grant the script permission to read your notifications and block accounts on your behalf.

1.  Log in to your Mastodon account on the web.
2.  Navigate to **Preferences** > **Development**.
3.  Click the **New Application** button.
4.  Fill out the form:
    *   **Application name:** Give it a descriptive name you'll recognize, such as `AI Content Filter`.
    *   **Application website:** This can be left blank.
    *   **Redirect URIs:** Leave this as the default `urn:ietf:wg:oauth:2.0:oob`.
5.  Under the **Scopes** section, you must grant the specific permissions the script needs. Uncheck any default selections and ensure **only** the following are checked:
    *   `read:notifications`: Allows the script to see your mentions.
    *   `write:blocks`: Allows the script to block accounts.
    > **Security Tip:** It's best practice to only grant the minimum permissions required (Principle of Least Privilege). Avoid enabling powerful scopes like `write:statuses` or `admin:write` for this script.
6.  Click **Save application**.
7.  On the next page, you will see the application's details. You need to **copy three values**:
    *   `Client key`
    *   `Client secret`
    *   `Your access token`
8.  Paste these three values into the corresponding fields in your `.env` file. The script is now authorized to connect to your account.

## Configuration

1.  **Create a `.env` file** in the same directory as the script. This file will store your secret keys and settings. **Do not share this file.**

2.  **Copy and paste the template below** into your `.env` file and fill it with your credentials.

    ```.env
    # Mastodon Configuration
    MASTODON_API_BASE_URL="https://your-instance.social"
    MASTODON_CLIENT_KEY="paste_your_client_key_here"
    MASTODON_CLIENT_SECRET="paste_your_client_secret_here"
    MASTODON_ACCESS_TOKEN="paste_your_access_token_here"

    # --- CHOOSE AND CONFIGURE ONE AI BACKEND ---

    # Option 1: Ollama (Recommended)
    OLLAMA_HOST="http://localhost:11434"
    OLLAMA_MODEL="llama3:8b" # Or "mistral", "phi3", etc.

    # Option 2: OpenAI (Uncomment and fill if using)
    # OPENAI_API_KEY="paste_your_openai_api_key_here"
    ```

## Running the Script

1.  **If using Ollama, ensure the Ollama application is running.**
2.  Open your terminal in the project directory.
3.  Run the script:
    ```bash
    python mastodon_filter_ollama.py
    ```

The script will start, connect to your accounts, and begin its filtering loop. It will print its actions to the terminal. Leave the terminal window running for the script to continue working.

### 🚨 Fine-Tuning with Dry Run Mode

By default, `DRY_RUN` is set to `True` inside the script.

```python
# --- CONFIGURATION ---
DRY_RUN = True  # SET TO FALSE TO ACTUALLY BLOCK ACCOUNTS
```

*   **In this mode**, the script will print messages like `DRY RUN: Would have blocked account @user@instance.social.`
*   **Let it run like this for a few days.** Monitor the output. Are the AI's decisions correct? Is it flagging sarcasm as negative?
*   **Once you are satisfied** with its performance, edit the script file, change the setting to `DRY_RUN = False`, save the file, and restart the script. It will now perform live blocking.

## Customization

The most effective way to improve the script's performance is by refining the AI's instructions. This is known as "prompt engineering".

Open the script file and find the `analyze_with_ollama` (or `analyze_with_openai`) function. Inside, you will find a `system_prompt` variable.

**Example `system_prompt`:**
```python
system_prompt = """
You are a content moderation AI. Analyze the social media post.
Classify it strictly as one of the following: 'POSITIVE', 'NEUTRAL', or 'NEGATIVE'.
A 'NEGATIVE' classification is for posts that are insulting, harassing, toxic, aggressive, spam, or hateful.
Your entire response must be ONLY ONE WORD: POSITIVE, NEUTRAL, or NEGATIVE.
"""
```

You can make this prompt more specific to your needs. For example:
*   To be less aggressive: `"Only classify a post as NEGATIVE if it contains direct insults or slurs."`
*   To also catch spam: `"A 'NEGATIVE' classification is for posts that are insulting, harassing, OR unsolicited promotions."`
*   To better handle nuance: `"Consider sarcasm to be NEUTRAL unless it is clearly hostile."`

Experiment with the prompt to tune the AI's behavior to your personal preference.

## Disclaimer

This project is provided as-is. The user assumes all responsibility for the actions performed by this script, including any accounts that are blocked, any API costs incurred (if using paid services), and for complying with the terms of service of both Mastodon and any AI service provider.
