#!/usr/bin/env python3

from requests import HTTPError
import argparse
from tqdm import tqdm
from tasks import TaskHandler
#from ultra_rest_client.connection import RestApiConnection
import ultra_auth
import logging
import json
import zipfile
import os
import time

REPO_URL = "https://github.com/vercara/udns_snapshot"

class CustomHelpParser(argparse.ArgumentParser):
    def print_help(self, *args, **kwargs):
        ascii_art = """
  .-------------------.
 /--\"--.------.------/|
 |UDNS |__Ll__| [==] ||
 |     | .--. | \"\"\"\" ||
 |     |( () )|      ||
 |     | `--. |      |/
 `-----'------'------'
"""
        print(ascii_art)
        super().print_help(*args, **kwargs)

def get_zones(client):
    zones = []
    cursor = ""
    while True:
        response = client.get(f"/v3/zones?limit=1000&cursor={cursor}")
        zones.extend(response.get("zones", []))
        cursor = response["cursorInfo"].get("next")
        if not cursor:
            break
    return zones

def get_zones_from_file(filename):
    with open(filename, "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def prompt_confirmation(action_description):
    RED = "\033[91m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"
    print(f"{RED}WARNING:{RESET} {YELLOW}You are about to {action_description}. This cannot be undone.{RESET}")
    confirmation = input(f"Type '{YELLOW}UNDERSTOOD{RESET}' (case sensitive) to proceed or anything else to terminate: ")
    if confirmation != "UNDERSTOOD":
        print(f"{RED}Operation terminated.{RESET}")
        exit(0)

def get_snapshot(client, zone):
    logging.info(f"[DOWNLOAD] Creating backup of {zone}.")
    try:
        response = client.get(f"/v1/zones/{zone}/snapshot")
        logging.info(f"[SUCCESS] Snapshot downloaded for {zone}.")
        return response
    except HTTPError as e:
        if e.response.status_code in [400, 404]:
            logging.error(f"[SKIP] Unable to download {zone} snapshot. Either this zone cannot be snapshotted (secondary/alias), a snapshot doesn't exist or you don't have permission. HTTP Error: {e.response.status_code}")
        else:
            logging.error(f"[FATAL] An unexpected error occurred trying to download {zone}.")

def create_snapshot(client, zone):
    logging.info(f"[CREATE] Beginning snapshot of {zone}.")
    try:
        response = client.post(f"/v1/zones/{zone}/snapshot", {"description": f"Snapshot generated by {REPO_URL}"})
        task = response["task_id"]
        logging.info(f"[SUCCESS] Snapshot initiated for {zone}. Task ID: {task}")
        return task
    except HTTPError as e:
        if e.response.status_code in [400, 404]:
            logging.error(f"[SKIP] Unable to snapshot {zone}. Either this zone cannot be snapshotted (secondary/alias) or you don't have permission. HTTP Error: {e.response.status_code}")
        else:
            logging.error(f"[FATAL] An unexpected error occurred trying to snapshot {zone}.")
            raise

def restore_snapshot(client, zone):
    logging.info(f"[RESTORE] Beginning restore of {zone}.")
    try:
        response = client.post(f"/v1/zones/{zone}/restore", {})
        task = response["task_id"]
        logging.info(f"[SUCCESS] Restore initiated for {zone}. Task ID: {task}")
        return task
    except HTTPError as e:
        if e.response.status_code in [400, 404]:
            logging.error(f"[SKIP] Unable to restore {zone}. Either this zone cannot be restored (secondary/alias), you don't have permission or no snapshot exists. HTTP Error: {e.response.status_code}")
        else:
            logging.error(f"[FATAL] An unexpected error occurred trying to restore {zone}.")
            raise

def verify_task(client, task):
    logging.info(f"[VERIFY] Checking status of {task}.")
    handler = TaskHandler(client)
    try:
        response = handler.wait(task, 1)
        rcode = response["code"]
        message = response["message"]
        if rcode != "COMPLETE":
            logging.error(f"[FAILED] {task} indicates it was not successfully processed: {message}")
        else:
            logging.info(f"[SUCCESS] {task} completed: {message}")
    except Exception as e:
        logging.error(f"[FATAL] An unexpected error occurred retrieving {task}: {e.message}")
        raise

def backup_zones_to_zip(zones):
    timestamp = int(time.time())
    zip_filename = f'snapshot-backup_{timestamp}.zip'
    
    # Temporary directory to store the json files
    temp_dir = 'temp_zone_files'
    os.makedirs(temp_dir, exist_ok=True)
    
    # Create JSON files
    for zone in zones:
        try:
            file_name = f"{zone['zone_snapshot']['zoneName']}.json"
            file_path = os.path.join(temp_dir, file_name)
            with open(file_path, 'w') as file:
                logging.info(f"[DOWNLOAD] Writing '{file_name}'' to '{file_path}''.")
                json.dump(zone['zone_snapshot'], file, indent=4)
        except:
            logging.info(f"[SKIP] Skipping {zone['zone_name']}, reason: {json.dumps(zone['zone_snapshot'])}")

    
    # Create a zip file and add all JSON files
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        logging.info(f"[DOWNLOAD] Creating archive '{zip_filename}'.")
        for file_name in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, file_name)
            zipf.write(file_path, arcname=file_name)
    
    # Clean up the temporary files
    logging.info("[DOWNLOAD] Cleaning up temp files.")
    for file_name in os.listdir(temp_dir):
        os.remove(os.path.join(temp_dir, file_name))
    os.rmdir(temp_dir)
    
    return zip_filename

def main(username=None, password=None, token=None, refresh_token=None, restore=False, log_file='output.log', download=False, zones_file=None):
    logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # We will be migrating to github.com/ultradns/python_rest_api_client soon
    # client = RestApiConnection(host='api.ultradns.com')
    # if token:
    #     client.access_token = token
    #     client.refresh_token = refresh_token
    # else:
    #     client.auth(username, password)

    if token:
        client = ultra_auth.UltraApi(token, refresh_token, True)
    else:
        client = ultra_auth.UltraApi(username, password)

    if zones_file:
        zone_names = get_zones_from_file(zones_file)
    else:
        zones = get_zones(client)
        zone_names = [z['properties']['name'] for z in zones]

    if download:
        zone_snapshots = []
        for zone in tqdm(zone_names, desc="Downloading and zipping snapshot backups"):
            zone_snapshot = get_snapshot(client, zone)
            if zone_snapshot:
                zone_snapshots.append({'zone_snapshot': zone_snapshot, 'zone_name': zone})

        if zone_snapshots:
            backup_zones_to_zip(zone_snapshots)
        else:
            logging.info(f"[SKIP] No existing snapshots found for {zone}.")

    elif restore:
        prompt_confirmation("roll zones back to their most recent snapshot")
        for zone in tqdm(zone_names, desc="Restoring zones to their most recent snapshot"):
            task = restore_snapshot(client, zone)
            if task:
                verify_task(client, task)

    else:
        prompt_confirmation("overwrite zone snapshots with a new snapshot representing their current state")
        for zone in tqdm(zone_names, desc="Creating zone snapshots"):
            task = create_snapshot(client, zone)
            if task:
                verify_task(client, task)

    print(f"Script completed. Check {log_file} for more information.")

if __name__ == "__main__":
    parser = CustomHelpParser(description="UltraDNS Zone Snapshot")

    auth_group = parser.add_argument_group('authentication')
    auth_group.add_argument("-u", "--username", help="Username for authentication")
    auth_group.add_argument("-p", "--password", help="Password for authentication")
    auth_group.add_argument("-t", "--token", help="Directly pass the Bearer token")
    auth_group.add_argument("-r", "--refresh-token", help="Pass the Refresh token (optional with --token)")
    
    parser.add_argument("-s", "--restore", action="store_true", help="Loops through zones and restores them to their most recent snapshot.")
    parser.add_argument("-l", "--log-file", default="output.log", help="Specify the log file name. Default is 'output.log'.")
    parser.add_argument("-d", "--download", action="store_true", help="Download a zip file with all existing snapshots in an account or specified list.")
    parser.add_argument("-z", "--zones-file", help="Specify a file containing a list of zones (one per line).")
    parser.add_argument("-a", "--all-zones", action="store_true", help="Iterate through every zone in a given account.")

    args = parser.parse_args()

    if args.token:
        if args.username or args.password:
            parser.error("You cannot provide a token along with a username or password.")
    elif args.username and args.password:
        pass
    elif args.username or args.password:
        parser.error("You must provide both a username and password.")
    else:
        parser.error("You must provide either a token, or both a username and password.")

    if not (args.zones_file or args.all_zones):
        parser.error("You either need to specify a file containing a list of zones or use the --all-zones switch.")

    main(args.username, args.password, args.token, args.refresh_token, args.restore, args.log_file, args.download, args.zones_file)
