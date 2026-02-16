# HotelGen Job File Documentation

## Overview

The job file is a YAML configuration file that defines all parameters for generating a simulated hotel chain dataset. The file uses a nested structure under a top-level `job` key.

## File Structure

```yaml
job:
  database:
    # Database connection parameters
  generation:
    # Data generation parameters
```

## Parameter Reference

### Database Configuration

Located under `job.database`, these parameters control the database connection:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `host` | string | Yes | Database server hostname or IP address |
| `username` | string | Yes | Database username for authentication |
| `password` | string | Yes | Database password for authentication |
| `dbname` | string | Yes | Name of the database to use/create |

**Example:**
```yaml
database:
  host: "localhost"
  username: "hotelgen_user"
  password: "secure_password"
  dbname: "hotelgen_db"
```

### Generation Configuration

Located under `job.generation`, these parameters control the data generation process.

#### Date Range (`job.generation.dates`)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start` | string | Yes | Start date for simulation (format: YYYY-MM-DD) |
| `end` | string | Yes | End date for simulation (format: YYYY-MM-DD) |

**Example:**
```yaml
dates:
  start: "2024-01-01"
  end: "2024-12-31"
```

#### Hotel Generation (`job.generation.hotels`)

Controls how many properties are generated using a normal distribution.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `count` | integer | Yes | Mean (average) number of properties to generate |
| `sd` | integer | Yes | Standard deviation for property count |

The actual number of properties generated will be approximately `count ± sd` (minimum 10).

**Example:**
```yaml
hotels:
  count: 50   # Generate around 50 properties
  sd: 10      # With ±10 variation
```

#### Property Type Ratios (`job.generation.ratios`)

Controls the distribution of property types. All values are optional with defaults shown.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `resorts` | float | No | 0.05 | Fraction of properties that are resorts (5%) |
| `hotels` | float | No | 0.55 | Fraction of properties that are hotels (55%) |
| `motels` | float | No | 0.40 | Fraction of properties that are motels (40%) |

These should sum to approximately 1.0. Any rounding differences will be added to the resort count.

**Example:**
```yaml
ratios:
  resorts: 0.05  # 5% resorts
  hotels: 0.55   # 55% hotels
  motels: 0.40   # 40% motels
```

#### Customer Generation (`job.generation.customers`)

Controls how many customers are generated.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `count` | integer | Yes | - | Mean number of customers to generate |
| `sd` | integer | Yes | - | Standard deviation for customer count |
| `state_sd` | float | No | 0.2 | Standard deviation for geographic distribution |

**Example:**
```yaml
customers:
  count: 10000     # Generate around 10,000 customers
  sd: 500          # With ±500 variation
  state_sd: 0.2    # Geographic distribution variance
```

#### Simulation Settings (`job.generation`)

Top-level generation settings that control the daily simulation behavior.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `ramp_up_days` | integer | No | 45 | Number of days to gradually reach target occupancy |
| `target_occupancy` | float | No | 0.30 | Target occupancy rate (0.30 = 30%) |
| `target_occupancy_sd` | float | No | 0.05 | Daily variation in occupancy (5% variance) |

**Occupancy Behavior:**
- Days 1-`ramp_up_days`: Occupancy gradually increases from near 0% to `target_occupancy`
- After ramp-up: Occupancy fluctuates around `target_occupancy` with `target_occupancy_sd` variation
- Daily occupancy can range from 0% to 50% maximum

**Example:**
```yaml
ramp_up_days: 45           # Ramp up over 45 days
target_occupancy: 0.30     # Target 30% occupancy
target_occupancy_sd: 0.05  # ±5% daily variation
```

## Complete Example

See `sample.job.yaml` for a complete, working example configuration.

## Usage

Run HotelGen with your job file:

```bash
# Basic usage
python -m xl9045qi.hotelgen path/to/your.job.yaml

# With options
python -m xl9045qi.hotelgen path/to/your.job.yaml --drop --output mydata.pkl

# Generate without database (data only)
python -m xl9045qi.hotelgen path/to/your.job.yaml --no-database
```

## Default Job File

If no job file is specified, HotelGen defaults to: `dev/cis444-s26.job.yaml`
