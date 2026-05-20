# cronclear

> Utility to audit and visualize crontab schedules across multiple remote hosts via SSH.

---

## Installation

```bash
pip install cronclear
```

Or install from source:

```bash
git clone https://github.com/youruser/cronclear.git && cd cronclear && pip install .
```

---

## Usage

Define your hosts in a config file or pass them directly via the CLI:

```bash
# Audit crontabs on multiple hosts
cronclear audit --hosts web01,web02,db01 --user deploy

# Output a visual schedule table
cronclear visualize --hosts web01,web02 --user deploy --format table

# Export results to JSON
cronclear audit --hosts web01 --user deploy --output report.json
```

Example output:

```
Host     User    Schedule        Command
-------- ------- --------------- ----------------------------
web01    root    0 2 * * *       /usr/bin/backup.sh
web01    deploy  */15 * * * *    /opt/app/healthcheck.sh
web02    root    0 4 * * 0       /usr/bin/weekly-cleanup.sh
```

**Options:**

| Flag | Description |
|------|-------------|
| `--hosts` | Comma-separated list of remote hostnames |
| `--user` | SSH user for remote connections |
| `--format` | Output format: `table`, `json`, or `csv` |
| `--output` | Write results to a file |
| `--key` | Path to SSH private key (default: `~/.ssh/id_rsa`) |

---

## Requirements

- Python 3.8+
- SSH access to target hosts
- `paramiko` (installed automatically)

---

## License

This project is licensed under the [MIT License](LICENSE).