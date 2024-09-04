# Bus Reservation System

Automate Genome Campus bus reservations based on a given schedule using the
`config.yaml` configuration file.

## Setup

### Prerequisites

- Python 3.x
- `yaml` library: Install with `pip install pyyaml`
- `BeautifulSoup` library: Install with `pip install beautifulsoup4`

### Configuration

1. Create the file `login_details.txt` in the root directory of the repository.
   This file should contain your username and password used to log into bus app.
   The file should be of format (without the quotes): "email,password"
1. Modify the `config.yaml` from the defaults provided in root directory of the
   repository.
1. Define your pickup and dropoff labels for each day of the week in the
   following format:

```{yaml}
days:
    Monday:
        AM:
            pickup: "Your Pickup Stop Label Here"
            dropoff: "Your Dropoff Stop Label Here"
        PM:
            pickup: "Your Pickup Stop Label Here"
            dropoff: "Your Dropoff Stop Label Here"
    Tuesday:
        AM:
            pickup: "Your Pickup Stop Label Here"
            dropoff: "Your Dropoff Stop Label Here"
        PM:
            pickup: "Your Pickup Stop Label Here"
            dropoff: "Your Dropoff Stop Label Here"
    ...
```
Replace "Your Pickup Stop Label Here" and "Your Dropoff Stop Label Here" with the
appropriate stop names. Do not use stop IDs directly; instead, use the stop labels
as defined in the bus routes (e.g., "St Paul's Rd", "Centennial Hotel").

The script will automatically look up the corresponding stop IDs and service numbers
based on the labels you provide in the config.yaml, using the busroutes.yaml lookup file.
To get the stop names, look inside the busroutes.yaml file.


### Usage

1. Run the main script:

   `python reserve_bus_seats_bushub.py`

2. The script will automatically book buses based on the configuration provided in config.yaml.
The stop codes and bus service numbers will be looked up dynamically from the busroutes.yaml based on the stop labels you define.
