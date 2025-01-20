import subprocess
import paramiko
import re
import time
from datetime import datetime
import os
import requests

TARGET_DEVICES = ["PTX1_1_RE0","PTX2_2_RE0","PTX3_3_RE0","PTX4_4_RE0", "vMX1_RE", "vMX2_RE", "vMX3_RE", "vMX4_RE", "vRR1_RE", "vRR2_RE"]

def get_vmm_ip_addresses():
    """
    Execute the 'vmm ip' command and parse the IP addresses.
    - Filters only the target devices specified in TARGET_DEVICES.
    """
    try:
        result = subprocess.run(["vmm", "ip"], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split("\n")
        ip_addresses = {}
        for line in lines:
            # Match device names and IP addresses from command output
            match = re.match(r"(\S+)\s+(\d+\.\d+\.\d+\.\d+)", line)
            if match:
                device, ip = match.groups()
                if device in TARGET_DEVICES:  # Include only target devices
                    ip_addresses[device] = ip
        return ip_addresses
    except subprocess.CalledProcessError as e:
        print(f"Error executing 'vmm ip': {e}")
        return {}

def check_vmm_ping(ip_addresses):
    """
    Perform 'vmm ping' and verify if devices are alive.
    - Matches the device names and IPs that respond as 'alive'.
    """
    try:
        result = subprocess.run(["vmm", "ping"], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split("\n")
        alive_devices = {}
        for line in lines:
            match = re.match(r"(\S+)\s+(\d+\.\d+\.\d+\.\d+)\s+alive", line)
            if match:
                device, ip = match.groups()
                if device in ip_addresses:  # Ensure device exists in initial list
                    alive_devices[device] = ip
        return alive_devices
    except subprocess.CalledProcessError as e:
        print(f"Error executing 'vmm ping': {e}")
        return {}

def backup_configuration(alive_devices):
    """
    SSH into each alive device and capture its configuration.
    - Captures the configuration using 'show configuration | display set | except "groups global"'.
    """
    all_configurations = {}
    for device, ip in alive_devices.items():
        print(f"\nConnecting to {device} ({ip})...")
        try:
            # Initialize SSH connection
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=ip, username="root", password="Embe1mpls", timeout=10)

            # Start an interactive shell session
            shell = ssh.invoke_shell()
            shell.settimeout(60)

            # Enter CLI mode
            shell.send("cli\n")
            time.sleep(1)
            cli_output = shell.recv(8192).decode('utf-8', errors='ignore')

            if not (">" in cli_output or "%" in cli_output or "root@" in cli_output):
                print(f"Error: Failed to enter CLI mode on {device}")
                continue

            # Capture configuration excluding 'groups global'
            shell.send("show configuration | display set | except \"groups global\" | no-more\n")
            config_output = ""
            while True:
                time.sleep(1)
                if shell.recv_ready():
                    part = shell.recv(49152).decode('utf-8', errors='ignore')
                    config_output += part
                    if ">" in part or "%" in part or "root@" in part:
                        break
                else:
                    if len(config_output) > 0:
                        break

            if not config_output.strip():
                print(f"No configuration output received from {device}.")
            else:
                all_configurations[device] = config_output
                print(f"Configuration captured for {device}")

            # Close the SSH connection
            ssh.close()

        except paramiko.ssh_exception.SSHException as e:
            print(f"SSH error for {device}: {str(e)}")
        except Exception as e:
            print(f"Failed to connect to {device}: {str(e)}")
    return all_configurations

def save_configurations_to_file(configurations):
    """
    Save captured configurations to a timestamped text file.
    - Each device's configuration is saved under its own section in the file.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"configuration_backup_{timestamp}.txt"
    with open(filename, 'w') as file:
        for device, config in configurations.items():
            file.write(f"\nDevice: {device}\n{'=' * 40}\n{config}\n")
    print(f"\nConfigurations successfully saved to {filename}")
    return filename

def create_github_repo(username, token, repo_name):
    """
    Create a new GitHub repository using the GitHub API or verify if it exists.
    """
    repo_url = f"https://api.github.com/repos/{username}/{repo_name}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Check if the repository already exists
    response = requests.get(repo_url, headers=headers)
    if response.status_code == 200:
        print(f"Repository '{repo_name}' already exists. Skipping creation.")
        return

    # Create the repository if it doesn't exist
    url = "https://api.github.com/user/repos"
    data = {
        "name": repo_name,
        "private": False
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 201:
        print(f"Repository '{repo_name}' created successfully.")
    else:
        print(f"Failed to create repository: {response.json()}")
        raise Exception("Repository creation failed.")

def upload_to_github(file_path):
    """
    Prompt user for GitHub repository details and upload the file.
    - Initializes a Git repository, adds the file, and pushes it to the specified GitHub repo.
    """
    repo_name = input("Enter the name of the GitHub repository: ").strip()
    username = input("Enter your GitHub username: ").strip()
    token = input("Enter your GitHub personal access token: ").strip()

    if not repo_name or not username or not token:
        print("Repository name, username, and token cannot be empty.")
        return

    try:
        create_github_repo(username, token, repo_name)

        print(f"Uploading to repository: {repo_name}")

        # Initialize Git in the current directory
        os.system("git init")
        os.system(f"git remote add origin https://{username}:{token}@github.com/{username}/{repo_name}.git")

        # Add the file, commit, and push to GitHub
        os.system(f"git add {file_path}")
        os.system("git commit -m \"Add configuration backup\"")
        os.system("git branch -M main")
        os.system("git push -u origin main")

        print(f"Backup uploaded to GitHub repository: {repo_name}")
    except Exception as e:
        print(f"Failed to upload to GitHub: {str(e)}")

if __name__ == "__main__":
    # Step 1: Retrieve IP addresses of devices
    ip_addresses = get_vmm_ip_addresses()
    if not ip_addresses:
        print("No IP addresses found.")
        exit(1)

    # Step 2: Check which devices are alive
    alive_devices = check_vmm_ping(ip_addresses)
    if not alive_devices:
        print("No alive devices found.")
        exit(1)

    # Step 3: Backup configurations from alive devices
    configurations = backup_configuration(alive_devices)

    # Step 4: Save configurations and upload to GitHub if available
    if configurations:
        backup_file = save_configurations_to_file(configurations)
        upload_to_github(backup_file)
    else:
        print("No configurations were captured.")

