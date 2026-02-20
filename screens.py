from helpers import (
    time,
    set_last_checked,
    get_last_checked,
    format_time_ago,
    add_entry,
    read_entries,
    edit_entry,
    delete_entry,
    read_config,
    write_config,
)
from templates import TITLE_LABEL
import os
import re
import signal
import subprocess
import threading

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import Button, Checkbox, Footer, Header, Input, Link, Static
from textual.screen import ModalScreen, Screen

class MainScreen(Screen):
    def compose(self) -> ComposeResult:
        last_checked = get_last_checked()

        yield Header(show_clock=True)
        yield Footer()
        
        with Container(id="main-content"):
            with Container(id="content-grid"):
                yield Container(
                    Static(TITLE_LABEL, id="title-label"),
                    id="title-panel",
                )
                yield Container(
                    Static("Recent updates\n\n- New packs detected\n- Queue is healthy"),
                    id="left-panel",
                )
                yield Container(
                    Static(
                        f"Status\n\nLast checked:\n{time.ctime(last_checked)} ({format_time_ago(last_checked)})"
                    ),
                    id="right-panel",
                )


class ProcessEntriesScreen(Screen):
    def __init__(self) -> None:
        super().__init__()
        self._worker: threading.Thread | None = None
        self._stop_requested = False
        self._current_process: subprocess.Popen[str] | None = None
        self._is_running = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()

        with Container(id="main-content"):
            with Container(id="add-content-grid"):
                yield Container(
                    Static(TITLE_LABEL, id="title-label"),
                    id="title-panel",
                )
                yield Container(
                    Static("Ready. Press Start to process entries.", id="process-current"),
                    Horizontal(
                        Button("Start", id="process-start-button", flat=True),
                        Button("Stop", id="process-stop-button", flat=True, disabled=True),
                        Button("Reset", id="process-reset-button", flat=True),
                        id="process-controls",
                    ),
                    VerticalScroll(
                        Static("", id="process-live-log"),
                        id="process-log-scroll",
                    ),
                    Static("", id="process-summary"),
                    id="process-entries-panel",
                )

    def on_mount(self) -> None:
        self._set_controls(running=False)

    def _set_current(self, text: str) -> None:
        self.query_one("#process-current", Static).update(text)

    def _set_summary(self, text: str) -> None:
        self.query_one("#process-summary", Static).update(text)

    def _set_log(self, text: str) -> None:
        self.query_one("#process-live-log", Static).update(text)

    def _set_controls(self, running: bool) -> None:
        self.query_one("#process-start-button", Button).disabled = running
        self.query_one("#process-stop-button", Button).disabled = not running
        self.query_one("#process-reset-button", Button).disabled = running

    def _lftp_quote(self, value: str) -> str:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    def _extract_file_progress(self, line: str) -> str | None:
        transfer_match = re.search(r"Transferring file [`'](.+?)[`']", line)
        if transfer_match:
            return transfer_match.group(1)

        get_match = re.search(r"\bget\s+(.+)$", line)
        if get_match:
            return get_match.group(1).strip()

        return None

    def _extract_percentage(self, line: str) -> int | None:
        matches = re.findall(r"(\d{1,3})%", line)
        if not matches:
            return None

        try:
            percent = int(matches[-1])
        except ValueError:
            return None

        if 0 <= percent <= 100:
            return percent
        return None

    def _terminate_current_process(self) -> None:
        process = self._current_process
        if process is None or process.poll() is not None:
            return

        try:
            os.killpg(process.pid, signal.SIGTERM)
        except Exception:
            try:
                process.terminate()
            except Exception:
                return

    def _process_entries(self) -> None:
        self._is_running = True
        self.app.call_from_thread(self._set_controls, True)

        config = read_config()
        url = str(config.get("url", "")).strip()
        username = str(config.get("username", "")).strip()
        password = str(config.get("password", "")).strip()
        destination_path = str(config.get("destination_path", "")).strip()

        if not url or not username or not password or not destination_path:
            self.app.call_from_thread(
                self._set_current,
                "Missing config values. Set URL, username, password and destination path first.",
            )
            self._is_running = False
            self.app.call_from_thread(self._set_controls, False)
            return

        entries = read_entries()
        if not entries:
            self.app.call_from_thread(self._set_current, "No entries found to process.")
            self.app.call_from_thread(self._set_summary, "Nothing processed.")
            self._is_running = False
            self.app.call_from_thread(self._set_controls, False)
            return

        started_at = int(time.time())
        log_lines: list[str] = [
            f"Process started: {time.ctime(started_at)}",
            f"Debug: worker thread started at {started_at}",
            f"FTP server: {url}",
            f"Destination base: {destination_path}",
            f"Debug: loaded {len(entries)} entries",
            "",
            "Entries:",
        ]

        processed_count = 0
        success_count = 0
        failed_count = 0
        skipped_count = 0

        for index, entry in enumerate(entries, start=1):
            if self._stop_requested:
                log_lines.append("Processing stopped by user.")
                break

            label = str(entry.get("label", "")).strip() or f"Entry {index}"
            source_path = str(entry.get("path", "")).strip()
            skip = bool(entry.get("skip", False))

            if not source_path:
                failed_count += 1
                log_lines.append(
                    f"[{index}] FAILED | {label} | source: <missing> | destination: {destination_path}"
                )
                continue

            if skip:
                skipped_count += 1
                log_lines.append(
                    f"[{index}] SKIPPED | {label} | source: {source_path} | destination: {destination_path}"
                )
                self.app.call_from_thread(
                    self._set_current,
                    f"Skipping {index}/{len(entries)}: {label}",
                )
                self.app.call_from_thread(self._set_log, "\n".join(log_lines))
                continue

            processed_count += 1

            self.app.call_from_thread(
                self._set_current,
                f"Processing {index}/{len(entries)}: {label} ({source_path})",
            )

            command = [
                "lftp",
                "-u",
                f"{username},{password}",
                url,
                "-e",
                (
                    f"mirror --verbose=3 {self._lftp_quote(source_path)} "
                    f"{self._lftp_quote(destination_path)}; bye"
                ),
            ]
            log_lines.append(f"Debug: command[{index}] = {' '.join(command)}")

            try:
                self._current_process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    preexec_fn=os.setsid,
                )
                log_lines.append(f"Debug: started lftp pid={self._current_process.pid}")

                current_file = source_path
                last_percent: int | None = None
                self.app.call_from_thread(
                    self._set_current,
                    f"Processing {index}/{len(entries)}: {label} | file: {current_file}",
                )

                if self._current_process.stdout is not None:
                    for output_line in self._current_process.stdout:
                        if self._stop_requested:
                            self._terminate_current_process()
                            log_lines.append("    stop requested: terminating active transfer")
                            break

                        stripped = output_line.strip()
                        if not stripped:
                            continue

                        log_lines.append(f"    lftp: {stripped}")

                        file_progress = self._extract_file_progress(stripped)
                        if file_progress:
                            current_file = file_progress
                            last_percent = None
                            self.app.call_from_thread(
                                self._set_current,
                                (
                                    f"Processing {index}/{len(entries)}: {label} | "
                                    f"file: {file_progress}"
                                ),
                            )

                        percent = self._extract_percentage(stripped)
                        if percent is not None and percent != last_percent:
                            last_percent = percent
                            self.app.call_from_thread(
                                self._set_current,
                                (
                                    f"Processing {index}/{len(entries)}: {label} | "
                                    f"file: {current_file} | {percent}%"
                                ),
                            )
                            log_lines.append(f"    progress: {current_file} | {percent}%")

                        self.app.call_from_thread(self._set_log, "\n".join(log_lines))

                try:
                    return_code = self._current_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    log_lines.append("Debug: wait timeout, force-killing process group")
                    self._terminate_current_process()
                    try:
                        os.killpg(self._current_process.pid, signal.SIGKILL)
                    except Exception:
                        pass
                    return_code = self._current_process.wait(timeout=5)

                self._current_process = None
                log_lines.append(f"Debug: lftp exit code={return_code}")

                if self._stop_requested:
                    log_lines.append(
                        f"[{index}] STOPPED | {label} | source: {source_path} | destination: {destination_path}"
                    )
                    break

                if return_code == 0:
                    success_count += 1
                    self.app.call_from_thread(self._set_current, f"Finished {index}/{len(entries)}: {label}")
                    log_lines.append(
                        f"[{index}] OK | {label} | source: {source_path} | destination: {destination_path}"
                    )
                else:
                    failed_count += 1
                    log_lines.append(
                        f"[{index}] FAILED | {label} | source: {source_path} | destination: {destination_path}"
                    )
                    log_lines.append(f"    error: lftp exited with code {return_code}")
            except FileNotFoundError:
                failed_count += 1
                log_lines.append(
                    f"[{index}] FAILED | {label} | source: {source_path} | destination: {destination_path}"
                )
                log_lines.append("    error: lftp command not found")
                self.app.call_from_thread(
                    self._set_current,
                    "Failed: lftp is not installed or not available in PATH.",
                )
                self.app.call_from_thread(self._set_log, "\n".join(log_lines))
                self._current_process = None
                break

            self.app.call_from_thread(self._set_log, "\n".join(log_lines))

        finished_at = int(time.time())
        set_last_checked()
        log_lines.extend(
            [
                "",
                f"Process finished: {time.ctime(finished_at)}",
                f"Debug: worker finished at {finished_at}",
                (
                    "Summary: "
                    f"processed={processed_count}, success={success_count}, "
                    f"failed={failed_count}, skipped={skipped_count}"
                ),
            ]
        )

        log_path = f"data/logs/{finished_at}.txt"
        with open(log_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(log_lines) + "\n")

        if self._stop_requested:
            current_text = "Processing stopped."
        else:
            current_text = "Processing complete."

        self.app.call_from_thread(self._set_log, "\n".join(log_lines))
        self.app.call_from_thread(
            self._set_current,
            current_text,
        )
        self.app.call_from_thread(
            self._set_summary,
            (
                f"Done. Success: {success_count}, Failed: {failed_count}, "
                f"Skipped: {skipped_count}. Log: {log_path}"
            ),
        )
        self._is_running = False
        self.app.call_from_thread(self._set_controls, False)
        self._stop_requested = False

    def _start_processing(self) -> None:
        if self._is_running:
            self._set_summary("Already processing entries.")
            return

        self._stop_requested = False
        self._set_summary("")
        self._worker = threading.Thread(target=self._process_entries, daemon=True)
        self._worker.start()

    def _stop_processing(self) -> None:
        if not self._is_running:
            self._set_summary("No active processing to stop.")
            return

        self._stop_requested = True
        self._set_summary("Stopping after current operation...")
        self._terminate_current_process()

    def _reset_processing(self) -> None:
        if self._is_running:
            self._set_summary("Stop processing before reset.")
            return

        self._set_current("Ready. Press Start to process entries.")
        self._set_log("")
        self._set_summary("")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "process-start-button":
            self._start_processing()
        elif event.button.id == "process-stop-button":
            self._stop_processing()
        elif event.button.id == "process-reset-button":
            self._reset_processing()

class EditConfigScreen(Screen):
    def compose(self) -> ComposeResult:
        config = read_config()

        yield Header(show_clock=True)
        yield Footer()
        
        with Container(id="main-content"):
            with Container(id="add-content-grid"):
                yield Container(
                    Static(TITLE_LABEL, id="title-label"),
                    id="title-panel",
                )
                yield Container(
                    Input(
                        placeholder="FTP URL",
                        value=config.get("url", ""),
                        id="config-url-input",
                    ),
                    Input(
                        placeholder="FTP Username",
                        value=config.get("username", ""),
                        id="config-username-input",
                    ),
                    Input(
                        placeholder="FTP Password",
                        value=config.get("password", ""),
                        password=True,
                        id="config-password-input",
                    ),
                    Input(
                        placeholder="Destination Path",
                        value=config.get("destination_path", ""),
                        id="config-destination-input",
                    ),
                    Button("Save Config", id="save-config-button", flat=True),
                    Static("", id="config-status"),
                    id="add-entry-panel",
                )

    def _set_status(self, message: str, success: bool) -> None:
        status = self.query_one("#config-status", Static)
        status.update(message)
        status.remove_class("success")
        status.remove_class("error")
        status.add_class("success" if success else "error")

    def _submit_form(self) -> None:
        url_input = self.query_one("#config-url-input", Input)
        username_input = self.query_one("#config-username-input", Input)
        password_input = self.query_one("#config-password-input", Input)
        destination_input = self.query_one("#config-destination-input", Input)
        
        url = url_input.value.strip()
        username = username_input.value.strip()
        password = password_input.value.strip()
        destination_path = destination_input.value.strip()

        if not url or not username or not password or not destination_path:
            self._set_status("All fields are required.", success=False)
            return

        write_config(
            {
                "url": url,
                "username": username,
                "password": password,
                "destination_path": destination_path,
            }
        )
        self._set_status("Config saved successfully.", success=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-config-button":
            self._submit_form()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id in {
            "config-url-input",
            "config-username-input",
            "config-password-input",
            "config-destination-input",
        }:
            self._submit_form()

class AddEntryScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()
        
        with Container(id="main-content"):
            with Container(id="add-content-grid"):
                yield Container(
                    Static(TITLE_LABEL, id="title-label"),
                    id="title-panel",
                )
                yield Container(
                    Input(placeholder="Label", id="label-input"),
                    Input(placeholder="Path", id="path-input"),
                    Input(placeholder="URL (optional)", id="url-input"),
                    Button("Add to Queue", id="add-button", flat=True),
                    Static("", id="add-entry-status"),
                    id="add-entry-panel",
                )

    def _set_status(self, message: str, success: bool) -> None:
        status = self.query_one("#add-entry-status", Static)
        status.update(message)
        status.remove_class("success")
        status.remove_class("error")
        status.add_class("success" if success else "error")

    def _submit_form(self) -> None:
        label_input = self.query_one("#label-input", Input)
        path_input = self.query_one("#path-input", Input)
        url_input = self.query_one("#url-input", Input)

        label = label_input.value.strip()
        path = path_input.value.strip()
        url = url_input.value.strip()

        if not label or not path:
            self._set_status("Label and Path are required.", success=False)
            return

        add_entry(label=label, path=path, url=url)
        self._set_status(f"Added '{label}' to queue.", success=True)
        label_input.value = ""
        path_input.value = ""
        url_input.value = ""
        label_input.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-button":
            self._submit_form()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id in {"label-input", "path-input", "url-input"}:
            self._submit_form()


class ViewEntriesScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()

        with Container(id="main-content"):
            with Container(id="add-content-grid"):
                yield Container(
                    Static(TITLE_LABEL, id="title-label"),
                    id="title-panel",
                )
                yield Container(
                    VerticalScroll(id="entries-scroll"),
                    Button("Delete Selected", id="delete-selected-button", flat=True),
                    Static("", id="entries-status"),
                    id="view-entries-panel",
                )

    def _set_status(self, message: str, success: bool) -> None:
        status = self.query_one("#entries-status", Static)
        status.update(message)
        status.remove_class("success")
        status.remove_class("error")
        status.add_class("success" if success else "error")

    def _open_edit_modal(self, index: int) -> None:
        entries = read_entries()
        if index < 0 or index >= len(entries):
            self._set_status("Entry index is out of range.", success=False)
            return

        entry = entries[index]

        def _after_close(saved: bool | None) -> None:
            self._render_entries()
            if saved:
                self._set_status(f"Updated entry {index + 1}.", success=True)

        self.app.push_screen(EditEntryModal(index=index, entry=entry), _after_close)

    def _delete_entry(self, index: int) -> None:
        entries = read_entries()
        if index < 0 or index >= len(entries):
            self._set_status("Entry index is out of range.", success=False)
            return
        delete_entry(index)
        self._render_entries()
        self._set_status(f"Deleted entry {index + 1}.", success=True)

    def _delete_selected_entries(self) -> None:
        selected_indices = []
        for widget in self.query("#entries-scroll Checkbox"):
            if isinstance(widget, Checkbox) and widget.value and widget.id and widget.id.startswith("entry-check-"):
                selected_indices.append(int(widget.id.split("-")[-1]))

        if not selected_indices:
            self._set_status("No entries selected.", success=False)
            return

        def _after_close(confirmed: bool | None) -> None:
            if not confirmed:
                return

            for index in sorted(selected_indices, reverse=True):
                delete_entry(index)

            self._render_entries()
            self._set_status(
                f"Deleted {len(selected_indices)} selected entr{'y' if len(selected_indices) == 1 else 'ies'}.",
                success=True,
            )

        self.app.push_screen(
            ConfirmDeleteSelectedModal(selected_count=len(selected_indices)),
            _after_close,
        )

    def _render_entries(self) -> None:
        entries = read_entries()
        scroll = self.query_one("#entries-scroll", VerticalScroll)
        status = self.query_one("#entries-status", Static)

        scroll.remove_children()

        if not entries:
            scroll.mount(Static("No queue entries found."))
            status.update("Press Ctrl+N to add your first entry.")
            return

        for index, entry in enumerate(entries):
            label = str(entry.get("label", ""))
            path = str(entry.get("path", ""))
            url = str(entry.get("url", ""))
            skip = bool(entry.get("skip", False))

            if url:
                label_path_widget = Horizontal(
                    Link(label, url=url),
                    Static(f" ({path})", classes="entry-path"),
                    classes="entry-label-wrap",
                )
            else:
                label_path_widget = Static(
                    f"{label} ({path})",
                    classes="entry-label-wrap entry-path",
                )

            row = Horizontal(
                Checkbox("Select", id=f"entry-check-{index}", classes="entry-select-checkbox"),
                label_path_widget,
                Checkbox("Skip", value=skip, id=f"entry-skip-{index}", classes="entry-skip-checkbox"),
                Button("Edit", id=f"entry-edit-{index}", flat=False),
                Button("Delete", id=f"entry-delete-{index}", flat=False),
                classes="entry-row",
            )
            scroll.mount(row)

        status.update(f"Loaded {len(entries)} entr{'y' if len(entries) == 1 else 'ies'}.")

    def on_mount(self) -> None:
        self._render_entries()

    def on_screen_resume(self) -> None:
        self._render_entries()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "delete-selected-button":
            self._delete_selected_entries()
        elif button_id and button_id.startswith("entry-edit-"):
            index = int(button_id.split("-")[-1])
            self._open_edit_modal(index)
        elif button_id and button_id.startswith("entry-delete-"):
            index = int(button_id.split("-")[-1])
            self._delete_entry(index)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        checkbox_id = event.checkbox.id
        if not checkbox_id or not checkbox_id.startswith("entry-skip-"):
            return

        index = int(checkbox_id.split("-")[-1])
        entries = read_entries()
        if index < 0 or index >= len(entries):
            self._set_status("Entry index is out of range.", success=False)
            return

        entry = entries[index]
        edit_entry(
            index=index,
            label=str(entry.get("label", "")),
            path=str(entry.get("path", "")),
            skip=bool(event.value),
            url=str(entry.get("url", "")),
        )
        self._set_status(
            f"Entry {index + 1} skip set to {'on' if event.value else 'off'}.",
            success=True,
        )


class EditEntryModal(ModalScreen[bool]):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, index: int, entry: dict) -> None:
        super().__init__()
        self.index = index
        self.entry = entry

    def compose(self) -> ComposeResult:
        with Container(id="edit-entry-modal"):
            yield Static(f"Edit Entry #{self.index + 1}")
            yield Input(
                placeholder="Label",
                value=str(self.entry.get("label", "")),
                id="modal-label-input",
            )
            yield Input(
                placeholder="Path",
                value=str(self.entry.get("path", "")),
                id="modal-path-input",
            )
            yield Input(
                placeholder="URL (optional)",
                value=str(self.entry.get("url", "")),
                id="modal-url-input",
            )
            with Horizontal(id="edit-entry-actions"):
                yield Button("Save", id="modal-save-button", flat=False)
                yield Button("Cancel", id="modal-cancel-button", flat=False)
            yield Static("", id="edit-entry-status")

    def _set_status(self, message: str, success: bool) -> None:
        status = self.query_one("#edit-entry-status", Static)
        status.update(message)
        status.remove_class("success")
        status.remove_class("error")
        status.add_class("success" if success else "error")

    def _save(self) -> None:
        label = self.query_one("#modal-label-input", Input).value.strip()
        path = self.query_one("#modal-path-input", Input).value.strip()
        url = self.query_one("#modal-url-input", Input).value.strip()

        if not label or not path:
            self._set_status("Label and Path are required.", success=False)
            return

        edit_entry(
            index=self.index,
            label=label,
            path=path,
            skip=bool(self.entry.get("skip", False)),
            url=url,
        )
        self.dismiss(True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "modal-save-button":
            self._save()
        elif event.button.id == "modal-cancel-button":
            self.dismiss(False)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id in {"modal-label-input", "modal-path-input", "modal-url-input"}:
            self._save()

    def key_escape(self) -> None:
        self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)


class ConfirmDeleteSelectedModal(ModalScreen[bool]):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, selected_count: int) -> None:
        super().__init__()
        self.selected_count = selected_count

    def compose(self) -> ComposeResult:
        with Container(id="confirm-delete-modal"):
            yield Static(
                f"Delete {self.selected_count} selected entr{'y' if self.selected_count == 1 else 'ies'}?"
            )
            with Horizontal(id="confirm-delete-actions"):
                yield Button("Delete", id="confirm-delete-button", flat=True)
                yield Button("Cancel", id="confirm-cancel-button", flat=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-delete-button":
            self.dismiss(True)
        elif event.button.id == "confirm-cancel-button":
            self.dismiss(False)

    def key_escape(self) -> None:
        self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)