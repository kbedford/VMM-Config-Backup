import subprocess
import paramiko
import re
import time
from datetime import datetime

# Updated credentials
username = "root"
password = "Embe1mpls"

def get_vmm_ip_addresses():
    """Execute the 'vmm ip' command and parse the IP addresses."""
    try:
        result = subprocess.run(["vmm", "ip"], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split("\n")
        ip_addresses = {}
        for line in lines:
            # Match device and IP addresses, excluding MPC0 entries
            match = re.match(r"(\S+)\s+(\d+\.\d+\.\d+\.\d+)", line)
            if match:
                device, ip = match.groups()
                if "MPC0" not in device:  # Exclude devices with 'MPC0'
                    ip_addresses[device] = ip
        return ip_addresses
    except subprocess.CalledProcessError as e:
        print(f"Error executing 'vmm ip': {e}")
        return {}

def check_vmm_ping(ip_addresses):
    """Perform 'vmm ping' and check if the devices are alive."""
    try:
        result = subprocess.run(["vmm", "ping"], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split("\n")
        alive_devices = {}
        for line in lines:
            match = re.match(r"(\S+)\s+(\d+\.\d+\.\d+\.\d+)\s+alive", line)
            if match:
                device, ip = match.groups()
                if device in ip_addresses:  # Ensure the device is in the initial list
                    alive_devices[device] = ip
        return alive_devices
    except subprocess.CalledProcessError as e:
        print(f"Error executing 'vmm ping': {e}")
        return {}

def backup_configuration(alive_devices):
    """SSH into each alive device and capture the configuration."""
    all_configurations = {}
    for device, ip in alive_devices.items():
        print(f"\nConnecting to {device} ({ip})...")
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=ip, username=username, password=password, timeout=10)

            shell = ssh.invoke_shell()
            shell.settimeout(60)

            shell.send("cli\n")
            time.sleep(1)
            cli_output = shell.recv(8192).decode('utf-8', errors='ignore')

            if not (">" in cli_output or "%" in cli_output or "root@" in cli_output):
                print(f"Error: Failed to enter CLI mode on {device}")
                continue

            shell.send("show configuration | display set | no-more\n")
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

            ssh.close()

        except paramiko.ssh_exception.SSHException as e:
            print(f"SSH error for {device}: {str(e)}")
        except Exception as e:
            print(f"Failed to connect to {device}: {str(e)}")
    return all_configurations

def save_configurations_to_file(configurations):
    """Save the configurations to a text file with a timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"configuration_backup_{timestamp}.txt"
    with open(filename, 'w') as file:
        for device, config in configurations.items():
            file.write(f"\nDevice: {device}\n{'=' * 40}\n{config}\n")
    print(f"\nConfigurations successfully saved to {filename}")

if __name__ == "__main__":
    ip_addresses = get_vmm_ip_addresses()
    if not ip_addresses:
        print("No IP addresses found.")
        exit(1)

    alive_devices = check_vmm_ping(ip_addresses)
    if not alive_devices:
        print("No alive devices found.")
        exit(1)

    configurations = backup_configuration(alive_devices)

    if configurations:
        save_configurations_to_file(configurations)
    else:
        print("No configurations were captured.")

