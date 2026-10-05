import socket

import paramiko


SSH_PORT = 2510
SSH_USERNAME = "root"
SSH_KEY_PATH = r"C:\SSH\kevin-roper"

def run_ssh_command(host, port, username, key_file, passphrase, command):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=host,
            port=port,
            username=username,
            key_filename=key_file,
            passphrase=passphrase,
            timeout=25,
            look_for_keys=False,
            allow_agent=False,
        )

        stdin, stdout, stderr = client.exec_command(command, timeout=30)

        output = stdout.read().decode(errors="ignore").strip()
        error = stderr.read().decode(errors="ignore").strip()

        return output if output else error

    except (socket.timeout, TimeoutError, paramiko.ssh_exception.NoValidConnectionsError):
        return "CONNECTION_TIMEOUT"

    except Exception as e:
        return f"SSH_ERROR: {e}"

    finally:
        client.close()
        