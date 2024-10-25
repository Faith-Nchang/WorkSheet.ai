from flask import Flask, render_template, redirect, url_for, request, jsonify
from dotenv import load_dotenv
import requests
import os
from openai import OpenAI
import json, re


app = Flask(__name__)
openai_api_key = os.getenv("OPENAI_API_KEY")


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate', methods=['GET', 'POST'])
def generate():
    user_prompt = None 
    difficulty = None
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
                    "answer": "Paris"
                },
                {
                    "question": "What is the capital of Spain?",
                    "answer": "Madrid"
                }
            ]
        }
        
        Respond only in JSON format with no extra text.
        '''

        client = OpenAI()

        # Generate response using OpenAI API
        completion = client.chat.completions.create(
            model="gpt-4o",  # replace with your model name
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
        try:
            response = json.loads(response_text)
        except json.JSONDecodeError:
            response = {"error": "Failed to parse the response"}
        return render_template('generate.html', response=response.get('worksheet', []))
    return render_template('generate.html', response=[])



if __name__ == '__main__':
    app.run(debug=True)