# Hack Night Check In

<a href="https://slack.com/oauth/v2/authorize?client_id=2524560276.937162414487&scope=commands,users.profile:read,chat:write"><img alt="Add to Slack" height="40" width="139" src="https://platform.slack-edge.com/img/add_to_slack.png" srcset="https://platform.slack-edge.com/img/add_to_slack.png 1x, https://platform.slack-edge.com/img/add_to_slack@2x.png 2x"></a>

We built this app at [OpenOakland](https://openoakland.org/) to track our hack night attendance.

On the frontend, we integrate with slack using a slash command to make it dead simple for brigade members to check in each night:

![checkin-demo](https://user-images.githubusercontent.com/16271389/78525574-6a411b80-778c-11ea-8f25-d930e36566e8.gif)


On the backend, we store everything in Google Sheets making it easy for any member to access and analyze our attendance information. (Our members names are blacked out below to respect their privacy)

<img width="970" alt="Screen Shot 2020-04-05 at 10 25 13 PM" src="https://user-images.githubusercontent.com/16271389/78525585-70cf9300-778c-11ea-8ed3-ed95f9e8edf7.png">


## Contributing

Currently [Gaurav](http://github.com/gauravmk/) is the only person working on this but if you are interested in getting involved, just let me (me being Gaurav) know. You can email me at gaurav@gauravkulkarni.com or hit me up on slack if you're on either the OpenOakland or Code for America slack.

Having both a slack app and a google app is required to be able to dev on this repo and I'm still in "dev on the prod apps" point with this repo. So if you're interested in working on this project, just hit me up and we can work through making the dev experience usable.

On the other hand, if you just want to tell me what's broken or what you wish was different, open up some github issues. I'm all for that.


## Tech stack

This is just in case you're curious. There are a few key dependencies:

#### Python

This is written in python 3. Really 3.6 or higher

#### Heroku

We're hosted on heroku at hacknight-checkin.herokuapp.com. Nothing actually lives at that index page though. 

#### Flask ([app.py](https://github.com/gauravmk/hacknight-checkin/blob/master/app.py))

We need a webserver for a couple reasons. Mostly oauth flows with slack and google, but also to receive the slash commands that members send. We use [flask](https://flask.palletsprojects.com/en/1.1.x/)

#### APScheduler ([app.py](https://github.com/gauravmk/hacknight-checkin/blob/master/app.py))

[APScheduler](https://apscheduler.readthedocs.io/) is a super basic scheduler library for python. We use it to periodically sync data from redis to google sheets.

#### Slack ([slack_client.py](https://github.com/gauravmk/hacknight-checkin/blob/master/slack_client.py))

Mostly it's just handling receiving the `/checkin` slash command from users though we occasionally use the web api. For instance, we grab users' display names to make the attendance sheet readable.

#### Google Sheets ([google_client.py](https://github.com/gauravmk/hacknight-checkin/blob/master/google_client.py))

We store everything in google sheets. We're using the sheets v4 api. You can find the quickstart for the API [here](https://developers.google.com/sheets/api/quickstart/python).

#### Redis ([redis_client.py](https://github.com/gauravmk/hacknight-checkin/blob/master/redis_client.py))

Redis is our datastore. All keys are namespaced with the prefix: `checkin:[your slack team id]:`.
