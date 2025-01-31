import os
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import platform
import json
import ctypes

from elevate import elevate

# --------------------------------------------------------
#   "LinkMasterX" - Symbolic Link Manager
#   Technical Name: "SMLK-Pro"
#   (c) 2025 LinkMasterX by dedAI - All Rights Reserved
# --------------------------------------------------------

HISTORY_FILE = "symlink_history.json"

# Request admin privileges if not already elevated
elevate()

def load_history():
    """
    Loads symlink operation history from a JSON file.
    Returns a list of records or an empty list.
    """
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_history(history_list):
    """
    Saves symlink operation history to a JSON file.
    """
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_list, f, indent=2)

def move_item(src, dst_folder):
    """
    Moves a file or directory from src to dst_folder and returns the new location path.
    Raises an exception if the move operation fails.
    """
    item_name = os.path.basename(src.rstrip("\\/"))
    new_location = os.path.join(dst_folder, item_name)

    os.makedirs(dst_folder, exist_ok=True)
    shutil.move(src, new_location)
    return new_location

def create_symlink(src, dst):
    """
    Creates a symbolic link pointing from src to dst (Windows only).
    Raises an exception if creation fails or if the OS is not Windows.
    """
    if platform.system() != "Windows":
        raise NotImplementedError("Symbolic links are only supported on Windows in this script.")
    if os.path.exists(src):
        raise FileExistsError(f"The source path '{src}' already exists.")

    # Construct the mklink command
    if os.path.isdir(dst):
        cmd = f'mklink /d "{src}" "{dst}"'
    else:
        cmd = f'mklink "{src}" "{dst}"'

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)

def remove_symlink(symlink_path):
    """
    Removes a symbolic link if it exists.
    """
    if os.path.exists(symlink_path):
        if os.path.islink(symlink_path):
            os.unlink(symlink_path)
        else:
            raise Exception("The specified path is not a symbolic link or already removed.")

def validate_paths(src, dst_folder):
    """
    Validates source and destination paths for existence and type consistency.
    Returns True if valid, else False and shows an error message.
    """
    if not src or not os.path.exists(src):
        messagebox.showerror("Error", "Invalid source path.")
        return False
    if not dst_folder or not os.path.exists(dst_folder):
        messagebox.showerror("Error", "Invalid destination path.")
        return False
    if os.path.isdir(src) and not os.path.isdir(dst_folder):
        messagebox.showerror(
            "Error",
            "Cannot move a folder into a path that is not a folder."
        )
        return False
    return True

class HistoryWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("LinkMasterX History")
        self.geometry("500x300")
        self.parent = parent
        self.history = load_history()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(self, columns=("src", "dst", "symlink"), show="headings")
        self.tree.heading("src", text="Original Path")
        self.tree.heading("dst", text="Moved Path")
        self.tree.heading("symlink", text="Symlink Path")
        self.tree.grid(row=0, column=0, sticky="nsew")

        for record in self.history:
            self.tree.insert("", tk.END, values=(record["original_src"], record["final_dst"], record["symlink_path"]))

        button_frame = ttk.Frame(self)
        button_frame.grid(row=1, column=0, pady=10)

        revert_button = ttk.Button(button_frame, text="Revert Selected", command=self.revert_selected)
        revert_button.pack(side=tk.LEFT, padx=5)

        close_button = ttk.Button(button_frame, text="Close", command=self.destroy)
        close_button.pack(side=tk.LEFT)

    def revert_selected(self):
        """
        Reverts the selected symlink operation:
         1) Remove symlink
         2) Move the item back
         3) Remove record from history
        """
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showerror("Error", "No entry selected.")
            return
        values = self.tree.item(selected_item, "values")
        original_src, final_dst, symlink_path = values

        try:
            remove_symlink(symlink_path)
            shutil.move(final_dst, original_src)
            messagebox.showinfo("Success", f"Reverted symlink and moved back to {original_src}.")

            self.history = [record for record in self.history if record["symlink_path"] != symlink_path]
            save_history(self.history)
            self.tree.delete(selected_item)
        except Exception as e:
            messagebox.showerror("Error", str(e))

class SymlinkGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LinkMasterX - Symbolic Link Manager")

        # Load a custom icon (ICO file) for the top-left corner if available:
        # Replace "myicon.ico" with your .ico file's name or path
        try:
            self.root.iconbitmap("myicon.ico")
        except:
            pass

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except:
            pass

        self.main_frame = ttk.Frame(self.root, padding="15")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        history_menu = tk.Menu(menubar, tearoff=False)
        history_menu.add_command(label="View/Manage History", command=self.show_history)
        menubar.add_cascade(label="History", menu=history_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(
            label="Instructions",
            command=lambda: messagebox.showinfo(
                "Instructions",
                "1. Select a source file or folder.\n"
                "2. Select a destination folder.\n"
                "3. Click 'Move & Link' to move the item and create a symlink.\n"
                "4. Use 'History' -> 'View/Manage History' to revert any previous operations."
            )
        )
        menubar.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menubar)

        self.source_label = ttk.Label(self.main_frame, text="Source Path:")
        self.source_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")

        self.source_entry = ttk.Entry(self.main_frame, width=40)
        self.source_entry.grid(row=0, column=1, padx=5, pady=5)

        self.source_file_button = ttk.Button(
            self.main_frame,
            text="Browse File",
            command=self.browse_source_file
        )
        self.source_file_button.grid(row=0, column=2, padx=5, pady=5)

        self.source_folder_button = ttk.Button(
            self.main_frame,
            text="Browse Folder",
            command=self.browse_source_folder
        )
        self.source_folder_button.grid(row=0, column=3, padx=5, pady=5)

        self.dest_label = ttk.Label(self.main_frame, text="Destination Path:")
        self.dest_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")

        self.dest_entry = ttk.Entry(self.main_frame, width=40)
        self.dest_entry.grid(row=1, column=1, padx=5, pady=5)

        self.dest_button = ttk.Button(
            self.main_frame,
            text="Browse Folder",
            command=self.browse_destination
        )
        self.dest_button.grid(row=1, column=2, padx=5, pady=5)

        self.create_button = ttk.Button(
            self.main_frame,
            text="Move & Link",
            command=self.run_symlink_process
        )
        self.create_button.grid(row=2, column=1, pady=10)

        # Status label
        self.status_label = ttk.Label(self.main_frame, text="", foreground="gray")
        self.status_label.grid(row=3, column=0, columnspan=4, sticky="w", pady=5)

        # Simple watermark in a separate frame
        self.watermark_label = ttk.Label(self.main_frame, text="© 2025 LinkMasterX by dedAI - All Rights Reserved")
        self.watermark_label.grid(row=4, column=1, columnspan=2, pady=10)

    def browse_source_file(self):
        path = filedialog.askopenfilename(title="Select Source File")
        if path:
            self.source_entry.delete(0, tk.END)
            self.source_entry.insert(0, path)
            self.status_label.config(text="Selected a file as source.")

    def browse_source_folder(self):
        path = filedialog.askdirectory(title="Select Source Folder")
        if path:
            self.source_entry.delete(0, tk.END)
            self.source_entry.insert(0, path)
            self.status_label.config(text="Selected a folder as source.")

    def browse_destination(self):
        path = filedialog.askdirectory(title="Select Destination Folder")
        if path:
            self.dest_entry.delete(0, tk.END)
            self.dest_entry.insert(0, path)
            self.status_label.config(text="Selected destination folder.")

    def run_symlink_process(self):
        src = self.source_entry.get().strip()
        dst_folder = self.dest_entry.get().strip()

        if not validate_paths(src, dst_folder):
            return

        try:
            self.status_label.config(text="Moving item, please wait...")
            new_location = move_item(src, dst_folder)
            self.status_label.config(text="Creating symlink...")
            create_symlink(src, new_location)

            history_list = load_history()
            record = {
                "original_src": src,
                "final_dst": new_location,
                "symlink_path": src
            }
            history_list.append(record)
            save_history(history_list)

            messagebox.showinfo("Success", f"Moved to {new_location} and created symlink.")
            self.status_label.config(text="Operation completed successfully.")
        except FileExistsError as e:
            messagebox.showerror("Error", str(e))
            self.status_label.config(text=str(e))
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to create symlink.\n{e.stderr}")
            self.status_label.config(text="Symlink creation failed.")
        except NotImplementedError as e:
            messagebox.showerror("Error", str(e))
            self.status_label.config(text=str(e))
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred.\n{e}")
            self.status_label.config(text="An unexpected error occurred.")

    def show_history(self):
        HistoryWindow(self.root)

def main():
    root = tk.Tk()
    app = SymlinkGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
