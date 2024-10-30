import json
import paramiko
from prettytable import PrettyTable
import os
import glob

with open(os.path.expanduser('~/.config/docklist/conf.json'), 'r') as config_file:
    config = json.load(config_file)

ssh_config_path = os.getenv('SSH_CONFIG_PATH', os.path.expanduser("~/.ssh/config"))

ssh_config = paramiko.SSHConfig()
with open(ssh_config_path) as f:
    ssh_config.parse(f)

hosts = config["hosts"]
ssh_key_path = config["ssh_key_path"]

command = "docker ps --format '{{json .}}'"

table = PrettyTable()

fields_to_display = config["fields"]

table.field_names = [field.capitalize() for field, display in fields_to_display.items() if display]

def extract_fields(container, fields, host_name):
    extracted = []
    if fields.get("host"):
        extracted.append(host_name)
    if fields.get("container_name"):
        extracted.append(container.get('Names', 'N/A'))
    if fields.get("ports"):
        extracted.append(container.get('Ports', 'N/A'))
    if fields.get("compose_path"):
        extracted.append(container.get('ComposePath', 'N/A'))
    if fields.get("network"):
        extracted.append(container.get('Network', 'N/A'))
    if fields.get("status"):
        extracted.append(container.get('Status', 'N/A'))
    if fields.get("uptime"):
        extracted.append(container.get('Uptime', 'N/A'))
    return extracted

def parse_docker_output(output):
    containers = []
    for line in output:
        try:
            container = json.loads(line.strip())
            containers.append(container)
        except json.JSONDecodeError:
            print(f"Error decoding JSON: {line}")
    return containers

all_containers = []

for host in hosts:
    try:
        host_config = ssh_config.lookup(host)
        hostname = host_config.get('hostname', host)
        user = host_config.get('user', None)
        key_filename = host_config.get('identityfile', [ssh_key_path])[0]

        print(f"Attempting to connect to host: {host}")
        print(f"Resolved hostname: {hostname}")
        print(f"Using user: {user}")
        print(f"Using key file: {key_filename}")

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if user:
            if key_filename:
                print("Connecting with user and key file...")
                ssh.connect(hostname, username=user, key_filename=key_filename)
            else:
                print("Connecting with user only...")
                ssh.connect(hostname, username=user)
        else:
            if key_filename:
                print("Connecting with key file only...")
                ssh.connect(hostname, key_filename=key_filename)
            else:
                print("Connecting with default settings...")
                ssh.connect(hostname)

        command_to_execute = command if user == 'root' else f"sudo {command}"

        stdin, stdout, stderr = ssh.exec_command(command_to_execute)
        output = stdout.readlines()
        containers = parse_docker_output(output)
        all_containers.extend(containers)
        for container in containers:
            table.add_row(extract_fields(container, fields_to_display, host))
        ssh.close()
    except Exception as e:
        print(f"Error connecting to {host}: {e}")

with open(os.path.expanduser('~/.config/docklist/docker_containers.json'), 'w') as json_file:
    json.dump(all_containers, json_file, indent=4)

print(table)

host_config = ssh_config.lookup('ai')
print(f"Resolved hostname for 'ai': {host_config.get('hostname', 'Not found')}")