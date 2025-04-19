import os
from flask import Flask, redirect, request
from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth
import requests

# ===== CONFIG =====
FITBIT_CLIENT_ID = '23QC9S'
FITBIT_CLIENT_SECRET = '95dd38ddbd20edfe6b19956a61afee9f'
REDIRECT_URI = 'http://localhost:8000/fitbit/callback'
SCOPE = ['heartrate', 'profile']

# ===== FLASK APP =====
app = Flask(__name__)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # for localhost testing only

# ===== Step 1: Start Fitbit Login =====
@app.route('/fitbit/login')
def fitbit_login():
    oauth = OAuth2Session(FITBIT_CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPE)
    authorization_url, state = oauth.authorization_url('https://www.fitbit.com/oauth2/authorize')
    return redirect(authorization_url)

# ===== Step 2: Handle Callback and Get Token =====
@app.route('/fitbit/callback')
def fitbit_callback():
    oauth = OAuth2Session(FITBIT_CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPE)
    code = request.args.get('code')

    token = oauth.fetch_token(
        token_url='https://api.fitbit.com/oauth2/token',
        code=code,
        auth=HTTPBasicAuth(FITBIT_CLIENT_ID, FITBIT_CLIENT_SECRET)
    )

    access_token = token['access_token']
    print("✅ Access Token Retrieved!")

    # Fetch heart rate
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    hr_response = requests.get(
        'https://api.fitbit.com/1/user/-/activities/heart/date/today/1d.json',
        headers=headers
    )

    hr_data = hr_response.json()
    print("❤️ Heart Rate Data:")
    print(hr_data)

    return "✅ Fitbit Integration Complete! Check your terminal for heart rate data."

# ===== Run App =====
if __name__ == '__main__':
    app.run(port=8000, debug=True)
