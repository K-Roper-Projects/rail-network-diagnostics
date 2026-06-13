import paramiko
from getpass import getpass


host = input("CCU IP address: ")
port = int(input("SSH port [2510]: ") or "2510")
username = input("Username [root]: ") or "root"
key_file = input("OpenSSH private key path: ")
passphrase = getpass("SSH key passphrase: ")

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

client.connect(
    hostname=host,
    port=port,
    username=username,
    key_filename=key_file,
    passphrase=passphrase,
    timeout=10,
    look_for_keys=False,
    allow_agent=False,
)

stdin, stdout, stderr = client.exec_command("cat /var/local/gprmc")

print("Output:")
print(stdout.read().decode().strip())

error = stderr.read().decode().strip()
if error:
    print("Error:")
    print(error)

client.close()