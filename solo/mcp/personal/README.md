# Local Time MCP (Personal)

This MCP lives in the `solo-cli` repository under `mcp/personal`.

A simple LitServe-powered Microservice Control Protocol (MCP) that returns the server’s current local time—either in its own timezone or in any valid [Olson timezone](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) you specify.

## Features

- No heavy models required—just the Python standard library + `pytz`  
- Optional `timezone` parameter (e.g. `"America/Los_Angeles"`, `"Europe/London"`)  
- Returns ISO-style timestamp plus timezone abbreviation  
- Categorized under **Personal** MCPs in `mcp/personal`

## Requirements

- Python 3.8+  
- `litserve`  
- `pydantic`  
- `pytz`  

## Installation

1. From the root of your `solo-cli` repo, activate (or create) a Python virtual environment:
   ```bash
   cd /path/to/solo-cli
   python3 -m venv venv
   source venv/bin/activate
