import sys
import os
import json
import shutil
import tkinter as tk
import customtkinter as ctk
from pathlib import Path
from tkinter import filedialog, messagebox

# --------------- 
# Configuration
# ---------------

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent

MODS_DIR = BASE_DIR / "Mods"
CONFIG_FILE = BASE_DIR / "config.json"

WINDOW_SIZE = "560x640"
MIN_WINDOW_SIZE = (520, 560)

BTN_FG = "#2b2b2b"
BTN_BORDER_COLOR = "white"
BTN_BORDER_WIDTH = 1

TRANSPARENT_COLOR = "#010101"


# ========================
# ConfigManager
# ========================

class ConfigManager:
    def __init__(self, config_path: Path):
        self.path = config_path
        self.data = {"game_path": "", "mods": {}}
        self.load()

    def load(self):
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                try:
                    shutil.copy2(self.path, self.path.with_suffix(".bak"))
                except Exception:
                    pass
                self.data = {"game_path": "", "mods": {}}
                self.save()

    def save(self):
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            os.replace(str(tmp), str(self.path))
        except Exception:
            try:
                with open(self.path, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=4, ensure_ascii=False)
            except Exception:
                pass

    @property
    def game_path(self) -> str:
        return self.data.get("game_path", "")

    @game_path.setter
    def game_path(self, value: str):
        self.data["game_path"] = value

    def get_mod_state(self, mod_name: str) -> bool:
        return bool(self.data.get("mods", {}).get(mod_name, False))

    def set_mod_state(self, mod_name: str, enabled: bool):
        self.data.setdefault("mods", {})[mod_name] = bool(enabled)


# ========================
# ModManager
# ========================

class ModManager:
    def __init__(self, mods_dir: Path):
        self.mods_dir = mods_dir
        self.mods_dir.mkdir(exist_ok=True, parents=True)

    def list_mods(self):
        mods = []
        for entry in self.mods_dir.iterdir():
            if entry.is_dir() and (entry / "dropzone").is_dir():
                mods.append(entry.name)
        return sorted(mods, key=str.casefold)

    def _manifest_path(self, mod_name: str) -> Path:
        return self.mods_dir / mod_name / "manifest.json"

    @staticmethod
    def _same_file(src: Path, dst: Path) -> bool:
        try:
            return dst.exists() and (dst.stat().st_size == src.stat().st_size) and (int(dst.stat().st_mtime) == int(src.stat().st_mtime))
        except Exception:
            return False

    def enable_mod(self, mod_name: str, game_path: Path):
        src_dropzone = self.mods_dir / mod_name / "dropzone"
        dst_dropzone = game_path / "dropzone"
        dst_dropzone.mkdir(exist_ok=True, parents=True)

        files_written = []
        for root, _dirs, files in os.walk(src_dropzone):
            rel = Path(root).relative_to(src_dropzone)
            dest_dir = dst_dropzone / rel
            dest_dir.mkdir(parents=True, exist_ok=True)
            for file in files:
                src_file = Path(root) / file
                dst_file = dest_dir / file
                try:
                    if self._same_file(src_file, dst_file):
                        files_written.append(str(dst_file.relative_to(dst_dropzone)))
                        continue
                    shutil.copy2(src_file, dst_file)
                    files_written.append(str(dst_file.relative_to(dst_dropzone)))
                except Exception:
                    pass

        manifest = self._manifest_path(mod_name)
        try:
            with open(manifest, "w", encoding="utf-8") as f:
                json.dump(files_written, f, indent=4)
        except Exception:
            pass

    def disable_mod(self, mod_name: str, game_path: Path):
        dst_dropzone = game_path / "dropzone"
        manifest = self._manifest_path(mod_name)

        if not manifest.exists():
            return

        try:
            with open(manifest, "r", encoding="utf-8") as f:
                files = json.load(f)
        except Exception:
            return

        for relative in files:
            p = dst_dropzone / relative
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass

        for relative in files:
            dir_path = (dst_dropzone / relative).parent
            while dir_path != dst_dropzone and dir_path.exists():
                try:
                    dir_path.rmdir()
                except OSError:
                    break
                dir_path = dir_path.parent

        try:
            manifest.unlink(missing_ok=True)
        except Exception:
            pass


# ====================
# UI: Mod Item & Main
# ====================

class ModItem(ctk.CTkFrame):
    def __init__(self, master, name: str, initial_state: bool, index: int,
                 on_click_callback=None):
        super().__init__(master, fg_color="transparent")
        self.name = name
        self.index = index
        self.on_click_callback = on_click_callback

        self.columnconfigure(1, weight=1)

        self.switch_var = tk.BooleanVar(value=initial_state)
        self.switch = ctk.CTkSwitch(
            self, text=name, font=("Segoe UI", 14), variable=self.switch_var,
            command=self._on_switch, width=240,
            fg_color="#333333", button_color="#ffffff", progress_color="#333333",
            border_color=BTN_BORDER_COLOR, border_width=BTN_BORDER_WIDTH
        )
        self.switch.grid(row=0, column=0, sticky="w", padx=(6, 6), pady=4)

        self.switch.bind("<Button-1>", self._on_click, add="+")

    def _on_switch(self):
        pass

    def _on_click(self, event):
        ctrl = (event.state & 0x0004) != 0
        shift = (event.state & 0x0001) != 0
        def post():
            current_value = self.switch_var.get()
            if self.on_click_callback:
                self.on_click_callback(self.index, current_value, ctrl=ctrl, shift=shift)
        self.after(1, post)


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Mad Manager")
        self.geometry(WINDOW_SIZE)
        self.minsize(*MIN_WINDOW_SIZE)

        try:
            self.configure(bg=TRANSPARENT_COLOR)
            self.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)
        except Exception:
            pass

        self.config = ConfigManager(CONFIG_FILE)
        self.mod_manager = ModManager(MODS_DIR)

        self.mods = []
        self.item_widgets = []
        self.last_clicked_index = None
        self.pending_states = {}

        self._build_ui()
        self.refresh_mod_list()

    # ---------- UI Building ----------

    def _build_ui(self):
        buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        buttons_frame.pack(anchor="center", pady=12)

        self.select_btn = ctk.CTkButton(
            buttons_frame,
            text="Select Game Folder", font=("Segoe UI", 14),
            command=self.select_game_folder,
            fg_color=BTN_FG,
            border_color=BTN_BORDER_COLOR,
            border_width=BTN_BORDER_WIDTH
        )
        self.select_btn.pack(side="left", padx=6)

        self.refresh_btn = ctk.CTkButton(
            buttons_frame,
            text="Refresh", font=("Segoe UI", 14),
            command=self.refresh,
            fg_color=BTN_FG,
            border_color=BTN_BORDER_COLOR,
            border_width=BTN_BORDER_WIDTH
        )
        self.refresh_btn.pack(side="left", padx=6)

        self.scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=BTN_FG,
            corner_radius=5,
            width=0,
            height=0
        )
        self.scroll.pack(fill="both", expand=True, padx=(12), pady=(6, 12))

    # ---------- UI Actions ----------

    def select_game_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.config.game_path = folder
            self.config.save()

    def refresh(self):
        self.config.load()
        self.refresh_mod_list()
        self.last_clicked_index = None

    def refresh_mod_list(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        self.item_widgets.clear()

        self.config.load()
        self.mods = self.mod_manager.list_mods()

        for idx, name in enumerate(self.mods):
            enabled = self.config.get_mod_state(name)
            self.pending_states[name] = enabled
            item = ModItem(
                self.scroll, name, enabled, idx,
                on_click_callback=self._on_item_click
            )
            item.pack(fill="x", padx=6, pady=2)
            self.item_widgets.append(item)

    # ---------- Selection Logic (Ctrl / Shift) ----------

    def _apply_state_to_index(self, index: int, value: bool, apply_change: bool = True):
        if 0 <= index < len(self.item_widgets):
            item = self.item_widgets[index]
            item.switch_var.set(value)
            self.pending_states[item.name] = value
            if apply_change:
                self._apply_mod_change(item.name, value)

    def _on_item_click(self, index: int, current_value: bool, ctrl: bool, shift: bool):
        game_path = Path(self.config.game_path) if self.config.game_path else None
        if not game_path or not game_path.exists():
            messagebox.showerror("Error", "Please select a valid game folder first.")
            if 0 <= index < len(self.item_widgets):
                self.item_widgets[index].switch_var.set(not current_value)
            return

        if shift and self.last_clicked_index is not None:
            start = min(self.last_clicked_index, index)
            end = max(self.last_clicked_index, index)
            for i in range(start, end + 1):
                self._apply_state_to_index(i, current_value, apply_change=True)
        else:
            self._apply_state_to_index(index, current_value, apply_change=True)

        self.last_clicked_index = index

    # ---------- Apply Change (Install/Uninstall immediately) ----------

    def _apply_mod_change(self, name: str, value: bool):
        game_path = Path(self.config.game_path) if self.config.game_path else None
        if not game_path or not game_path.exists():
            messagebox.showerror("Error", "Please select a valid game folder first.")
            for item in self.item_widgets:
                if item.name == name:
                    item.switch_var.set(not value)
                    self.pending_states[name] = not value
                    break
            return

        try:
            if value:
                self.mod_manager.enable_mod(name, game_path)
                self.config.set_mod_state(name, True)
            else:
                self.mod_manager.disable_mod(name, game_path)
                self.config.set_mod_state(name, False)
            self.config.save()
        except Exception:
            for item in self.item_widgets:
                if item.name == name:
                    item.switch_var.set(not value)
                    self.pending_states[name] = not value
                    break


def main():
    MODS_DIR.mkdir(exist_ok=True, parents=True)
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
