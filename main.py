from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import LineBotApiError
from linebot.exceptions import InvalidSignatureError
import requests
from linebot.models import MessageEvent, TextMessage, TextSendMessage, TemplateSendMessage, ButtonsTemplate, MessageTemplateAction, FlexSendMessage, PostbackEvent
from datetime import datetime as dt
import random
import json
from datetime import timedelta
import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_key.json"


# Check if the variable exists
key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# local
# GOOGLE_APPLICATION_CREDENTIALS = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

# Imports the Google Cloud client library
from google.cloud import datastore

# Instantiates a client
datastore_client = datastore.Client()

app = Flask(__name__)


# LINE BOT
line_bot_key = os.environ['line_bot_api']
line_bot_api = LineBotApi(line_bot_key)
channel_secret = os.environ.get("CHANNEL_SECRET")
handler = WebhookHandler(channel_secret)  # Initialize with CHANNEL_SECRET


@app.route('/', methods=['GET','POST'])
def home():
    return "Hello"


@app.route("/callback", methods=['GET','POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


def get_user_id(event):
    try:
        _id = event.source.user_id
        return _id
    except LineBotApiError as e:
        # error handle
        return "Cannot get User ID"

def reset_user_data(user_id):
    try:
        key = datastore_client.key('Task4', user_id)
        datastore_client.delete(key)
        print(f"Data reset for user: {user_id}")
    except Exception as e:
        print(f"Error resetting data for user {user_id}: {e}")


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    message = event.message.text.lower()
    user_id = event.source.user_id

    if message == "reset":
        reset_user_data(user_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage("Your data has been reset. You can start fresh!"))
        return

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    message = event.message.text.lower()
    print(f"Received message: {message} from user: {event.source.user_id}")


def get_quote():
    response = requests.get("https://api.kanye.rest")
    data = response.json()
    quote = data['quote']
    return quote


# Number guessing game logic
def check_number(num, task):
    if num == 'q':
        task['game-mode'] = 0
        datastore_client.put(task)
        return f"Game ended, the secret number was {task['secret-number']}"

    try:
        number = int(num)
    except:
        return "Please enter a number or 'q' to quit."

    if task['score'] == 0:
        task['game-mode'] = 0
        datastore_client.put(task)
        return f"Game ended, the secret number was {task['secret-number']}"

    if number == task["secret-number"]:
        task['game-mode'] = 0
        datastore_client.put(task)
        return f"Correct! Final score: {task['score']}/20"

    elif number < task["secret-number"]:
        task['score'] -= 1
        datastore_client.put(task)
        return f"Too low. Try again. Current score: {task['score']}/20"

    else:
        task['score'] -= 1
        datastore_client.put(task)
        return f"Too high. Try again. Current score: {task['score']}/20"



cards = [11, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10]
def deal_card():
    card = random.choice(cards)
    return card


def calculate_score(cards):
    for i in range(len(cards)):
        cards[i] = int (cards[i])
    if sum(cards)==21 and len(cards)==2:
        return 0

    if 11 in cards and sum(cards)>21:
        cards.remove(11)
        cards.append(1)

    return sum(cards)


def compare(user_score, computer_score):
    if user_score == computer_score:
        return "It's a draw!"

    elif computer_score == 0:
        return "Computer got Blackjack! You lose."

    elif user_score == 0:
        return "Blackjack! You win!"

    elif user_score > 21:
        return "You went over 21. Try again!"

    elif computer_score > 21:
        return "Computer went over 21. You win!"

    elif user_score > computer_score:
        return "Congratulations, you win!"

    else:
        return "You lost. Try again!"


# Format the to-do list into a numbered format
def display_to_do(send, task):
    i = 1
    for t in task:
        send += f"{i}. "
        send += t
        send += "\n"
        i += 1
    return send.strip()


# Generate buttons for Flex messages
symbol_list = ["+", "#", "$"]


def generate_button(j, label):
    global symbol_list
    for i in range(0, 3):
        j['footer']['contents'][i]['action']['text'] = f"{symbol_list[i]}{label}"


# Check if the user wants to quit a mode
def check_if_quit_mode(message, event, task, mode):
    if message == 'q':
        if mode == 'game-21':
            task[mode]['mode'] = 0
        else:
            task[mode] = 0
        datastore_client.put(task)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(f"Exiting {mode} mode"))


# Respond when no to-do items are found for a specific date
def no_todo_found_reply(event, date):
    j = json.load(open('no_todo_found.json', 'r', encoding='utf-8'))
    j['body']['contents'][0]['contents'][0]['contents'][0]['text'] = f"No to-do items found for {date}"
    j['footer']['contents'][0]['action']['text'] = f"+{date}"
    flex_message = FlexSendMessage(
        alt_text='no-todo-found',
        contents=j
    )
    line_bot_api.reply_message(event.reply_token, flex_message)


# Display today's to-do list
def display_today(event, j, task, today):
    send = f"You have {len(task['to-do'][today])} tasks for today. Keep it up!\n\n"
    j['body']['contents'][0]['text'] = "Today's To-Do"
    j['body']['contents'][2]['contents'][0]['contents'][0]['text'] = display_to_do(send, task['to-do'][today])
    generate_button(j, today)
    flex_message = FlexSendMessage(
        alt_text='to-do-list',
        contents=j
    )
    line_bot_api.reply_message(event.reply_token, flex_message)


# Display to-do list for other dates
def display_other_day(event, j, task, send, date_type):
    if "!" in date_type:
        date_type = date_type.replace("!", "")
        j['body']['contents'][2]['contents'][0]['contents'][0]['text'] = display_to_do(send, task['to-do'][date_type])
        generate_button(j, date_type)
    else:
        j['body']['contents'][2]['contents'][0]['contents'][0]['text'] = display_to_do(send, task['to-do'][task[date_type]])
        generate_button(j, task[date_type])
    flex_message = FlexSendMessage(
        alt_text="to-do",
        contents=j
    )
    line_bot_api.reply_message(event.reply_token, flex_message)


# Initialize the database with default values
def initialize_db(key):
    task = datastore.Entity(key=key)
    task['game-21'] = {'mode': 0, "user_cards": [], "computer_cards": [], 'user_score': 0, 'computer_score': 0, 'round': 0}
    task['weather-mode'] = 0
    task['view-mode'] = 0
    task['edit-mode'] = 0
    task['delete-mode'] = 0
    task['add-mode'] = 0
    task['game-mode'] = 0
    task['to-do'] = {}
    task['score'] = 20
    task['secret-number'] = 0
    task['date-to-add'] = 0
    datastore_client.put(task)
    return task


# Postback event handler
@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = get_user_id(event)
    key = datastore_client.key('Task4', user_id)
    try:
        task = datastore_client.get(key=key)
    except:
        task = initialize_db(key)

    if task['view-mode'] == 2:
        date = event.postback.params['date']
        send = f"Your to-do items for {date}:\n\n"
        j = json.load(open('brown2.json', 'r', encoding='utf-8'))
        try:
            to_do = task['to-do'][date]
            if len(to_do) == 0:
                task['view-mode'] = 0
                datastore_client.put(task)
                no_todo_found_reply(event, date)
            else:
                today = str(dt.now().date())
                if date == today:
                    task['view-mode'] = 0
                    datastore_client.put(task)
                    display_today(event, j, task, today)
                else:
                    date += "!"
                    task['view-mode'] = 0
                    datastore_client.put(task)
                    display_other_day(event, j, task, send, date)
        except:
            task['view-mode'] = 0
            datastore_client.put(task)
            no_todo_found_reply(event, date)

    elif task['add-mode'] == 2:
        date = event.postback.params['date']
        send = f"You selected {date}. Please enter the task to add for that date:"
        task['add-mode'] = 3
        task['date-to-add'] = date
        datastore_client.put(task)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(send))


# Message event handler
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    message = event.message.text
    user_id = get_user_id(event)
    key = datastore_client.key('Task4', user_id)

    try:
        task = datastore_client.get(key=key)
    except:
        task = initialize_db(key)


# Version II----------------------------------------------------------------------------

@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = get_user_id(event)
    key = datastore_client.key('Task4', user_id)

    # Check if the database entry exists for the user
    try:
        task = datastore_client.get(key=key)
        r = task['add-mode']
    except:
        # If not found, initialize a new database entry
        task = initialize_db(key)

    # View mode: Viewing to-do list for a specific date
    if task['view-mode'] == 2:
        date = event.postback.params['date']
        send = f"Your to-do items for {date}:\n\n"
        j = json.load(open('brown2.json', 'r', encoding='utf-8'))

        try:
            # Check if tasks exist for the selected date
            to_do = task['to-do'][date]
            if len(to_do) == 0:  # If the list exists but is empty
                task['view-mode'] = 0
                datastore_client.put(task)
                no_todo_found_reply(event, date)
            else:
                today = str(dt.now().date())
                task['view-mode'] = 0
                datastore_client.put(task)
                if date == today:  # If the date is today
                    display_today(event, j, task, today)
                else:
                    date += "!"
                    display_other_day(event, j, task, send, date)
        except:
            # If no tasks exist for the selected date
            task['view-mode'] = 0
            datastore_client.put(task)
            no_todo_found_reply(event, date)

    # Add mode: Adding a new to-do item for a specific date
    elif task['add-mode'] == 2:
        date = event.postback.params['date']
        send = f"You selected {date}. Please enter the task to add for that date:"
        task['add-mode'] = 3
        task['date-to-add'] = date
        datastore_client.put(task)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(send))


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    message = event.message.text
    user_id = get_user_id(event)
    key = datastore_client.key('Task4', user_id)

    # Check if the database entry exists for the user
    try:
        task = datastore_client.get(key=key)
        r = task['add-mode']
    except:
        # If not found, initialize a new database entry
        task = initialize_db(key)

    # Add mode: Initializing task addition
    if task['add-mode'] == 2:
        check_if_quit_mode(message, event, task, 'add-mode')
        j = json.load(open('pick_date_to_add.json', 'r', encoding='utf-8'))
        j['body']['contents'][0]['text'] = "Please use the date picker to select a date, or type 'q' to exit add mode."
        flex_message = FlexSendMessage(
            alt_text='Pick a date',
            contents=j
        )
        line_bot_api.reply_message(event.reply_token, flex_message)

    # Adding a task for a selected date
    elif task['add-mode'] == 3:
        today = str(dt.now().date())
        # Check if the task list for the date exists
        try:
            task['to-do'][task['date-to-add']].append(message)
        except:
            task['to-do'][task['date-to-add']] = [message]

        task['add-mode'] = 0
        datastore_client.put(task)
        j = json.load(open('brown2.json', 'r', encoding='utf-8'))

        if task['date-to-add'] == today:
            display_today(event, j, task, today)
        send = f"Task added successfully. Your to-do items for {task['date-to-add']} are:\n\n"
        display_other_day(event, j, task, send, "date-to-add")

    # View mode: Displaying tasks for a specific date
    elif "@" in message:
        message = message.replace("@", "")
        if message == "Other dates":
            task['view-mode'] = 2
            datastore_client.put(task)
            j = json.load(open('pick_a_date.json', 'r', encoding='utf-8'))
            flex_message = FlexSendMessage(
                alt_text='Pick a date',
                contents=j
            )
            line_bot_api.reply_message(event.reply_token, flex_message)
        else:
            j = json.load(open('brown2.json', 'r', encoding='utf-8'))
            send = f"Your to-do items for {message} are:\n\n"
            try:
                to_do = task['to-do'][message]
                if len(to_do) == 0:  # If the list exists but is empty
                    task['view-mode'] = 0
                    datastore_client.put(task)
                    no_todo_found_reply(event, message)
                else:
                    today = str(dt.now().date())
                    task['view-mode'] = 0
                    datastore_client.put(task)
                    if message == today:
                        display_today(event, j, task, today)
                    else:
                        message += "!"
                        display_other_day(event, j, task, send, message)
            except:
                # If no tasks exist for the selected date
                task['view-mode'] = 0
                datastore_client.put(task)
                no_todo_found_reply(event, message)


    # ---------------------------- Edit Mode -----------------------------------------------------#
    # Edit To-Do Mode: Receiving the index of the task to edit
    elif task['edit-mode'] == 1:
        check_if_quit_mode(message, event, task, "edit-mode")
        success = 1

        # Step 1: Check if the user input is a valid number
        try:
            index = int(message) - 1  # Adjusting for 0-based index
        except:
            success = 0
            line_bot_api.reply_message(event.reply_token,
                                       TextSendMessage("Please enter a valid number, or type 'q' to exit edit mode."))

        # Step 2: Check if the number is greater than zero
        if success == 1:
            if int(message) > 0:
                success = 2
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(
                    "Please enter a number greater than zero, or type 'q' to exit edit mode."))

        # Step 3: Check if the number is within the range of the to-do list
        if success == 2:
            try:
                to_do = task['to-do'][task['date-to-edit']][index]
                task['edit-index'] = index
                task['edit-mode'] = 2
                datastore_client.put(task)
                line_bot_api.reply_message(event.reply_token,
                                           TextSendMessage("Please enter the text to edit the task:"))
            except:  # Index out of range
                line_bot_api.reply_message(event.reply_token, TextSendMessage(
                    "Please enter a number within the valid range, or type 'q' to exit edit mode."))

    # Receiving the text to update the selected task
    elif task['edit-mode'] == 2:
        check_if_quit_mode(message, event, task, "edit-mode")
        task['to-do'][task['date-to-edit']][task['edit-index']] = message
        task['edit-mode'] = 0
        datastore_client.put(task)
        today = str(dt.now().date())
        j = json.load(open('brown2.json', 'r', encoding='utf-8'))

        # If the edited task is for today, display today's to-do list
        if task['date-to-edit'] == today:
            display_today(event, j, task, today)
        send = f"Task successfully edited. Your to-do items for {task['date-to-edit']} are:\n\n"
        display_other_day(event, j, task, send, "date-to-edit")


    # ----------------------------------- Delete Mode --------------------------------------------------#

    # Delete To-Do Mode: Receiving the index of the task to delete

    elif task['delete-mode'] == 1:

        check_if_quit_mode(message, event, task, "delete-mode")

        index = 0

        success = 1

        # Step 1: Check if the user input is a valid number

        try:

            index = int(message) - 1  # Adjusting for 0-based index

        except:

            success = 0

            line_bot_api.reply_message(event.reply_token,
                                       TextSendMessage("Please enter a valid number, or type 'q' to exit delete mode."))

        # Step 2: Check if the number is greater than zero

        if success == 1:

            if int(message) > 0:

                success = 2

            else:

                line_bot_api.reply_message(event.reply_token, TextSendMessage(
                    "Please enter a number greater than zero, or type 'q' to exit delete mode."))

        # Step 3: Check if the number is within the range of the to-do list

        if success == 2:

            try:

                # Remove the task from the to-do list

                task['to-do'][task['date-to-delete']].pop(index)

                task['delete-mode'] = 0

                datastore_client.put(task)

                # If no tasks remain for the date

                if len(task['to-do'][task['date-to-delete']]) == 0:

                    line_bot_api.reply_message(event.reply_token, TextSendMessage(
                        f"Task successfully deleted. No tasks remain for {task['date-to-delete']}."))

                else:

                    today = str(dt.now().date())

                    j = json.load(open('brown2.json', 'r', encoding='utf-8'))

                    # If the date is today, display today's to-do list

                    if task['date-to-delete'] == today:

                        display_today(event, j, task, today)

                    else:  # Display tasks for other dates

                        send = f"Task successfully deleted. Your to-do items for {task['date-to-delete']} are:\n\n"

                        display_other_day(event, j, task, send, "date-to-delete")

            except:  # Index out of range

                line_bot_api.reply_message(event.reply_token, TextSendMessage(
                    "Please enter a number within the valid range, or type 'q' to exit delete mode."))



    # ----------------------------------- number guessing --------------------------------------------------#
    elif task['game-mode'] == 1:
        check_if_quit_mode(message, event, task, 'game-mode')
        # Generate a random number based on the range provided by the user
        try:
            message = message.split("~")
            task['secret-number'] = random.randint(int(message[0]), int(message[1]))
            task['game-mode'] = 2
            datastore_client.put(task)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                f"Let's play 'Guess the Number'! Pick a number between {message[0]} and {message[1]}."))
        # If the input is invalid, prompt the user to select the range again or exit
        except:
            j = json.load(open('guess_menu_2.json', 'r', encoding='utf-8'))
            flex_message = FlexSendMessage(
                alt_text='guess_number_menu',
                contents=j
            )
            line_bot_api.reply_message(event.reply_token, flex_message)



    elif task['game-mode'] == 2:
        reply = check_number(message, task)
        # If the guess is correct or the game ends (e.g., by quitting), display the result
        if "correct" in reply or "end" in reply:
            j = json.load(open('game_2.json', 'r', encoding='utf-8'))
            # Show "Challenge Failed" if the game ended or the user ran out of attempts
            if "end" in reply:
                j['body']['contents'][0]['text'] = "Challenge Failed"
                j['body']['contents'][1]['contents'][0]['contents'][1]['text'] = str(task['secret-number'])
                j['body']['contents'][1]['contents'][1]['contents'][1]['text'] = f"{task['score']}/20"

                flex_message = FlexSendMessage(
                    alt_text='congrats',
                    contents=j
                )
                line_bot_api.reply_message(event.reply_token, flex_message)

            # Otherwise, prompt the user to guess again
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(reply))

    # ----------------------------------- 21 --------------------------------------------------#
    elif task['game-21']['mode'] == 1:
        message = message.strip().lower()
        check_if_quit_mode(message, event, task, 'game-21')  # Check if the user wants to quit

        user_wanna_end = False  # Flag to indicate if the user wants to end
        task['game-21']['round'] += 1  # Increment the round count
        datastore_client.put(task)

        # First round: Both user and computer are dealt two cards
        if task['game-21']['round'] == 1:
            for _ in range(2):
                task['game-21']['user_cards'].append(deal_card())  # User's cards
                task['game-21']['computer_cards'].append(deal_card())  # Computer's cards
                datastore_client.put(task)

        # Subsequent rounds: User chooses to draw another card
        if task['game-21']['round'] >= 2 and message == 'y':
            task['game-21']['user_cards'].append(deal_card())
            datastore_client.put(task)

        # User decides not to draw more cards
        elif task['game-21']['round'] >= 2 and message == 'n':
            user_wanna_end = True
            task['game-21']['mode'] = 0
            datastore_client.put(task)

        # Calculate scores for both user and computer
        task['game-21']['user_score'] = calculate_score(task['game-21']['user_cards'])
        task['game-21']['computer_score'] = calculate_score(task['game-21']['computer_cards'])
        datastore_client.put(task)

        send = ""  # Message to be sent to the user

        # Display user's cards and computer's first card
        if not user_wanna_end:
            send = f"♣ Your cards: {task['game-21']['user_cards']}, Current Score: {task['game-21']['user_score']}\n"
            send += f"♣ Computer's first card: {task['game-21']['computer_cards'][0]}\n\n"

        # End the game if any termination condition is met
        if task['game-21']['user_score'] == 0 or task['game-21']['computer_score'] == 0 or task['game-21'][
            'user_score'] > 21 or user_wanna_end:
            task['game-21']['mode'] = 0
            datastore_client.put(task)
        else:
            # Prompt the user to continue drawing cards
            send += "Do you want to draw another card? Reply 'y' for yes, 'n' for no."
            line_bot_api.reply_message(event.reply_token, TextSendMessage(send))


        # Final scoring
        if task['game-21']['mode'] == 0 or user_wanna_end:
            # Computer draws until its score is 17 or higher
            while task['game-21']['computer_score'] != 0 and task['game-21']['computer_score'] < 17:
                task['game-21']['computer_cards'].append(deal_card())
                task['game-21']['computer_score'] = calculate_score(task['game-21']['computer_cards'])
                datastore_client.put(task)

            # Compare results and prepare final Flex Message
            j = json.load(open('game-21.json', 'r', encoding='utf-8'))
            j['body']['contents'][0]['text'] = compare(task['game-21']['user_score'], task['game-21']['computer_score'])
            j['body']['contents'][1]['contents'][0]['contents'][1]['text'] = str(task['game-21']['user_cards'])
            j['body']['contents'][1]['contents'][1]['contents'][1]['text'] = str(task['game-21']['user_score'])
            j['body']['contents'][1]['contents'][2]['contents'][1]['text'] = str(task['game-21']['computer_cards'])
            j['body']['contents'][1]['contents'][3]['contents'][1]['text'] = str(task['game-21']['computer_score'])

            flex_message = FlexSendMessage(
                alt_text='Final Result',
                contents=j
            )
            line_bot_api.reply_message(event.reply_token, flex_message)

    # ----------------------------------- others --------------------------------------------------#

    elif "encourage" in message:
        j = json.load(open('quoting.json','r',encoding='utf-8'))
        j['body']['contents'][0]['contents'][0]['contents'][0]['text'] = get_quote()
        flex_message = FlexSendMessage(
            alt_text='quotes',
            contents=j
        )
        line_bot_api.reply_message(event.reply_token, flex_message)
    elif "game" in message:
        j = json.load(open('game_menu.json','r',encoding='utf-8'))
        flex_message = FlexSendMessage(
            alt_text='game_menu',
            contents=j
        )
        line_bot_api.reply_message(event.reply_token, flex_message)

    elif "number guessing" in message:
        # 將遊戲數值初始化
        task['game-mode'] = 1
        task['score'] = 20
        datastore_client.put(task)
        j = json.load(open('guess_number_menu.json','r', encoding='utf-8'))
        flex_message = FlexSendMessage(
            alt_text='guess_number_menu',
            contents=j
        )
        line_bot_api.reply_message(event.reply_token, flex_message)

    elif "blackjack" in message:
        task['game-21']['mode'] = 1
        task['game-21']['user_cards']=[]
        task['game-21']['computer_cards']=[]
        task['game-21']['user_score']=0
        task['game-21']['computer_score']=0
        task['game-21']['round']=0
        datastore_client.put(task)
        line_bot_api.reply_message(event.reply_token, TextSendMessage("Welcome to blackjack game, enter y to draw a card, q to quit"))

    elif message == "to-do":
        j = json.load(open('todo_start.json', 'r', encoding='utf-8'))
        flex_message = FlexSendMessage(
            alt_text='to-do',
            contents=j
        )
        line_bot_api.reply_message(event.reply_token, flex_message)

    elif "add to-do" in message:
        task["add-mode"] = 2
        datastore_client.put(task)
        j = json.load(open('pick_date_to_add.json','r',encoding='utf-8'))
        flex_message = FlexSendMessage(
            alt_text='pick a date',
            contents=j
        )
        line_bot_api.reply_message(event.reply_token, flex_message)

    elif "view" in message:
        j = json.load(open('to_do_menu.json','r',encoding='utf-8'))
        today = dt.now().date()
        tomorrow = str(today+timedelta(days=1))
        today_plus_2 = str(today+timedelta(days=2))
        today_plus_3 = str(today+timedelta(days=3))
        today_plus_4 = str(today+timedelta(days=4))
        label_list = ["today","tomorrow","the day after tomorrow",today_plus_3,today_plus_4,"other dates"]
        day_list = [str(today),tomorrow,today_plus_2,today_plus_3,today_plus_4,"other dates"]
        for i in range(len(j['footer']['contents'])):
            j['footer']['contents'][i]['action']['label'] = label_list[i]
            j['footer']['contents'][i]['action']['text'] = f"@{day_list[i]}"
        flex_message = FlexSendMessage(
            alt_text='to_do_menu',
            contents=j
        )
        task["view-mode"] = 1
        datastore_client.put(task)
        line_bot_api.reply_message(event.reply_token, flex_message)

    elif "+" in message:
        date = message.replace("+", "")
        task['date-to-add'] = date
        task['add-mode'] = 3
        datastore_client.put(task)
        line_bot_api.reply_message(event.reply_token, TextSendMessage("Please enter to-do: "))

    # edit
    elif "#" in message:
        m = message.replace("#", "")
        send = f"Your to-do on {m} includes: \n"
        m_to_send = display_to_do(send, task['to-do'][m])
        m_to_send += "\n"
        m_to_send += "\nPlease enter the number of the task you would like to edit: "
        task['edit-mode'] = 1
        task['date-to-edit'] = m
        datastore_client.put(task)

        line_bot_api.reply_message(event.reply_token, TextSendMessage(m_to_send))

    # delete
    elif "$" in message:
        m = message.replace("$", "")
        send = f"Your to-do on {m} includes: \n"
        try:
            m_to_send = display_to_do(send, task['to-do'][m])
            m_to_send += "\n"
            m_to_send += "\nPlease enter the number of the task you would like to delete: "
            task['delete-mode'] = 1
            task['date-to-delete'] = m
            datastore_client.put(task)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(m_to_send))
        except:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(f"You don't have any to-do on {m}"))

    # view today
    elif message == "today":
        today = dt.now().date()
        today = str(today)
        j = json.load(open('brown2.json','r',encoding='utf-8'))
        try:
            to_do = task['to-do'][today]
            if len(to_do) == 0:
                no_todo_found_reply(event, today)

            else:
                display_today(event,j,task,today)
        except:
            no_todo_found_reply(event, today)

    elif message == "help":
        j = json.load(open('questions.json','r',encoding='utf-8'))
        flex_message = FlexSendMessage(
            alt_text='contact',
            contents=j
        )
        line_bot_api.reply_message(event.reply_token, flex_message)

    elif message.strip().lower() == "reset":
        id = get_user_id(event)  # Fetch the user's unique identifier
        key = datastore_client.key('Task4', id)

        # Reinitialize the user's task state
        try:
            task = datastore_client.get(key=key)
            if task:
                task['game-mode'] = 0
                task['score'] = 20  # Reset score to the default value
                task['secret-number'] = None  # Clear secret number
                datastore_client.put(task)
                reply_message = "Your game state has been reset. You can start a new game."
            else:
                reply_message = "No existing game state found to reset."
        except Exception as e:
            print(f"Error resetting task: {e}")
            reply_message = "An error occurred while resetting your state. Please try again later."

        # Send the confirmation to the user
        line_bot_api.reply_message(event.reply_token, TextSendMessage(reply_message))


    else:
        message +="bot processing..."
        line_bot_api.reply_message(event.reply_token, TextSendMessage(message))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)
