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
1. Define your pickup and dropoff codes for each day of the week in the
   following format:

```{yaml}
days:
    Monday:
        AM:
            pickup: YOUR_PICKUP_CODE_HERE
            dropoff: YOUR_DROPOFF_CODE_HERE
        PM:
            pickup: YOUR_PICKUP_CODE_HERE
            dropoff: YOUR_DROPOFF_CODE_HERE
    Tuesday:
        AM:
            pickup: YOUR_PICKUP_CODE_HERE
            dropoff: YOUR_DROPOFF_CODE_HERE
        PM:
            pickup: YOUR_PICKUP_CODE_HERE
            dropoff: YOUR_DROPOFF_CODE_HERE
    ...
```

Replace `YOUR_PICKUP_CODE_HERE` and `YOUR_DROPOFF_CODE_HERE` with the
appropriate codes for each stop.

| CC Bus Stops            |       Stop IDs |
| :---------------------- | -------------: |
| St Paul's Rd - S        |   0500CCITY247 |
| Centennial Hotel - S    |   0500CCITY022 |
| Mander Way - S          |   0500CCITY236 |
| Opp Red Cross Lane - E  |   0500CCITY080 |
| Wellcome Genome Campus  | BUSHUBd6ZTW0SS |
| Red Cross Lane - W (RQ) |   0500CCITY081 |
| Mander Way - N (RQ)     |   0500CCITY234 |
| Botanic Gdns - N (RQ)   |   0500CCITY035 |
| St Paul's Rd - N (RQ)   |   0500CCITY222 |

### Usage

1. Run the main script:

   `python reserve_bus_seats_bushub.py`

2. The script will automatically book buses based on the configuration provided
   in `config.yaml`.
