from flask import Flask, render_template, redirect, url_for, request, jsonify
from dotenv import load_dotenv
import requests
import os
from openai import OpenAI
import json, re
import stripe



app = Flask(__name__)
load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")

stripe_keys = {
    "secret_key": os.getenv("STRIPE_SECRET_KEY"),
    "publishable_key": os.getenv("STRIPE_PUBLISHABLE_KEY"),
}

stripe.api_key = stripe_keys["secret_key"]


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate', methods=['GET', 'POST'])
def generate():
    user_prompt = None 
    difficulty = None
    question_count = None
    error = None
    response = None
    if request.method == 'POST':
        user_prompt = request.form.get('prompt')
        difficulty = request.form.get('difficulty')
        question_count = request.form.get('question_count')
        
        system_prompt = '''You are a Worksheet generator. Based on the user's specifications, generate a worksheet with several questions. 
        Ensure that you return your results in the following format:
        
        {
            "worksheet": [
                {
                    "question": "What is the capital of France?",
                    "image": 'image_url';
                    "answer": "Paris"
                },
                {
                    "question": "What is the capital of Spain?",
                    "image": 'image_url';
                    "answer": "Madrid"
                }
            ]
        }
        
        Respond only in JSON format with no extra text.
        '''
        try:
            client = OpenAI()

            # Generate response using OpenAI API
            completion = client.chat.completions.create(
                model="gpt-4o",  
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Generate a worksheet of {question_count} questions with a difficulty of {difficulty} based on the following prompt: {user_prompt}"
                    }
                ]
            )

            # Extract response content
            response_text = completion.choices[0].message.content   
            
            # Parse the JSON response if necessary
        
            response = json.loads(response_text)

             # Generate images for each question using DALL-E
            for item in response.get('worksheet', []):
                question = item['question']
                # Generate an image using DALL-E
                image_response = client.images.generate(
                    model="dall-e-3",
                    prompt="A illustration of this prompt " + question + " and the answer being" + item['answer'] + ". The answer is only meant to  be used for context and should not be included in the image.",
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )

                image_url = image_response.data[0].url

                item["image"] = image_url

   
        except json.JSONDecodeError:
            error = "Failed to parse the response from the API."
        except Exception as e:
            error = f"An unexpected error occurred: {str(e)}"

        


        return render_template('generate.html', response=response.get('worksheet', []), error=error)
    
    return render_template('generate.html', response=[], error=None)



@app.route("/config")
def get_publishable_key():
    stripe_config = {"publicKey": stripe_keys["publishable_key"]}
    return jsonify(stripe_config)

@app.route("/create-checkout-session")
def create_checkout_session():
    domain_url = "http://127.0.0.1:5000/"
    stripe.api_key = stripe_keys["secret_key"]

    try:
        # Create new Checkout Session for the order
        checkout_session = stripe.checkout.Session.create(
            success_url=domain_url + "success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=domain_url + "cancelled",
            payment_method_types=["card"],
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": "Worksheet Generator",
                        },
                        "unit_amount": 1000,  # Amount in cents
                    },
                    "quantity": 1,
                }
            ]
        )
        return jsonify({"sessionId": checkout_session["id"]})
    except Exception as e:
        return jsonify(error=str(e)), 403
    
@app.route("/success")
def success():
    return render_template("success.html")


@app.route("/cancelled")
def cancelled():
    return render_template("cancelled.html")


@app.route("/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, stripe_keys["endpoint_secret"]
        )

    except ValueError as e:
        # Invalid payload
        return "Invalid payload", 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return "Invalid signature", 400

    # Handle the checkout.session.completed event
    if event["type"] == "checkout.session.completed":
        print("Payment was successful.")
        # TODO: run some custom code here

    return "Success", 200


if __name__ == '__main__':
    app.run(debug=True)