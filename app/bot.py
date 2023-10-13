import getopt
import sys
import mongo
from datetime import date
import bothelper as bot
import time
import threading
from flask import Flask, request, jsonify
import telegram

test = False

opts, args = getopt.getopt(sys.argv[1:], "t", ["test"])
for opt, arg in opts:
  if opt in ("-t", "--test"):
      print("Test mode activated")
      test = True

host_name = "0.0.0.0"
port = 8090
app = Flask(__name__)




@app.route("/ticketEvent", methods=['POST'])
def eventFunc():
    print("Inside cold message function")
    request_data = request.data
    try:
        bot.sendColdMessage(request_data, test)
        return "succeeded"
    except:
        return "failed"


def main():
    while True:
        time.sleep(1)


threading.Thread(target=lambda: app.run(
    host=host_name, port=port, debug=False, use_reloader=False)).start()
threading.Thread(target=lambda: main()).start()
db = mongo.mongo()
bot.setup(test)

setup()
