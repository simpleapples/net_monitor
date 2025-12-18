# Network Monitor

A lightweight Python3 network connectivity monitoring tool that continuously checks network connectivity at multiple layers (PING, DNS, TCP) and logs failures.

## Features

- **Multi-layer monitoring**: Tests network at three different levels
  - PING: Tests connectivity to a target IP (network layer)
  - DNS: Tests domain name resolution (DNS layer)
  - TCP: Tests TCP port connectivity (transport layer)
- **Independent concurrent threads**: All three checks run independently without blocking each other
- **Failure logging only**: Only logs when a check fails, keeping logs clean
- **Configurable targets and timeout**: Customize monitoring targets and timeout duration
- **Docker support**: Easy deployment with Docker

## Requirements

- Python 3.6+
- System commands: `ping`, `dig`, `nc`

On Ubuntu/Debian:

```bash
sudo apt-get install iputils-ping dnsutils netcat-openbsd
```

On macOS:

```bash
# ping and dig come pre-installed
# nc is available as part of macOS
```

## Installation

### Direct Usage

1. Clone the repository:

```bash
git clone <repository-url>
cd net_monitor_v2
```

2. Run the monitor:

```bash
python3 network_monitor.py
```

### Docker Usage

1. Build the image:

```bash
docker build -t network-monitor .
```

2. Run the container:

```bash
docker run -d -v $(pwd)/logs:/app/logs network-monitor
```

## Usage

### Basic Usage

```bash
python3 network_monitor.py
```

Monitors with default settings:

- PING target: 8.8.8.8
- DNS target: google.com
- TCP target: google.com:80
- Timeout: 1 second
- Log directory: ./logs

### Custom Targets

```bash
python3 network_monitor.py \
  --ping 114.114.114.114 \
  --dns baidu.com \
  --tcp baidu.com:80 \
  --timeout 5 \
  --log-dir ./my_logs
```

### Command-line Arguments

- `--timeout <seconds>`: Command timeout in seconds (default: 1)
- `--log-dir <path>`: Log directory (default: ./logs)
- `--ping <ip>`: PING target IP (default: 8.8.8.8)
- `--dns <domain>`: DNS query target domain (default: google.com)
- `--tcp <host:port>`: TCP target host:port (default: google.com:80)

### Docker with Environment Variables

```bash
docker run -d \
  -e TIMEOUT=5 \
  -e PING_TARGET=114.114.114.114 \
  -e DNS_TARGET=baidu.com \
  -e TCP_TARGET=baidu.com:80 \
  -v $(pwd)/logs:/app/logs \
  network-monitor
```

Available environment variables:

- `TIMEOUT`: Command timeout in seconds (default: 1)
- `LOG_DIR`: Log directory (default: /app/logs)
- `PING_TARGET`: PING target IP (default: 8.8.8.8)
- `DNS_TARGET`: DNS query target domain (default: google.com)
- `TCP_TARGET`: TCP target host:port (default: google.com:80)

## Log Output

Logs are written to `./logs/network_monitor_YYYYMMDD.log` by default.

Example log output:

```
2025-12-16 10:23:45 - INFO - Network monitor started
2025-12-16 10:23:45 - INFO - Targets: {'ping': '8.8.8.8', 'dns': 'google.com', 'tcp': ('google.com', 80)}
2025-12-16 10:23:45 - INFO - Timeout: 1s
2025-12-16 10:24:50 - ERROR - ✗ PING 8.8.8.8 failed (return code: 1)
2025-12-16 10:24:51 - ERROR - ✗ DNS google.com timeout
2025-12-16 10:24:52 - ERROR - ✗ TCP google.com:80 failed
```

## Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Network Monitor                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Main Thread                           │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │ NetworkMonitor.__init__()                           │ │  │
│  │  │  - Parse command line arguments                     │ │  │
│  │  │  - Setup logging                                    │ │  │
│  │  │  - Read configuration                              │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  │                          │                                │  │
│  │                          ▼                                │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │ NetworkMonitor.monitor_loop()                       │ │  │
│  │  │  - Start 3 daemon threads                           │ │  │
│  │  │  - Keep main thread alive                           │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  └──────────────┬──────────────────┬──────────────────────────┘  │
│                 │                  │                             │
│    ┌────────────┘                  └────────────┐                │
│    │                                            │                │
│    ▼                    ▼                       ▼                 │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐       │
│  │ PING Thread │  │  DNS Thread  │  │  TCP Thread      │       │
│  └──────┬──────┘  └──────┬───────┘  └────────┬─────────┘       │
│         │                │                   │                 │
│         │                │                   │                 │
│  ┌──────▼──────┐  ┌──────▼───────┐  ┌────────▼─────────┐      │
│  │  _loop()    │  │  _loop()     │  │  _loop()         │      │
│  │             │  │              │  │                  │      │
│  │ while True: │  │ while True:  │  │ while True:      │      │
│  │   check()   │  │   check()    │  │   check()        │      │
│  │   sleep(1s) │  │   sleep(1s)  │  │   sleep(1s)      │      │
│  └──────▲──────┘  └──────▲───────┘  └────────▲─────────┘      │
│         │                │                   │                 │
│  ┌──────┴──────┐  ┌──────┴───────┐  ┌────────┴─────────┐      │
│  │check_ping() │  │check_dns()   │  │check_tcp()       │      │
│  │             │  │              │  │                  │      │
│  │ping -c 1    │  │dig +tries=1  │  │nc -zv -w timeout │      │
│  │-W timeout   │  │+time=timeout │  │host port         │      │
│  │target_ip    │  │target_domain │  │                  │      │
│  │             │  │              │  │Try/Except:       │      │
│  │Execute      │  │Execute       │  │TimeoutExpired    │      │
│  │Return code  │  │Check stdout  │  │Return code       │      │
│  │on failure   │  │on failure    │  │on failure        │      │
│  │Log error    │  │Log error     │  │Log error         │      │
│  └─────────────┘  └──────────────┘  └──────────────────┘      │
│         │                │                   │                 │
│         └────────────────┴───────────────────┘                 │
│                          │                                     │
│                          ▼                                     │
│              ┌──────────────────────┐                          │
│              │ Logging System       │                          │
│              │ ┌──────────────────┐ │                          │
│              │ │ File Handler     │ │                          │
│              │ │ logs/network_    │ │                          │
│              │ │ monitor_YYYYMMDD│ │                          │
│              │ │ .log             │ │                          │
│              │ └──────────────────┘ │                          │
│              │ ┌──────────────────┐ │                          │
│              │ │ Stream Handler   │ │                          │
│              │ │ (stdout)         │ │                          │
│              │ └──────────────────┘ │                          │
│              │ Only log ERRORS      │                          │
│              │ (failures)           │                          │
│              └──────────────────────┘                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Component Description

The monitor runs three independent daemon threads:

1. **PING Thread**: Continuously sends PING requests to the target IP with a timeout of `-W` milliseconds
2. **DNS Thread**: Continuously queries the target domain using `dig` with a timeout
3. **TCP Thread**: Continuously attempts TCP connections to the target host:port using `nc`

Each thread:

- Executes its check function in an infinite loop
- Waits 1 second between checks
- Logs only when a check fails
- Has its own timeout protection to prevent hanging

### Data Flow

```
Command Line Arguments / Environment Variables
        │
        ▼
    Parser (argparse)
        │
        ▼
NetworkMonitor.__init__()
        │
    ┌───┴───┬───────┬────────┐
    ▼       ▼       ▼        ▼
  Targets Timeout Logger Config
    │
    ├──► check_ping()  ──► Logs (on failure only)
    │
    ├──► check_dns()   ──► Logs (on failure only)
    │
    └──► check_tcp()   ──► Logs (on failure only)
         Each runs in independent thread
         Each sleeps 1 second between checks
```

## Troubleshooting

### nc command not found

Make sure `netcat-openbsd` is installed:

```bash
sudo apt-get install netcat-openbsd
```

### dig command not found

Install dnsutils:

```bash
sudo apt-get install dnsutils
```

### ping command not found

Install iputils-ping:

```bash
sudo apt-get install iputils-ping
```

### No log output

- Check that the log directory exists and is writable
- Verify that the monitoring targets are actually failing (logs only contain failures)
- Check log file: `tail -f logs/network_monitor_*.log`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.
