# Bus Reservation Automation

This script automates bus seat reservations for the Wellcome Genome Campus BusHub service.

## Features

- **Continuous Mode**: Books buses for the next 2 weeks (default behavior)
- **Home-Soon Mode**: Continuously monitors for PM bus availability and books as soon as it becomes available

## Usage

### Continuous Mode (Default)

Books buses for the next 2 weeks based on your configuration:

```bash
python reserve_bus_seats_bushub.py
# or
python reserve_bus_seats_bushub.py continuous
```

### Home-Soon Mode

Continuously monitors for PM bus availability and books immediately when available:

```bash
python reserve_bus_seats_bushub.py home-soon
```

You can also specify a custom check interval (in seconds):

```bash
python reserve_bus_seats_bushub.py home-soon --check-interval 60
```

## Configuration

### Required Files

1. **`login_details.txt`**: Contains your username and password in the format `username,password`
2. **`config.yaml`**: Defines your bus routes for each day of the week
3. **`bushub_cookie.txt`**: Contains your authentication cookie (automatically generated)

### Config.yaml Format

```yaml
days:
  Monday:
    AM:
      pickup: "Centennial Hotel - S"
      dropoff: "Wellcome Genome Campus"
    PM:
      pickup: "Wellcome Genome Campus"
      dropoff: "Brooklands Av - N (RQ)"
  # ... repeat for other days
```

## How It Works

### Continuous Mode

- Fetches the latest bus stop information from the API
- Updates `busroutes.yaml` with current route data
- Checks existing reservations to avoid duplicates
- Books buses for the next 2 weeks (weekdays only)

### Home-Soon Mode

- Monitors only the PM route for today
- Checks every 30 seconds (configurable) for bus availability
- Books immediately when a bus with available seats is found
- Stops when a reservation is successfully made or manually interrupted

## Requirements

- Python 3.6+
- Required packages: `requests`, `yaml`, `beautifulsoup4`

Install dependencies:

```bash
pip install requests pyyaml beautifulsoup4
```
