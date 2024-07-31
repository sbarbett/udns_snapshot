# udns_snapshot

This script provides a basic CLI for taking snapshots of all zones within an UltraDNS account. Additionally, there's functionality to restore zones to their most recent snapshots.

## Features

- **Snapshot All Zones**: Quickly generate snapshots for all zones in the UltraDNS account.
- **Restore Zones from Snapshots**: Restore all zones to their most recent snapshot.
- **Selective Zone Processing**: Specify a file to process only a subset of zones.
  
## Prerequisites

- Python 3.x
- Libraries: 
	- `requests` (should be automatically installed with `ultra_auth`)
	- `tqdm` 
	- `ultra_auth`

## Usage

1. Clone the repository:

   ```
   git clone https://github.com/sbarbett/udns_snapshot.git
   ```

2. Navigate to the directory:

   ```
   cd udns_snapshot
   ```

3. Make sure the script is executable:

   ```
   chmod +x src/snapshot.py
   ```

4. Run the script:

   ```
   ./src/snapshot.py [options]
   ```

   Options include:

   - Authentication:
     - `-u` or `--username`: Username for authentication.
     - `-p` or `--password`: Password for authentication.
     - `-t` or `--token`: Directly pass the Bearer token.
     - `-r` or `--refresh-token`: Pass the Refresh token (optional with --token).

   - Actions:
     - `-s` or `--restore`: Restore zones to their most recent snapshot.
     - `-l` or `--log-file`: Specify the log file name (default is `output.log`).
     - `-d` or `--download`: Download a zip file with all existing snapshots.
     - `-z` or `--zones-file`: Specify a file with a list of zones to process.
     - `-a` or `--all-zones`: Process every zone in an account (use with caution).

## Notes

- It's essential to use this script with caution, especially the restore functionality, as it's a destructive action that can't be undone.
- By default, the script writes logs to `output.log`. You can change this with the `-l` option.
