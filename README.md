## Bear Assistant Line Bot

Bear Assistant (有事找熊熊) is a LINE chatbot designed to assist users with various tasks, including playing games, managing to-do lists, and answering questions. The bot uses Google Cloud services and is implemented with Python.

## Features

1. Number Guessing Game

Users can play a fun "Guess the Number" game by selecting a range of numbers.

The bot keeps track of scores and provides feedback for each guess.

2. 21-Point Blackjack Game

Play a simplified version of the 21-point blackjack game.

The bot acts as the dealer, and users can decide whether to draw more cards or stop.

3. To-Do List Management

Add, view, edit, and delete tasks based on specific dates.

Supports flexible and interactive date-based task management.

4. General Assistance

Provides helpful responses to questions and other interactions.

Project Setup

## Prerequisites

Python 3.9 or later

Google Cloud Platform (GCP) credentials

LINE Developer account with a Messaging API channel

Local Development

## Clone the Repository

git clone https://github.com/annybearlee/linebot.git
cd linebot

## Set Up Virtual Environment

python -m venv .venv
source .venv/bin/activate  # For Linux/Mac
.venv\Scripts\activate   # For Windows

## Install Dependencies

pip install -r requirements.txt

Set Up Environment Variables

Create a .env file to store your environment variables:

LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret
GOOGLE_APPLICATION_CREDENTIALS=path/to/google_key.json

## Run the Application

python main.py

## Deployment

Deploy the app to Google App Engine using the following commands:

gcloud app deploy
gcloud app browse

Google Cloud Configuration

Datastore

The bot uses Google Cloud Datastore for storing user data, such as game states and to-do tasks.

Ensure that the GOOGLE_APPLICATION_CREDENTIALS variable points to a valid service account key JSON file.



## How to Use the Bot

Add the Bot on LINE

Search for the bot name (有事找雪雪) in the LINE app or scan the QR code provided in your LINE Developer Console.

Interact with the Bot

Type 待辦 ("To-Do") to manage tasks.

Play games like 猜數字 ("Guess the Number") or 21點 ("21-Point Blackjack").

Type 疑難雜症 ("Help") to ask questions or get assistance.

File Structure

chatbot.

Built with love by Anny Lee.

