import os
import shutil
import json
import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path

MODS_DIR = "Mods"
CONFIG_FILE = "config.json"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

app = ctk.CTk()
app.geometry("256x256")
app.title("Mad Manager")
openstack_icon = app.iconbitmap('icon.ico')

class MadManager(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Mad Manager")
        self.geometry("500x550")
        self.resizable(False, False)

        self.mods = {}
        self.mod_vars = {}
        self.game_path = ""

        self.load_config()

        # Container cinza claro
        self.outer_frame = ctk.CTkFrame(self, fg_color="#3a3a3a")
        self.outer_frame.pack(padx=10, pady=(10, 5), fill="both", expand=True)

        # Container escuro interno
        self.mods_frame = ctk.CTkFrame(self.outer_frame, fg_color="#2b2b2b", corner_radius=10)
        self.mods_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Botões
        self.button_frame = ctk.CTkFrame(self, fg_color="#3a3a3a")
        self.button_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.select_button = ctk.CTkButton(
            self.button_frame,
            text="Select Game Folder",
            command=self.select_game_folder,
            fg_color="#333333",
            hover_color="#444444",
            text_color="white",
            border_color="gray",
            border_width=1
        )
        self.select_button.pack(pady=(10, 5), padx=10)

        self.save_button = ctk.CTkButton(
            self.button_frame,
            text="Save",
            command=self.save_mods,
            fg_color="#333333",
            hover_color="#444444",
            text_color="white",
            border_color="gray",
            border_width=1
        )
        self.save_button.pack(pady=(0, 10), padx=10)

        self.refresh_mods()

    def select_game_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.game_path = folder
            self.save_config()

    def refresh_mods(self):
        for widget in self.mods_frame.winfo_children():
            widget.destroy()

        self.mods.clear()
        self.mod_vars.clear()

        mods_path = Path(MODS_DIR)
        if not mods_path.exists():
            mods_path.mkdir()

        for mod_dir in mods_path.iterdir():
            dropzone_path = mod_dir / "dropzone"
            if dropzone_path.is_dir():
                var = ctk.BooleanVar(value=self.mods.get(mod_dir.name, False))
                cb = ctk.CTkCheckBox(self.mods_frame, text=mod_dir.name, variable=var, text_color="white")
                cb.pack(anchor="w", padx=10, pady=5)
                self.mod_vars[mod_dir.name] = var

    def save_mods(self):
        for mod_name, var in self.mod_vars.items():
            enabled = var.get()
            self.mods[mod_name] = enabled
            mod_dropzone = Path(MODS_DIR) / mod_name / "dropzone"

            if enabled:
                self.enable_mod(mod_name, mod_dropzone)
            else:
                self.disable_mod(mod_name)

        self.save_config()

    def enable_mod(self, mod_name, source_dropzone):
        if not self.game_path:
            return

        game_dropzone = Path(self.game_path) / "dropzone"
        game_dropzone.mkdir(exist_ok=True)

        manifest = []

        for root, dirs, files in os.walk(source_dropzone):
            rel_path = Path(root).relative_to(source_dropzone)
            dest_dir = game_dropzone / rel_path
            dest_dir.mkdir(parents=True, exist_ok=True)

            for file in files:
                src_file = Path(root) / file
                dst_file = dest_dir / file
                shutil.copy2(src_file, dst_file)
                manifest.append(str(dst_file.relative_to(game_dropzone)))

        manifest_path = Path(MODS_DIR) / mod_name / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=4)

    def disable_mod(self, mod_name):
        if not self.game_path:
            return

        game_dropzone = Path(self.game_path) / "dropzone"
        manifest_path = Path(MODS_DIR) / mod_name / "manifest.json"

        if manifest_path.exists():
            with open(manifest_path, "r") as f:
                files = json.load(f)

            for relative_file in files:
                file_path = game_dropzone / relative_file
                if file_path.exists():
                    file_path.unlink()

            # Cleanup empty directories
            for relative_file in files:
                dir_path = (game_dropzone / relative_file).parent
                while dir_path != game_dropzone and dir_path.exists():
                    try:
                        dir_path.rmdir()
                    except OSError:
                        break
                    dir_path = dir_path.parent

            manifest_path.unlink()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                self.mods = data.get("mods", {})
                self.game_path = data.get("game_path", "")

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump({
                "mods": self.mods,
                "game_path": self.game_path
            }, f, indent=4)


if __name__ == "__main__":
    app = MadManager()
    app.mainloop()