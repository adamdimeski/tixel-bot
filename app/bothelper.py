from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
import mongo
from datetime import date
import docker
import asyncio
import json
import telegram
import uuid
import os

with open(str(os.path.dirname(__file__)) + '/details.json') as file:
    details = json.load(file)

MONGODB_URI = details['mongodb_uri']
MONGODB_DATABASE = details['mongodb_database']
superUser = details['super_user']
test = False




db = mongo.mongo()


URL, FREQUENCY, THRESHOLD = range(3)
START_ROUTES, END_ROUTES = range(2)
USER_ID = range(1)
MSG = range(1)
userData = dict()
userRegister = dict()


def urlDecodable(url) -> dict:
    segments = url.split('/')
    data = dict()
    if "2023" in segments:
        yearI = segments.index('2023')  # || segments.index('2023')
        data["expiry"] = date(int(segments[yearI]), int(
            segments[yearI + 1]), int(segments[yearI + 2]))
        data["year"] = "2023"
    elif "2024" in segments:
        yearI = segments.index('2024')  # || segments.index('2023')
        data["expiry"] = date(int(segments[yearI]), int(
            segments[yearI + 1]), int(segments[yearI + 2]))
        data["year"] = "2024"
    else:
        data["expiry"] = date(2023, 12, 12)
        data["year"] = "2023"

    data["name"] = segments[-1]
    return data


def writeToUserData(id, payload: dict):
    if id in userData.keys():
        for k, v in payload.items():
            userData[id][k] = v
    else:
        userData[id] = payload


def sendColdMessage(payload: str, test) -> list:
    data = sorted(json.loads(payload),
                  key=lambda d: d['price'], reverse=True)[:5]
    print(len(data))
    if len(data) > 0:
        eventName = data[0]['eventName']
        collection = db["orders"]
        orders = collection.find({'name': eventName})
        ticketcollection = db["tickets"]
        tickets = ticketcollection.find({'eventName': eventName})
        users = dict()
        for order in orders:
            if 'userId' in order.keys():
                users[order["userId"]] = order['threshold']
        print(str(orders))
        print(users)
        for ticket in tickets:
            if "notified" in ticket.keys():
                notified = ticket["notified"]
            else:
                notified = list()

            print(str(ticket))
            print(notified)

            for id in users.keys():
                print(str(id))
                if int(ticket['price']) <= int(users[id]) and int(id) not in notified:
                    notified.append(id)
                    resp = "Ticket Found! \n\n Event: " + \
                        ticket['eventName'] + " \n\n Price: $" + \
                        str(ticket['price']) + \
                        " \n\n Link: " + ticket['url']
                    asyncio.run(sendCold(int(id), resp, test))

            print(notified)
            ticketcollection.update_one({"ticketID": ticket["ticketID"]}, {
                                        "$set": {"notified": notified}})


async def sendCold(userId, msg, test):
    if test:
        mytoken = details["telegram_bot_test_key"]
    else:
        mytoken = details["telegram_bot_key"]
    await telegram.Bot(mytoken).sendMessage(chat_id=userId, text=msg)


def createEvent(url: str, threshold: str, frequency: str, id: int) -> bool:
    # check if event already exists
    # return if already exists or add one
    try:
        if startContainer(url, frequency):
            try:
                expiry = urlDecodable(url)["expiry"]
                name = urlDecodable(url)["name"]
                event = {"url": url, "name": name, "expiry": expiry.isoformat(
                ), "threshold": threshold, "frequency": frequency, "userId": id}
                orders = db["orders"]
                orders.insert_one(event)
                logs = db["order-log"]
                event["uuid"] = str(uuid.uuid4())
                event["type"] = "create"
                logs.insert_one(event)
                return True
            except Exception as e:
                print(e)
                return False
        else:
            return False
    except:
        print("Error starting up docker container")
        return False


def deleteEvent(url: str, id: int) -> bool:
    print(url)
    try:
        collection = db["orders"]
        deletedOrders = collection.find({"url": url, "userId": id})
        collection.delete_many({"url": url, "userId": id})
        collection = db["orders"]
        tickets = collection.find({"url": url})
        if len(list(tickets)) == 0:
            tickets = db["tickets"]
            tickets.delete_many({"eventName": urlDecodable(url)["name"]})

        logs = db["order-log"]
        print(deletedOrders)
        for order in deletedOrders:
            logEvent = dict(order)
            logEvent["uuid"] = str(uuid.uuid4())
            logEvent["type"] = "cancel"
            print(logEvent)
            logs.insert_one(logEvent)

        return True
    except Exception as e:
        print(e)
        return False


def reInitialiseDockerEvents():
    collection = db["orders"]
    orders = list(collection.find())
    print("Checking if containers exist for all orders")
    for order in orders:
        url = order["url"]
        if not containerExists(url):
            startContainer(url, int(order['frequency']))
            print("Started container for " + urlDecodable(url)["name"])
    print("All containers setup")

    # get all orders
    # check if containers exist for each orders
    # if not start docker container


def startContainer(url: str, frequency: int):
    # start a docker container with the event url, name
    container_name = "tixel-" + urlDecodable(url)["name"]
    image_name = "scraper:latest"
    command = ["-s", url, "-f", str(frequency)]
    dockerclient = docker.from_env()
    stopContainer(url)

    try:
        # Start the Docker container
        container = dockerclient.containers.run(
            image=image_name,
            name=container_name,
            command=command,
            extra_hosts={'host.docker.internal': '192.168.0.216'},
            environment={'HOST_IP': "localhost"},
            detach=True  # Run the container in the background
        )
        # Print the container ID
        print(
            f"Container {container.name} ({container.id}) started successfully.")
        return True
    except docker.errors.ImageNotFound as e:
        print(f"Image {image_name} not found. Please make sure it exists.")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


def containerExists(url: str):
    try:
        # Use the `containers.get()` method to get container information by name
        dockerclient = docker.from_env()
        container_name = "tixel-" + urlDecodable(url)["name"]
        container = dockerclient.containers.get(container_name)

        # Check if the container is running
        if container.status == "running":
            print(f"Container {container_name} exists and is running.")
        else:
            print(f"Container {container_name} exists but is not running.")
        return True
    except docker.errors.NotFound:
        print(f"Container {container_name} does not exist.")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


def stopContainer(url: str):
    if containerExists(url):
        container_name = "tixel-" + urlDecodable(url)["name"]
        dockerclient = docker.from_env()
        container = dockerclient.containers.get(container_name)
        container.stop()
        container.remove()
        return "Container Removed"
    else:
        return "Container does not exist"


def getTickets(url: str) -> list:
    collection = db["tickets"]
    tickets = list(collection.find(
        {"eventName": urlDecodable(url)["name"]}).limit(5))
    if len(tickets) == 0:
        return "Not tickets found for this event"
    else:
        output = ""
        for ticket in tickets:
            output += ticket["url"] + " \n Event Name: " + \
                ticket["eventName"] + " \n Price: $" + \
                str(ticket["price"]) + "\n\n"
        return output


def getOrders(userId) -> str:
    collection = db["orders"]
    if int(userId) != superUser:
        orders = list(collection.find({'userId': userId}))
    else:
        orders = list(collection.find({}))
    send = ""
    if len(list(orders)) == 0:
        return "No orders found"
    else:
        for preorder in orders:
            order = {"url": "", "name": "", "expiry": "",
                     "threshold": "", "frequency": ""}
            order.update(preorder)
            send += order["url"] + '\n Name: ' + order["name"] + '\n Expiry: ' + str(order["expiry"]) + '\n Threshold: $' + str(
                order["threshold"]) + '\n Frequency: ' + str(order["frequency"]) + ' mins\n' + "\n\n"
        print(send)
        return send


def updateUsers():
    collection = db["users"]
    users = list(collection.find({}))
    for user in users:
        print(user)
        userRegister[int(user['id'])] = dict(user)


def verifyPayload(id, payload):
    if isVerified(id):
        return payload
    else:
        return "You are not verified to use this bot. Please send /register to register to this service."


def isVerified(id) -> bool:
    if int(id) == superUser:
        return True
    elif int(id) in userRegister.keys():
        return userRegister[int(id)]['verified']
    else:
        updateUsers()
        if int(id) in userRegister.keys():
            userRegister[int(id)]['verified']
        else:
            return False


def isRegistered(id) -> bool:
    print(id)
    print(userRegister)
    if id == superUser:
        return True
    elif int(id) in userRegister.keys():
        return True
    else:
        updateUsers()
        if int(id) in userRegister.keys():
            return True
        else:
            return False


def getUsers() -> str:
    collection = db["users"]
    updateUsers()
    retval = ""
    for id in userRegister.keys():
        user = userRegister[id]
        retval += " ID: " + str(user["id"]) + "\n Verified: " + str(user['verified']) + '\n Username: ' + \
            str(user['username']) + '\n Name: ' + \
            str(user["first_name"]) + " " + str(user["last_name"]) + "\n\n"
    return retval


def addUser(user: dict) -> str:
    collection = db["users"]
    users = collection.update_one(
        {"id": int(user["id"])}, {"$set": user}, True)


def verifyUser(id, verified):
    if isRegistered(id):
        collection = db["users"]
        # print(collection.find({"id": int(id)}))
        users = collection.update_one(
            {"id": int(id)}, {"$set": {"verified": verified}}, False)


def notifyUser(ticketUrl: str, userID: str, eventName: str) -> list:
    # send a telgram message to the user
    pass


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f' {str(getTickets("", ""))}')


async def getEventsHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Endpoint for accepting events')


async def getOrdersHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not isVerified(update.message.from_user.id):
        await update.message.reply_text(f'Not verified for this service')
        return ConversationHandler.END
    await update.message.reply_text(f' {str(getOrders(int(update.message.from_user.id)))}')


async def startgetTicketsHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not isVerified(update.message.from_user.id):
        await update.message.reply_text(f'Not verified for this service')
        return ConversationHandler.END

    await update.message.reply_text(f'What is the url of the event?')
    return URL


async def startverifyUserHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'What is the id of the user you would like to verify?')
    return USER_ID


async def startunverifyUserHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'What is the id of the user you would like to un-verify?')
    return USER_ID


async def startbroadcastHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'What is message you would like to broadcast to users?')
    return MSG


async def getUsersHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not isVerified(update.message.from_user.id):
        await update.message.reply_text(f'Not verified for this service')
        return ConversationHandler.END

    retval = getUsers()
    await update.message.reply_text(f'' + retval)


async def getTicketsHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not isVerified(update.message.from_user.id):
        await update.message.reply_text(f'Not verified for this service')
        return ConversationHandler.END

    url = update.message.text
    resp = getTickets(url)
    await update.message.reply_text(f'' + resp)
    return ConversationHandler.END


async def verifyUserHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    id = update.message.text
    # check if user is in system. If not, return user is not registered.
    if isRegistered(id):
        if isVerified(id):
            resp = "User is already verified"
        else:
            verifyUser(id, True)
            resp = "User has been verified"
            updateUsers()
    else:
        resp = "User is not registered"
    await update.message.reply_text(f'' + resp)
    return ConversationHandler.END


async def broadcastHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # check if user is in system. If not, return user is not registered.
    msg = str(update.message.text)
    for id in userRegister.keys():
        if userRegister[id]['verified']:
            await sendCold(id, msg)

    await update.message.reply_text(f' Message broadcasted')
    return ConversationHandler.END


async def unverifyUserHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    id = update.message.text
    # check if user is in system. If not, return user is not registered.
    if isRegistered(id):
        if isVerified(id):
            verifyUser(id, False)
            resp = "User has been verified"
            updateUsers()
        else:
            resp = "User has not registered"

    else:
        resp = "User is not registered"
    await update.message.reply_text(f'' + resp)
    return ConversationHandler.END


async def orderURL(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not isVerified(update.message.from_user.id):
        await update.message.reply_text(f'Not verified for this service')
        return ConversationHandler.END

    try:
        url = str(update.message.text)
        segments = url.split('/')
        try:
            name = urlDecodable(url)["name"]
        except Exception as e:
            print(e)

        writeToUserData(update.message.from_user.id, {"url": url})
    except:
        await update.message.reply_text(f'Failed to decode url.')
        return ConversationHandler.END

    await update.message.reply_text(f'What is the ticket price threshold?')
    return THRESHOLD


async def orderThreshold(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not isVerified(update.message.from_user.id):
        await update.message.reply_text(f'Not verified for this service')
        return ConversationHandler.END

    # get threshold from text
    '''keyboard = [
        [
            InlineKeyboardButton("5 min", callback_data="5"),
            InlineKeyboardButton("10 min", callback_data="10"),
            InlineKeyboardButton("30 min", callback_data="30"),
            InlineKeyboardButton("1 hour", callback_data="60"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)'''
    try:
        val = str(update.message.text).strip("$")
        thresh = int(val)
        writeToUserData(update.message.from_user.id, {"threshold": thresh})
    except:
        await update.message.reply_text(f'Failed to decode threshold. Please make sure the value is a number.')
        return ConversationHandler.END
    # await update.message.reply_text(f'What is the frequency?', reply_markup=reply_markup)
    await update.message.reply_text(f'What is the update frequency? (min)')
    return FREQUENCY


async def orderFrequency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not isVerified(update.message.from_user.id):
        await update.message.reply_text(f'Not verified for this service')
        return ConversationHandler.END

    # get the order frequency from the text
    try:
        val = str(update.message.text).strip("m").strip("min")
        freq = int(val)
        writeToUserData(update.message.from_user.id, {"frequency": freq})
    except:
        await update.message.reply_text(f'Failed to decode threshold. Please make sure the value is a number.')
        return ConversationHandler.END
    # context.bot.send_message(job.chat_id, text=f"Beep! {job.data} seconds are over!")(f'Attempting to track event' + str(userData[update.message.from_user.id]), reply_markup=reply_markup)
    res = createEvent(userData[update.message.from_user.id]['url'], userData[update.message.from_user.id]
                      ['threshold'], userData[update.message.from_user.id]['frequency'], int(update.message.from_user.id))
    resp = ""
    if res:
        resp = "Successfully tracked event"
    else:
        resp = "Event tracking failed"
    await update.message.reply_text(f'' + resp)
    return ConversationHandler.END


async def cancelOrder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not isVerified(update.message.from_user.id):
        await update.message.reply_text(f'Not verified for this service')
        return ConversationHandler.END

    # get the order frequency from the text
    url = update.message.text
    res = deleteEvent(url, int(update.message.from_user.id))
    resp = ""
    if res:
        resp = "Successfully deleted order(s)"
    else:
        resp = "Event order cancellation failed"
    await update.message.reply_text(f'' + resp)
    return ConversationHandler.END


async def createOrderhandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # return the name and the expiry of the event. Ask for pricing threshold and frequency
    if not isVerified(update.message.from_user.id):
        await update.message.reply_text(f'Not verified for this service')
        return ConversationHandler.END

    await update.message.reply_text(f'What is the url of the event you would like to track?')
    return URL


async def cancelOrderHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not isVerified(update.message.from_user.id):
        await update.message.reply_text(f'Not verified for this service')
        return ConversationHandler.END

    await update.message.reply_text(f'What is the url of the order you would like to cancel?')
    return URL


# async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     keyboard = [
#         [
#             InlineKeyboardButton("Tracked Orders", callback_data="/orders"),
#             InlineKeyboardButton("Get Event Tickets",
#                                  callback_data="/tickets"),
#         ],
#         [
#             InlineKeyboardButton("Track a new event", callback_data="/create"),
#             InlineKeyboardButton("Cancel an order", callback_data="/cancel"),
#         ],
#     ]
#     print(update.message.from_user.id)
#     reply_markup = InlineKeyboardMarkup(keyboard)
#     await update.message.reply_text(f'help screen', reply_markup=reply_markup)

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    resp = "Welcome to the tixel helper bot. I can help you find cheap tickets on tixel. \
    \n\n Note: This is beta product. This bot may be offline and unresponsive without notice. \
    \n\nCommands \
    \n/register    Register your telegram account with our service. You must wait to be be verified to use our service. \
    \n/orders      Lists the orders you are currently tracking \
    \n/tickets     Lists the tickets for an event being tracked \
    \n/create      Add a tixel event to be tracked. You will be notified when tickets fall below a threshold price \
    \n/cancel      Stop tracking an event \
    \n\nHow to track an event \
    \n\nTo track an event, you will need to go to tixel and find the event page of the event you would like to track. Copy the url and provide it to me when creating an event. \
    \nThe url should look like this \
    \nhttps://tixel.com/au/music-tickets/2023/09/29/jet-the-fortitude-music-hall-bri \
    \n\nNote: some urls cannot be tracked"
    await update.message.reply_text(f'' + resp)


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    userObj = update.message.from_user
    user = {'id': int(userObj.id), "first_name": userObj.first_name,
            "last_name": userObj.last_name, "username": userObj.username, "verified": False}
    res = ""
    updateUsers()
    if user['id'] in userRegister.keys():
        if isVerified(user['id']):
            res = "You are already registered and verified"
        else:
            res = "You have already registered. Please wait for verification."
    else:
        addUser(user)
        res = "Thank for you registering. Please wait for verification."
    await update.message.reply_text(f'' + res)


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'This is the tixel bot. I can help you find tickets on tixel.\n\n User /help to find all the available commands I can use.')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'This is the tixel bot. I can help you find tickets on tixel.\
    \n\n Use /help to find all the available commands that I can use. \
    \n\n To use this bot, you must first register. You can either type in /register or type in /help to access the help menu')


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns `ConversationHandler.END`, which tells the
    ConversationHandler that the conversation is over.
    """
    query = update.callback_query
    await query.answer()
    print(query.message.chat.id)
    if query.data == "/orders":
        return 10


def setup(test):
    if test:
        mytoken = details["telegram_bot_test_key"]
    else:
        mytoken = details["telegram_bot_key"]
        reInitialiseDockerEvents()

    updateUsers()

    bot = ApplicationBuilder().token(mytoken).build()
    bot.add_handler(CommandHandler("hello", hello))
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("orders", getOrdersHandler))
    bot.add_handler(CommandHandler("help", help))
    bot.add_handler(CommandHandler("register", register))
    bot.add_handler(CommandHandler("users", getUsersHandler,
                    filters=filters.Chat(superUser)))
    bot.add_handler(CommandHandler("info", info))
    createOrderConversation = ConversationHandler(
        entry_points=[CommandHandler(
            "create", createOrderhandler)],
        states={
            URL: [MessageHandler(filters.ALL, orderURL)],
            THRESHOLD: [MessageHandler(filters.ALL, orderThreshold)],
            FREQUENCY: [MessageHandler(filters.ALL, orderFrequency)],
        },
        fallbacks=[CommandHandler("help", help)],
    )
    bot.add_handler(createOrderConversation)

    deleteOrderConversation = ConversationHandler(
        entry_points=[CommandHandler(
            "cancel", cancelOrderHandler)],
        states={
            URL: [MessageHandler(filters.ALL, cancelOrder)],
        },
        fallbacks=[CommandHandler("help", help)],
    )
    bot.add_handler(deleteOrderConversation)

    getTicketsConversation = ConversationHandler(
        entry_points=[CommandHandler(
            "tickets", startgetTicketsHandler)],
        states={
            URL: [MessageHandler(filters.ALL, getTicketsHandler)],
        },
        fallbacks=[CommandHandler("help", help)],
    )
    bot.add_handler(getTicketsConversation)

    verifyUserConversation = ConversationHandler(
        entry_points=[CommandHandler(
            "verify", startverifyUserHandler, filters=filters.Chat(superUser))],
        states={
            USER_ID: [MessageHandler(filters.ALL, verifyUserHandler)],
        },
        fallbacks=[CommandHandler("help", help)],
    )
    bot.add_handler(verifyUserConversation)

    unverifyUserConversation = ConversationHandler(
        entry_points=[CommandHandler(
            "unverify", startunverifyUserHandler, filters=filters.Chat(superUser))],
        states={
            USER_ID: [MessageHandler(filters.ALL, unverifyUserHandler)],
        },
        fallbacks=[CommandHandler("help", help)],
    )
    bot.add_handler(unverifyUserConversation)

    broadcastConversation = ConversationHandler(
        entry_points=[CommandHandler(
            "broadcast", startbroadcastHandler, filters=filters.Chat(superUser))],
        states={
            MSG: [MessageHandler(filters.ALL, broadcastHandler)],
        },
        fallbacks=[CommandHandler("help", help)],
    )
    bot.add_handler(broadcastConversation)

    bot.run_polling()
