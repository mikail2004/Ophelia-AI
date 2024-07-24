from flask import Flask, render_template, request, redirect, session, jsonify, url_for, request, abort
import os
from zenora import APIClient
import firebase_admin
from firebase_admin import db, credentials
import stripe
import json

from dotenv import load_dotenv
from urllib.parse import quote
project_folder = os.path.expanduser('/home/ophie/mysite/')  #adjust as appropriate

load_dotenv(os.path.join(project_folder, '.env'))
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_KEY = os.getenv("STRIPE_KEY")
ENDPOINT_SECRET = os.getenv("ENDPOINT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
CLIENT_ID = int(os.getenv("CLIENT_ID"))
service_account_json_str = os.getenv('SERVICE_ACCOUNT_JSON') #Loading json (which is stored as a string) from .env
service_account_json = json.loads(service_account_json_str) #Converting json out of the string format
databaseURL = os.getenv('DATABASE_URL')

#Use quote() to format Redirect_URI
OAUTH_URL = f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={quote(REDIRECT_URI)}&response_type=code&scope=identify"

app = Flask(__name__, template_folder='web', static_folder='static')
client = APIClient(BOT_TOKEN, client_secret=CLIENT_SECRET)
cred = credentials.Certificate(service_account_json)
firebase_admin.initialize_app(cred, {"databaseURL":databaseURL})
app.config["SECRET_KEY"] = "mysecret"
ref = db.reference('/') #Creating reference to root node

stripe.api_key = STRIPE_SECRET_KEY

def usernameExists(userID):
    db_ref = db.reference("/")
    query = db_ref.order_by_key().equal_to(userID)
    query_snap = query.get()
    return len(query_snap) > 0

def updateUserTokens(userID, itemName):
    balance = db.reference(f"/{userID}/Balance").get()
    itemName = itemName.replace(",", "") # remove comma
    itemName = itemName.replace("Tokens", "") # remove word
    balance += int(itemName)
    db.reference(f"/{userID}").update({"Balance": balance})
    db.reference(f"/{userID}").update({"Type": 'Paid User' })
    print(balance)

@app.route("/", methods=["GET", "POST"])
def home():

    access_token = session.get("access_token")

    if not access_token:
        return render_template("index.html", oauth_url=OAUTH_URL)

    bearer_client = APIClient(access_token, bearer=True)
    current_user = bearer_client.users.get_current_user()

    global userID
    userID = current_user.id

    if usernameExists(str(current_user.id)) == False:
        balanceRemaining = 0
        dashboardPath = render_template('access.html')
    else:
        userTokens = db.reference(f"/{current_user.id}/TotalUserTokens").get()
        balance = db.reference(f"/{current_user.id}/Balance").get()
        balanceRemaining = balance - userTokens

        #Sessions 1-4

        dashboardPath = render_template('index.html',
                           sendID=current_user.id,
                           user=current_user.username,
                           avatar=current_user.avatar_url,
                           sendBalance=balanceRemaining,
                           #checkout_session_id1=session1['id'],
                           #checkout_session_id2=session2['id'],
                           #checkout_session_id3=session3['id'],
                           #checkout_session_id4=session4['id'],
                           #checkout_public_key=STRIPE_KEY
        )

    return dashboardPath

@app.route('/stripe_pay')
def stripe_pay():
    stripe.PromotionCode.create(coupon="t70LVZvO",) #Promotion code creation (linked to coupon from dashboard) || Don't mention code here, this is only for generation.

    #Session for 0.99.
    session1 = stripe.checkout.Session.create(
    payment_method_types=['card'],
    #Append final items to the cart
    line_items=[{
        'price': 'price_1NcUNDGHacRXI40reXawqau4',
        'quantity': 1,
    }],
    mode='payment',
    allow_promotion_codes=True, #allowing promotion codes for checkout web hook || Discount must never decrease price to $0.5 or below.
    customer_creation="always",
    success_url=url_for('thanks', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
    cancel_url=url_for('home', _external=True)
    )

    #Session for 1.99 tokens.
    session2 = stripe.checkout.Session.create(
    payment_method_types=['card'],
    #Append final items to the cart
    line_items=[{
        'price': 'price_1NcV2mGHacRXI40ra7Yt0SZq',
        'quantity': 1,
    }],
    mode='payment',
    allow_promotion_codes=True,
    customer_creation="always",
    success_url=url_for('thanks', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
    cancel_url=url_for('home', _external=True)
    )

    #Session for 4.99.
    session3 = stripe.checkout.Session.create(
    payment_method_types=['card'],
    #Append final items to the cart
    line_items=[{
        'price': 'price_1NdJciGHacRXI40r52NEHsGz',
        'quantity': 1,
    }],
    mode='payment',
    allow_promotion_codes=True,
    customer_creation="always",
    success_url=url_for('thanks', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
    cancel_url=url_for('home', _external=True)
    )

    #Session for 9.99.
    session4 = stripe.checkout.Session.create(
    payment_method_types=['card'],
    #Append final items to the cart
    line_items=[{
        'price': 'price_1NdJeDGHacRXI40rMjzRjzfL',
        'quantity': 1,
    }],
    mode='payment',
    allow_promotion_codes=True,
    customer_creation="always",
    success_url=url_for('thanks', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
    cancel_url=url_for('home', _external=True)
    )

    return {'checkout_session_id1': session1['id'],
        'checkout_session_id2': session2['id'],
        'checkout_session_id3': session3['id'],
        'checkout_session_id4': session4['id'],
        'checkout_public_key': STRIPE_KEY}

@app.route('/access')
def access():
    return render_template('access.html')

@app.route("/logout")
def logout():
    session.pop("access_token")
    return redirect("/")

@app.route("/oauth/callback")
def oauth_callback(): #To receive access token from Discord API
    try:
        code = request.args["code"]
        access_token = client.oauth.get_access_token(code, redirect_uri=REDIRECT_URI).access_token
        session["access_token"] = access_token
        return redirect("/")
    except:
        return render_template("index.html", oauth_url=OAUTH_URL)

@app.route('/thanks')
def thanks():
    return render_template('thanks.html')

@app.route('/stripe_webhook', methods=['POST'])
def stripe_webhook():
    print('WEBHOOK CALLED')

    if request.content_length > 1024 * 1024:
        print('REQUEST TOO BIG')
        abort(400)
    payload = request.get_data()
    sig_header = request.environ.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = ENDPOINT_SECRET
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        print('INVALID PAYLOAD')
        return {}, 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print('INVALID SIGNATURE')
        return {}, 400

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        line_items = stripe.checkout.Session.list_line_items(session['id'], limit=1)
        itemName = line_items['data'][0]['description']
        updateUserTokens(userID, itemName)

    return {}

if __name__ == '__main__':
    #port = int(os.environ.get("PORT", 5000))
    #app.run(debug=True, host='0.0.0.0', port=port)
    app.run()
