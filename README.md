# Tixel-Bot
A bot to assist buying tickets on tixel. Combining scalpel, a python web scraping framework and telegram bots, the tixel bot allows you to track a tixel event page and get notified when an event ticket falls below a certain price with direct link.

See more information in this blog post <coming soon>

## Requirements
- Docker engine enviroment accessible to bot app (The docker image has been optimised for running on a linux enviroment)
- A mongodb database
- ScrapeOps proxy
- Telegram account with a bot account (Bot accounts can be created using the telegram botfather)

The mongodb, telegram and scrapeops connection data is put into the details.json files for the scraper, scraper runner and bot app.
Connection Data


## Running this bot


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
