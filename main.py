import webbrowser

from screens import MainScreen, AddEntryScreen, EditConfigScreen, ViewEntriesScreen, ProcessEntriesScreen
from helpers import create_data_directory, create_logs_directory

from textual.app import App

class AnimeOutCLI(App):
    TITLE = "AnimeOut FTP CLI"
    CSS_PATH = "styles.tcss"
    BINDINGS = [
        ("ctrl+s", "switch_mode('main')", "Main Screen"),
        ("ctrl+d", "switch_mode('process_entries')", "Process Entries"),
        ("ctrl+n", "switch_mode('add_entry')", "Add Entry"),
        ("ctrl+b", "switch_mode('view_entries')", "View Entries"),
        ("ctrl+o", "switch_mode('edit_config')", "Edit Config"),
        ("ctrl+g", "open_git", "Open GitHub"),
    ]
    MODES = {
        "main": MainScreen,
        "add_entry": AddEntryScreen,
        "view_entries": ViewEntriesScreen,
        "edit_config": EditConfigScreen,
        "process_entries": ProcessEntriesScreen,
    }
    
    def on_mount(self) -> None:
        self.switch_mode("main")

    def action_open_git(self) -> None:
        webbrowser.open(
            "https://github.com/s-vhs/AnimeOut-CommunityTools/tree/ao-cli",
            new=2,
            autoraise=True,
        )


if __name__ == "__main__":
    create_data_directory()
    create_logs_directory()
    AnimeOutCLI().run()