**Overview**

This Python script automates the process of backing up configurations from network devices. It performs the following tasks: Retrieves IP addresses of devices using the vmm ip command. Check the availability of these devices using the vmm ping command. Connects to alive devices via SSH and captures their configurations. Saves the configurations to a timestamped file for record-keeping.

**Prerequisites**

Python 3.x installed on your system.

Required Python libraries:

  subprocess
  paramiko
  re
  time
  datetime

SSH access to the devices with valid credentials.

vmm command-line tool installed and accessible in your environment.

**Script Functionality**

1. get_vmm_ip_addresses()

This function executes the vmm ip command to retrieve a list of devices and their IP addresses. It filters out devices containing MPC0 as these are not required for configuration backups.

2. check_vmm_ping(ip_addresses)

This function performs a ping test using the vmm ping command to identify which devices are alive and reachable. Only devices that pass this test are considered for configuration backup.

3. backup_configuration(alive_devices)

This function:

Establishes an SSH connection to each alive device using the paramiko library.

Sends commands to enter CLI mode and capture the configuration.

Retrieves the configuration using the show configuration | display set | no-more command.

Handles errors like SSH connection failures gracefully.

4. save_configurations_to_file(configurations)

This function saves the captured configurations into a text file named with the current timestamp, ensuring each backup is unique.

**How to Use the Script**

Steps

Clone or Download the Repository

git clone https://github.com/kbedford/VMM-Config-Backup.git

  Install Dependencies
  Ensure the paramiko library is installed:

  pip install paramiko

**Update Credentials**

Open the script and update the following variables with your device's SSH credentials:

    Run the Script
    Execute the script using:
    python3 configuration_backup.py

**Verify Output**

Check the terminal for logs detailing which devices were processed.

Locate the generated file in the current directory with a name like configuration_backup_YYYY-MM-DD_HH-MM-SS.txt
