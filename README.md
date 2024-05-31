# Consumers Energy Data Dashboard
This is a custom dashboard for viewing your personal Consumers Energy data. The goal of the dashboard is to serve as a way to "try out" other energy plans as well as see the efect of shifting some of your usage to times when energy is cheaper. 

![[Screenshot of main application page]](/images/preview.png)

# Pre-requisits
1. [Register as a third party](https://greenbutton.consumersenergy.com/third-party/register) for Consumers Energy through the Green Button platform.
2. [Grant your UtilityAPI account permissions to view your Consumers API data](https://utilityapi.com/settings#data-request-settings). You need to allow access to at least `Intervals` for this project to work but `Bills` and `Account Details` are also available.
3. Create a `.env` file in the root directory that has the following content: 

```toml
HEADERS = {"Authorization": "Bearer <Your UtilityAPI bearer token>"}
METERS = ["Your Meter IDs","Another Meter ID"]
```

# Running the program
1. Create and activate a virtual environment: 

    `python3 pip install virtualenv`

    `python3 -m virtualenv .venv`

    `source .venv/bin/activate`

2. install required packages:

    `pip install -r requirements.txt`

3. start the dashboard:

    `python3 main.py`

4. open the dashboard by navigating to `http://127.0.0.1:8050`