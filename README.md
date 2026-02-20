# AO-CLI

Terminal UI for managing and processing AnimeOut FTP mirror entries.

AO-CLI lets you:
- configure FTP credentials and local destination,
- build a queue of source paths,
- edit/delete/skip entries,
- process entries through `lftp mirror`,
- view live transfer output with per-entry progress,
- save run logs for later review.

## Requirements

- Python **3.10+**
- `lftp` available in `PATH`

## Installation

1. Clone this repository.
2. Create and activate a virtual environment (recommended).
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Ensure `lftp` is installed:

```bash
lftp --version
```

## Run

```bash
python main.py
```

On first run, AO-CLI creates:
- `data/`
- `data/logs/`

## Keyboard Shortcuts

- `Ctrl+S` → Main screen
- `Ctrl+D` → Process entries
- `Ctrl+N` → Add entry
- `Ctrl+B` → View entries
- `Ctrl+O` → Edit config
- `Ctrl+G` → Open project GitHub page

## Data Files

- `data/config.json` → FTP + destination configuration
- `data/entries.json` → queue entries (JSON list)
- `data/last_checked.txt` → timestamp of last processing run
- `data/logs/<timestamp>.txt` → processing output logs

## Notes

- Paths with spaces are supported.
- Skip-enabled entries are logged as skipped and not mirrored.
- If `lftp` is missing, processing will fail with a clear error in the UI/log.

## Troubleshooting

- **`lftp command not found`**
	- Install `lftp` using your package manager and verify with `lftp --version`.

- **FTP mirror fails with directory errors**
	- Re-check the entry source path in **View Entries**.
	- Confirm your FTP user has permission to access that remote directory.

- **No entries processed**
	- Ensure entries exist in `data/entries.json` and are not marked `skip: true`.

## License

Licensed under the Teaware License. See [LICENSE](LICENSE) for more information.