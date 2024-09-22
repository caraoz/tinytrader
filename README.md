# tinytrader
Exchange for educational purposes. Will have a trading engine with a web server to monitor order books and requests. Local environment is MacOS 15 with python 3.12


## TODO
- set up trading engine - OK! (single server)
- set up sample client - OK! 
- set up webserver to monitor engine OK!
- set up IEX historical pcap to stress test engine - later
- set up persistence - IN PROGRESS


## Install
python3 -m venv venv
pip3 install -r requirements.txt


## Description

Folder server/ contains server.py which is the order book and matching engine. The book accepts arbitrary usernames (no authentication other than a user_id tag) and only accepts LIMIT and MARKET orders. polling_server.py is a webserver that needs to be instantiated on another port to prevent the engine from crashing. The polling server only has 1 endpoint for the order book polling every 10 seconds. 

Folder client/ has many sample clients to send orders including a test file that generates random orders. Average request time is between 100-200ms on the dev machine. 

