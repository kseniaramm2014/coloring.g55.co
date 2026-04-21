import json
import os
import re
import tkinter as tk
from tkinter import ttk, messagebox

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CATEGORIES_DIR = os.path.join(SCRIPT_DIR, "categories")
ROOT_CATEGORIES_FILE = os.path.join(SCRIPT_DIR, "categories.json")

PAGE_TEMPLATE = {"id": "", "title": "", "description": ""}
CATEGORY_TEMPLATE = {"id": "", "name": "", "description": ""}
NEW_CATEGORY_FILE_TEMPLATE = {"pages": []}


def list_json_files(folder: str) -> list[str]:
    files = []
    try:
        for name in os.listdir(folder):
            if name.lower().endswith(".json") and os.path.isfile(os.path.join(folder, name)):
                files.append(name)
    except Exception:
        pass
    files.sort(key=lambda s: s.lower())
    return files


def list_all_editable_files() -> list[str]:
    files = []
    if os.path.isfile(ROOT_CATEGORIES_FILE):
        files.append("categories.json")
    files.extend(list_json_files(CATEGORIES_DIR))
    return files


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


def normalize_loaded_json(loaded, file_name: str):
    if file_name == "categories.json":
        if isinstance(loaded, dict) and "categories" in loaded and isinstance(loaded["categories"], list):
            return loaded["categories"], loaded, "categories"
        raise ValueError('Unsupported categories.json format. Expected {"categories": [...]}')

    if isinstance(loaded, dict) and "pages" in loaded and isinstance(loaded["pages"], list):
        return loaded["pages"], loaded, "pages"
    if isinstance(loaded, list):
        return loaded, None, "pages"
    raise ValueError('Unsupported JSON format. Expected {"pages": [...]} or a list.')


def category_keyword_from_filename(name: str) -> str:
    name = os.path.splitext((name or "").strip())[0]
    return name.lower().replace("-", " ").strip()


def count_title_keyword_matches(items, keyword: str) -> int:
    keyword = (keyword or "").strip().lower().replace("-", " ")
    if not keyword:
        return 0

    count = 0
    for it in items:
        title = str(it.get("title", "")).strip().lower()
        if keyword in title:
            count += 1
    return count


def title_matches_keyword(title: str, keyword: str) -> bool:
    keyword = (keyword or "").strip().lower().replace("-", " ")
    title = (title or "").strip().lower()
    if not keyword:
        return False
    return keyword in title


def category_description_has_link(description: str) -> bool:
    description = str(description or "").lower()
    return "<a href=" in description


def count_categories_with_links(items) -> int:
    count = 0
    for it in items:
        if category_description_has_link(it.get("description", "")):
            count += 1
    return count


class JsonGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JSON Pages Editor")
        self.state("zoomed")

        self.current_file = None
        self.items = []
        self.wrapper = None
        self.mode = "pages"
        self.selected_index = None

        self.files = list_all_editable_files()

        self.file_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="")

        self.build_ui()

        if self.files:
            self.select_category_by_name(self.files[0])
        else:
            messagebox.showwarning("No JSON files", f"No editable .json files found in:\n{SCRIPT_DIR}")
            self.set_status("No JSON files found")

    def build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Button(top, text="Reload list", command=self.reload_list).pack(side="left")

        ttk.Label(top, text="Current file").pack(side="left", padx=(16, 6))
        ttk.Label(top, textvariable=self.file_var).pack(side="left")

        main = ttk.Frame(self, padding=10)
        main.pack(fill="both", expand=True)

        sidebar = ttk.Frame(main)
        sidebar.pack(side="left", fill="y")

        mid = ttk.Frame(main)
        mid.pack(side="left", fill="both", expand=True, padx=(12, 0))

        right = ttk.Frame(main)
        right.pack(side="right", fill="y", padx=(12, 0))

        ttk.Label(sidebar, text="Files").pack(anchor="w")

        cat_frame = ttk.Frame(sidebar)
        cat_frame.pack(fill="y", expand=True, pady=(6, 0))

        self.cat_listbox = tk.Listbox(cat_frame, height=28, exportselection=False, width=34)
        self.cat_listbox.pack(side="left", fill="y", expand=False)
        self.cat_listbox.bind("<<ListboxSelect>>", lambda e: self.on_category_click())

        cat_scroll = ttk.Scrollbar(cat_frame, orient="vertical", command=self.cat_listbox.yview)
        cat_scroll.pack(side="right", fill="y")
        self.cat_listbox.config(yscrollcommand=cat_scroll.set)

        ttk.Label(mid, text="Items").pack(anchor="w")

        list_frame = ttk.Frame(mid)
        list_frame.pack(fill="both", expand=True, pady=(6, 0))

        self.listbox = tk.Listbox(list_frame, height=22, exportselection=False)
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", lambda e: self.pick_from_list())

        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scroll.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scroll.set)

        form = ttk.LabelFrame(right, text="Editor", padding=10)
        form.pack(fill="x")

        self.name_title_label = ttk.Label(form, text="Title")
        self.name_title_label.grid(row=0, column=0, sticky="w")

        self.title_var = tk.StringVar()
        title_entry = ttk.Entry(form, textvariable=self.title_var, width=46)
        title_entry.grid(row=1, column=0, columnspan=2, sticky="we", pady=(0, 8))
        title_entry.bind("<KeyRelease>", self.on_title_change)

        ttk.Label(form, text="Id").grid(row=2, column=0, sticky="w")
        self.id_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.id_var, width=46).grid(
            row=3, column=0, columnspan=2, sticky="we", pady=(0, 8)
        )

        ttk.Label(form, text="Description").grid(row=4, column=0, sticky="w")
        self.desc_text = tk.Text(form, width=46, height=9, wrap="word")
        self.desc_text.grid(row=5, column=0, columnspan=2, sticky="we", pady=(0, 8))

        btn_row = ttk.Frame(form)
        btn_row.grid(row=6, column=0, columnspan=2, sticky="we")

        self.new_btn = ttk.Button(btn_row, text="New", command=self.new_template)
        self.new_btn.pack(side="left")
        self.add_btn = ttk.Button(btn_row, text="Add", command=self.add_item)
        self.add_btn.pack(side="left", padx=6)
        self.update_btn = ttk.Button(btn_row, text="Update", command=self.update_item)
        self.update_btn.pack(side="left", padx=6)
        self.delete_btn = ttk.Button(btn_row, text="Delete", command=self.delete_item)
        self.delete_btn.pack(side="left", padx=6)
        self.move_top_btn = ttk.Button(btn_row, text="Move to top", command=self.move_selected_to_top)
        self.move_top_btn.pack(side="left", padx=6)

        search = ttk.LabelFrame(right, text="Find by title", padding=10)
        search.pack(fill="x", pady=(10, 0))

        ttk.Label(search, text="Title").grid(row=0, column=0, sticky="w")
        self.search_title_var = tk.StringVar()
        search_entry = ttk.Entry(search, textvariable=self.search_title_var, width=34)
        search_entry.grid(row=1, column=0, sticky="we", padx=(0, 6))
        search_entry.bind("<Return>", lambda e: self.search_by_title())
        ttk.Button(search, text="Find", command=self.search_by_title).grid(row=1, column=1, sticky="e")

        ttk.Label(right, textvariable=self.status_var).pack(anchor="w", pady=(10, 0))

        self.refresh_category_list()
        self.new_template()
        self.update_mode_ui()
        self.set_status("Ready")

    def is_root_categories_mode(self) -> bool:
        return self.mode == "categories"

    def update_mode_ui(self):
        if self.is_root_categories_mode():
            self.name_title_label.config(text="Name")
        else:
            self.name_title_label.config(text="Title")

    def set_status(self, text: str):
        self.status_var.set(text)

    def update_page_match_status(self, prefix: str = ""):
        total = len(self.items)

        if self.is_root_categories_mode():
            linked = count_categories_with_links(self.items)
            text = f"Descriptions: {linked}/{total}"
        else:
            file_name = os.path.basename(self.current_file) if self.current_file else self.file_var.get()
            keyword = category_keyword_from_filename(file_name)
            matched = count_title_keyword_matches(self.items, keyword)
            text = f"Pages: {matched}/{total}"

        if prefix:
            self.set_status(f"{prefix}  {text}")
        else:
            self.set_status(text)

    def refresh_category_list(self):
        current_name = os.path.basename(self.current_file) if self.current_file else ""
        self.cat_listbox.delete(0, tk.END)
        for name in self.files:
            self.cat_listbox.insert(tk.END, name)
        if current_name and current_name in self.files:
            self.select_category_by_name(current_name, load=False)

    def select_category_by_name(self, name: str, load: bool = True):
        if name not in self.files:
            return
        idx = self.files.index(name)
        self.cat_listbox.selection_clear(0, tk.END)
        self.cat_listbox.selection_set(idx)
        self.cat_listbox.see(idx)
        if load:
            self.load_selected(name)

    def on_category_click(self):
        sel = self.cat_listbox.curselection()
        if not sel:
            return
        i = int(sel[0])
        if i < 0 or i >= len(self.files):
            return
        name = self.files[i]
        if self.current_file and os.path.basename(self.current_file) == name:
            return
        self.load_selected(name)

    def reload_list(self):
        keep = os.path.basename(self.current_file) if self.current_file else ""
        self.files = list_all_editable_files()

        self.refresh_category_list()

        if not self.files:
            self.file_var.set("")
            self.current_file = None
            self.items = []
            self.wrapper = None
            self.mode = "pages"
            self.selected_index = None
            self.refresh_list()
            self.new_template()
            self.update_mode_ui()
            self.set_status("No JSON files found")
            return

        if keep and keep in self.files:
            self.select_category_by_name(keep)
        else:
            self.select_category_by_name(self.files[0])

    def path_for_name(self, name: str):
        name = (name or "").strip()
        if not name:
            return None
        if name == "categories.json":
            return ROOT_CATEGORIES_FILE
        return os.path.join(CATEGORIES_DIR, name)

    def load_selected(self, file_name: str):
        path = self.path_for_name(file_name)
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)

            items, wrapper, mode = normalize_loaded_json(loaded, os.path.basename(path))

            cleaned = []
            if mode == "categories":
                for it in items:
                    if isinstance(it, dict):
                        cleaned.append(
                            {
                                "id": str(it.get("id", "")).strip(),
                                "name": str(it.get("name", "")).strip(),
                                "description": str(it.get("description", "")).strip(),
                            }
                        )
            else:
                for it in items:
                    if isinstance(it, dict):
                        cleaned.append(
                            {
                                "id": str(it.get("id", "")).strip(),
                                "title": str(it.get("title", "")).strip(),
                                "description": str(it.get("description", "")).strip(),
                            }
                        )

            self.items = cleaned
            self.wrapper = wrapper
            self.mode = mode
            self.current_file = path
            self.selected_index = None

            self.file_var.set(os.path.basename(self.current_file))
            self.refresh_list()
            self.new_template()
            self.update_mode_ui()
            self.update_page_match_status("Loaded")
        except Exception as e:
            self.items = []
            self.wrapper = None
            self.mode = "pages"
            self.current_file = path
            self.selected_index = None
            self.file_var.set(os.path.basename(self.current_file) if self.current_file else "")
            self.refresh_list()
            self.new_template()
            self.update_mode_ui()
            messagebox.showerror("Load failed", f"Could not load JSON:\n{e}")
            self.set_status("Load failed")

    def save_json(self, silent: bool = True) -> bool:
        if not self.current_file:
            return False
        try:
            if self.wrapper is None:
                payload = self.items
            else:
                if self.is_root_categories_mode():
                    self.wrapper["categories"] = self.items
                else:
                    self.wrapper["pages"] = self.items
                payload = self.wrapper

            with open(self.current_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=0)

            self.set_status("Auto saved")
            return True
        except Exception as e:
            self.set_status("Save failed")
            if not silent:
                messagebox.showerror("Save failed", f"Could not save JSON:\n{e}")
            return False

    def autosave(self) -> bool:
        return self.save_json(silent=True)

    def refresh_list(self):
        self.listbox.delete(0, tk.END)

        file_name = os.path.basename(self.current_file) if self.current_file else self.file_var.get()
        keyword = category_keyword_from_filename(file_name)

        for idx, it in enumerate(self.items):
            label = it.get("name") if self.is_root_categories_mode() else it.get("title")
            label = label or it.get("id") or "(empty)"
            self.listbox.insert(tk.END, label)

            if self.is_root_categories_mode():
                if not category_description_has_link(it.get("description", "")):
                    self.listbox.itemconfig(idx, bg="#e6e6e6", fg="#555555")
            else:
                if not title_matches_keyword(it.get("title", ""), keyword):
                    self.listbox.itemconfig(idx, bg="#ffe5e5", fg="#a00000")

    def on_title_change(self, event=None):
        if self.selected_index is not None:
            return
        current_id = self.id_var.get().strip()
        if current_id:
            return
        value = self.title_var.get().strip()
        if not value:
            return
        self.id_var.set(slugify(value))

    def read_form(self):
        if self.is_root_categories_mode():
            return {
                "id": self.id_var.get().strip(),
                "name": self.title_var.get().strip(),
                "description": self.desc_text.get("1.0", "end").strip(),
            }

        return {
            "id": self.id_var.get().strip(),
            "title": self.title_var.get().strip(),
            "description": self.desc_text.get("1.0", "end").strip(),
        }

    def write_form(self, it):
        if self.is_root_categories_mode():
            self.title_var.set(it.get("name", ""))
        else:
            self.title_var.set(it.get("title", ""))
        self.id_var.set(it.get("id", ""))
        self.desc_text.delete("1.0", "end")
        self.desc_text.insert("1.0", it.get("description", ""))

    def new_template(self):
        self.selected_index = None
        if self.is_root_categories_mode():
            self.write_form(CATEGORY_TEMPLATE.copy())
            self.set_status("New category")
        else:
            self.write_form(PAGE_TEMPLATE.copy())
            self.set_status("New page")

    def create_category_json_file(self, category_id: str):
        category_id = (category_id or "").strip()
        if not category_id:
            return

        os.makedirs(CATEGORIES_DIR, exist_ok=True)
        file_path = os.path.join(CATEGORIES_DIR, f"{category_id}.json")

        try:
            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(NEW_CATEGORY_FILE_TEMPLATE, f, ensure_ascii=False, indent=0)
        except Exception as e:
            messagebox.showerror("Category file creation failed", f"Could not create category JSON file:\n{e}")

    def create_category_folder(self, category_id: str):
        category_id = (category_id or "").strip()
        if not category_id:
            return

        folder_path = os.path.join(CATEGORIES_DIR, category_id)
        characters_file_path = os.path.join(folder_path, "characters.txt")
        characters_line = category_id.replace("-", " ")

        try:
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)

            if not os.path.exists(characters_file_path):
                with open(characters_file_path, "w", encoding="utf-8") as f:
                    f.write(characters_line + "\n")
        except Exception as e:
            messagebox.showerror("Folder creation failed", f"Could not create folder or characters.txt:\n{e}")

    def find_duplicate_id(self, item_id, ignore_index=None):
        for idx, it in enumerate(self.items):
            if ignore_index is not None and idx == ignore_index:
                continue
            if str(it.get("id", "")).strip() == item_id:
                return idx
        return None

    def goto_index(self, idx: int):
        if idx < 0 or idx >= len(self.items):
            return
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(idx)
        self.listbox.see(idx)
        self.selected_index = idx
        self.write_form(self.items[idx])

        if self.is_root_categories_mode():
            self.update_page_match_status(f"Selected category {idx + 1} of {len(self.items)}")
        else:
            self.update_page_match_status(f"Selected page {idx + 1} of {len(self.items)}")

    def search_by_title(self):
        q = self.search_title_var.get().strip().lower()
        if not q:
            messagebox.showwarning("Missing text", "Enter text to search.")
            return

        matches = []
        field = "name" if self.is_root_categories_mode() else "title"
        for idx, it in enumerate(self.items):
            t = str(it.get(field, "")).strip().lower()
            if q in t:
                matches.append(idx)

        if not matches:
            what = "category" if self.is_root_categories_mode() else "page"
            messagebox.showinfo("Not found", f"No {what} found containing:\n{q}")
            return

        self.goto_index(matches[0])
        self.set_status(f"Found {len(matches)} match(es)")

    def move_selected_to_top(self):
        if self.selected_index is None:
            messagebox.showwarning("Nothing selected", "Select an item to move to the top.")
            return

        if self.selected_index == 0:
            if self.is_root_categories_mode():
                self.update_page_match_status("Category is already at the top")
            else:
                self.update_page_match_status("Page is already at the top")
            return

        item = self.items.pop(self.selected_index)
        self.items.insert(0, item)
        self.refresh_list()
        self.goto_index(0)

        if not self.autosave():
            messagebox.showerror("Auto save failed", "Could not auto save after moving item to top.")
            return

        if self.is_root_categories_mode():
            self.update_page_match_status("Moved category to top and auto saved")
        else:
            self.update_page_match_status("Moved page to top and auto saved")

    def add_item(self):
        it = self.read_form()
        label = it.get("name") if self.is_root_categories_mode() else it.get("title")

        if not it["id"] or not label:
            messagebox.showwarning("Missing fields", "Please fill Id and Name or Title.")
            return

        dup = self.find_duplicate_id(it["id"])
        if dup is not None:
            what = "category" if self.is_root_categories_mode() else "page"
            messagebox.showerror("Duplicate id", f"A {what} with this id already exists at index {dup + 1}.")
            return

        self.items.insert(0, it)
        self.refresh_list()
        self.goto_index(0)

        if not self.autosave():
            messagebox.showerror("Auto save failed", "Could not auto save after add.")
            return

        if self.is_root_categories_mode():
            self.create_category_json_file(it["id"])
            self.create_category_folder(it["id"])
            self.files = list_all_editable_files()
            self.refresh_category_list()
            self.select_category_by_name("categories.json", load=False)

        self.update_page_match_status("Added and auto saved")

    def update_item(self):
        if self.selected_index is None:
            what = "category" if self.is_root_categories_mode() else "page"
            messagebox.showwarning("Nothing selected", f"Select a {what} to update.")
            return

        it = self.read_form()
        label = it.get("name") if self.is_root_categories_mode() else it.get("title")
        if not it["id"] or not label:
            messagebox.showwarning("Missing fields", "Please fill Id and Name or Title.")
            return

        dup = self.find_duplicate_id(it["id"], ignore_index=self.selected_index)
        if dup is not None:
            other = "category" if self.is_root_categories_mode() else "page"
            messagebox.showerror("Duplicate id", f"Another {other} already uses this id at index {dup + 1}.")
            return

        self.items[self.selected_index] = it
        keep = self.selected_index
        self.refresh_list()
        self.goto_index(keep)

        if not self.autosave():
            messagebox.showerror("Auto save failed", "Could not auto save after update.")

        self.update_page_match_status("Updated and auto saved")

    def delete_item(self):
        if self.selected_index is None:
            what = "category" if self.is_root_categories_mode() else "page"
            messagebox.showwarning("Nothing selected", f"Select a {what} to delete.")
            return

        idx = self.selected_index
        label = self.items[idx].get("name") if self.is_root_categories_mode() else self.items[idx].get("title")
        label = label or self.items[idx].get("id")
        what = "category" if self.is_root_categories_mode() else "page"
        if not messagebox.askyesno("Delete", f"Delete selected {what}?\n\n{label}"):
            return

        del self.items[idx]
        self.selected_index = None
        self.refresh_list()
        self.new_template()

        if not self.autosave():
            messagebox.showerror("Auto save failed", "Could not auto save after delete.")

        self.update_page_match_status("Deleted and auto saved")

    def pick_from_list(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = int(sel[0])
        if idx < len(self.items):
            self.selected_index = idx
            self.write_form(self.items[idx])
            if self.is_root_categories_mode():
                self.update_page_match_status(f"Selected category {idx + 1} of {len(self.items)}")
            else:
                self.update_page_match_status(f"Selected page {idx + 1} of {len(self.items)}")


if __name__ == "__main__":
    app = JsonGui()
    app.mainloop()
