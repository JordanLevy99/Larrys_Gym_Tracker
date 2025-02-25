import json
import os
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Paths
ROOT_DIR = Path(__file__).parent.parent
CONFIG_EXAMPLE_PATH = ROOT_DIR / 'config.example.json'
CONFIG_PATH = ROOT_DIR / 'config.json'


def load_config():
    """Load configuration from config.json or create from example if it doesn't exist"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    else:
        # Use example config as template
        with open(CONFIG_EXAMPLE_PATH, 'r') as f:
            config = json.load(f)
        return config


def save_config(config):
    """Save configuration to config.json"""
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)
    return True


@app.route('/')
def index():
    """Main configuration page"""
    config = load_config()
    return render_template('index.html', config=config)


@app.route('/save', methods=['POST'])
def save():
    """Save configuration from form"""
    try:
        # Extract and organize form data into config structure
        config = load_config()  # Start with existing config
        
        # Discord section
        config['discord']['token'] = request.form.get('discord_token', '')
        config['discord']['guild_id'] = request.form.get('discord_guild_id', '')
        config['discord']['channels']['text']['id'] = request.form.get('discord_text_channel_id', '')
        config['discord']['channels']['text']['name'] = request.form.get('discord_text_channel_name', 'larrys-gym-logger')
        config['discord']['channels']['voice']['id'] = request.form.get('discord_voice_channel_id', '')
        config['discord']['channels']['voice']['name'] = request.form.get('discord_voice_channel_name', "Larry's Gym")
        
        # Database section
        config['database']['main_db'] = request.form.get('main_db', 'larrys_database.db')
        config['database']['stock_db'] = request.form.get('stock_db', 'larrys_stock_exchange.db')
        
        # API Keys section
        config['api_keys']['openai'] = request.form.get('api_openai', '')
        config['api_keys']['perplexity'] = request.form.get('api_perplexity', '')
        config['api_keys']['finnhub'] = request.form.get('api_finnhub', '')
        config['api_keys']['news'] = request.form.get('api_news', '')
        config['api_keys']['odds'] = request.form.get('api_odds', '')
        config['api_keys']['dropbox_key'] = request.form.get('api_dropbox_key', '')
        config['api_keys']['dropbox_secret'] = request.form.get('api_dropbox_secret', '')
        config['api_keys']['dropbox_refresh_token'] = request.form.get('api_dropbox_refresh_token', '')
        config['api_keys']['gemini'] = request.form.get('api_gemini', '')
        
        # Process enabled extensions
        enabled_extensions = request.form.getlist('enabled_extensions')
        config['enabled_extensions'] = enabled_extensions
        
        # Users section
        if 'users' not in config:
            config['users'] = {}
            
        # Process user forms
        user_ids = request.form.getlist('user_id')
        user_names = request.form.getlist('user_name')
        user_birthdates = request.form.getlist('user_birthdate')
        
        # Clear existing users and add new ones
        config['users'] = {}
        for i in range(len(user_ids)):
            if user_ids[i] and user_names[i]:
                # Parse date in MM-DD format
                birthdate = user_birthdates[i] if user_birthdates[i] else "01-01"
                config['users'][user_ids[i]] = {
                    "display_name": user_names[i],
                    "birthdate": birthdate
                }
        
        # Birthday songs
        config['birthday_songs'] = {}
        birthday_user_ids = request.form.getlist('birthday_user_id')
        birthday_months = request.form.getlist('birthday_month')
        birthday_days = request.form.getlist('birthday_day')
        birthday_song_links = request.form.getlist('birthday_song_link')
        birthday_song_files = request.form.getlist('birthday_song_file')
        
        for i in range(len(birthday_user_ids)):
            if birthday_user_ids[i] and birthday_months[i] and birthday_days[i]:
                config['birthday_songs'][birthday_user_ids[i]] = {
                    "month": int(birthday_months[i]),
                    "day": int(birthday_days[i]),
                    "song_link": birthday_song_links[i] if birthday_song_links[i] else "",
                    "song_file": birthday_song_files[i] if birthday_song_files[i] else ""
                }
        
        # Winner songs
        config['winner_songs'] = {}
        winner_user_ids = request.form.getlist('winner_user_id')
        winner_song_files = request.form.getlist('winner_song_file')
        winner_durations = request.form.getlist('winner_duration')
        winner_start_seconds = request.form.getlist('winner_start_second')
        
        for i in range(len(winner_user_ids)):
            if winner_user_ids[i] and winner_song_files[i]:
                if winner_user_ids[i] not in config['winner_songs']:
                    config['winner_songs'][winner_user_ids[i]] = []
                
                config['winner_songs'][winner_user_ids[i]].append({
                    "file": winner_song_files[i],
                    "duration": int(winner_durations[i]) if winner_durations[i] else 15,
                    "start_second": int(winner_start_seconds[i]) if winner_start_seconds[i] else 0
                })
        
        # Save the config
        save_config(config)
        flash('Configuration saved successfully!', 'success')
        return redirect(url_for('index'))
    
    except Exception as e:
        flash(f'Error saving configuration: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/generate_discord_guide')
def generate_discord_guide():
    """Generate step-by-step guide for creating a Discord bot"""
    return render_template('discord_guide.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)