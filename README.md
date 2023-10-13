# Tixel-Bot
A bot to assist buying tickets on tixel. Combining scalpel, a python web scraping framework and telegram bots, the tixel bot allows you to track a tixel event page and get notified when an event ticket falls below a certain price with direct link.

See more information in this blog post [coming soon]()

## Requirements
- Docker engine enviroment accessible to bot app (The docker image has been optimised for running on a linux enviroment)
- A mongodb database
- ScrapeOps proxy
- Telegram account with a bot account (Bot accounts can be created using the telegram botfather)

## Running this bot

### Account Details
These are the details and api keys needed to make this bot work

The mongodb, telegram and scrapeops connection data is put into the details.json files for the scraper, scraper runner and bot app.
Connection Data

| Name | Source/Example |
| ---- |  ----  |
| `"mongodb_password"` | `"password"` |
| `"mongodb_uri"` | [MongoDB connection string](https://www.mongodb.com/docs/manual/reference/connection-string/) |
| `"telegram_bot_key"` | [How Do I Create a Bot?](https://core.telegram.org/bots) |
| `"telegram_bot_key_test"` | Use the same key if you don't need a test bot [How Do I Create a Bot?](https://core.telegram.org/bots) |
| `"super_user"` | [Your telegram user id](https://medium.com/@tabul8tor/how-to-find-your-telegram-user-id-6878d54acafa) |
| `"proxy_api_key"` | [Integration Method 1 - API Endpoint](https://scrapeops.io/docs/proxy-aggregator/getting-started/api-basics/) |
| `"proxy_meta"` | [Integration Method 1 - API Endpoint](https://scrapeops.io/docs/proxy-aggregator/getting-started/api-basics/) |

### Installing python packages
Some packages are required to be installed to run this bot app. These can found inside `app/requirements.txt` file. 

Using conda (preferred)

`cd app/`

`conda create --name tixel --file requirements.txt`

Using pip

`cd app/`

`pip install -r requirements.txt`

### Creating the docker image
Firstly we need to create the scraper docker image. 

From the root directory

`cd scraper`

`docker build . -t scraper`

### Running the bot
To run the bot, from the root directory

`cd app`

`python bot.py`


## Important Details
- The docker scraper sends a web request from the docker container to localhost on the machine the docker engine is running. Calling localhost from within docker image will only allow access to whats inside the docker image. On a linux machine, you can access the localhost of the actual machine by using `http://host.docker.internal` instead of `http:/localhost`. This may not work for docker images running on mac, windows and other systems.
- Please ensure you use this bot responsibily and take note of tixel's terms of service. This bot is for personal, non-commercial use only
