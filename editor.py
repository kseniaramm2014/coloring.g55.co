import json
import os
import re
import tkinter as tk
from tkinter import ttk, messagebox

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CATEGORIES_DIR = os.path.join(SCRIPT_DIR, "categories")

TEMPLATE = {"id": "", "title": "", "description": ""}


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


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


def normalize_loaded_json(loaded):
    if isinstance(loaded, dict) and "pages" in loaded and isinstance(loaded["pages"], list):
        return loaded["pages"], loaded
    if isinstance(loaded, list):
        return loaded, None
    raise ValueError('Unsupported JSON format. Expected {"pages": [...]} or a list.')


def category_keyword_from_filename(name: str) -> str:
    name = os.path.splitext((name or "").strip())[0]
    return name.lower().replace("-", " ").strip()


def count_title_keyword_matches(pages, keyword: str) -> int:
    keyword = (keyword or "").strip().lower().replace("-", " ")
    if not keyword:
        return 0

    count = 0
    for it in pages:
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


class JsonGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JSON Pages Editor")
        self.state("zoomed")

        self.current_file = None
        self.pages = []
        self.wrapper = None
        self.selected_index = None

        self.files = list_json_files(CATEGORIES_DIR)

        self.file_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="")

        self.build_ui()

        if self.files:
            self.select_category_by_name(self.files[0])
        else:
            messagebox.showwarning("No JSON files", f"No .json files found in:\n{CATEGORIES_DIR}")
            self.set_status("No JSON files found")

    def build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Button(top, text="Reload list", command=self.reload_list).pack(side="left")

        ttk.Label(top, text="Current category").pack(side="left", padx=(16, 6))
        ttk.Label(top, textvariable=self.file_var).pack(side="left")

        main = ttk.Frame(self, padding=10)
        main.pack(fill="both", expand=True)

        sidebar = ttk.Frame(main)
        sidebar.pack(side="left", fill="y")

        mid = ttk.Frame(main)
        mid.pack(side="left", fill="both", expand=True, padx=(12, 0))

        right = ttk.Frame(main)
        right.pack(side="right", fill="y", padx=(12, 0))

        ttk.Label(sidebar, text="Categories").pack(anchor="w")

        cat_frame = ttk.Frame(sidebar)
        cat_frame.pack(fill="y", expand=True, pady=(6, 0))

        self.cat_listbox = tk.Listbox(cat_frame, height=28, exportselection=False, width=34)
        self.cat_listbox.pack(side="left", fill="y", expand=False)
        self.cat_listbox.bind("<<ListboxSelect>>", lambda e: self.on_category_click())

        cat_scroll = ttk.Scrollbar(cat_frame, orient="vertical", command=self.cat_listbox.yview)
        cat_scroll.pack(side="right", fill="y")
        self.cat_listbox.config(yscrollcommand=cat_scroll.set)

        ttk.Label(mid, text="Pages").pack(anchor="w")

        list_frame = ttk.Frame(mid)
        list_frame.pack(fill="both", expand=True, pady=(6, 0))

        self.listbox = tk.Listbox(list_frame, height=22, exportselection=False)
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", lambda e: self.pick_from_list())

        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scroll.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scroll.set)

        form = ttk.LabelFrame(right, text="Template page", padding=10)
        form.pack(fill="x")

        ttk.Label(form, text="Title").grid(row=0, column=0, sticky="w")
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

        ttk.Button(btn_row, text="New", command=self.new_template).pack(side="left")
        ttk.Button(btn_row, text="Add", command=self.add_page).pack(side="left", padx=6)
        ttk.Button(btn_row, text="Update", command=self.update_page).pack(side="left", padx=6)
        ttk.Button(btn_row, text="Delete", command=self.delete_page).pack(side="left", padx=6)

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
        self.set_status("Ready")

    def set_status(self, text: str):
        self.status_var.set(text)

    def update_page_match_status(self, prefix: str = ""):
        file_name = os.path.basename(self.current_file) if self.current_file else self.file_var.get()
        keyword = category_keyword_from_filename(file_name)
        total = len(self.pages)
        matched = count_title_keyword_matches(self.pages, keyword)

        if prefix:
            self.set_status(f"{prefix}  Pages: {matched}/{total}")
        else:
            self.set_status(f"Pages: {matched}/{total}")

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
        self.files = list_json_files(CATEGORIES_DIR)

        self.refresh_category_list()

        if not self.files:
            self.file_var.set("")
            self.current_file = None
            self.pages = []
            self.wrapper = None
            self.selected_index = None
            self.refresh_list()
            self.new_template()
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
        return os.path.join(CATEGORIES_DIR, name)

    def load_selected(self, file_name: str):
        path = self.path_for_name(file_name)
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)

            pages, wrapper = normalize_loaded_json(loaded)

            cleaned = []
            for it in pages:
                if isinstance(it, dict):
                    cleaned.append(
                        {
                            "id": str(it.get("id", "")).strip(),
                            "title": str(it.get("title", "")).strip(),
                            "description": str(it.get("description", "")).strip(),
                        }
                    )

            self.pages = cleaned
            self.wrapper = wrapper
            self.current_file = path
            self.selected_index = None

            self.file_var.set(os.path.basename(self.current_file))
            self.refresh_list()
            self.new_template()
            self.update_page_match_status("Loaded")
        except Exception as e:
            self.pages = []
            self.wrapper = None
            self.current_file = path
            self.selected_index = None
            self.file_var.set(os.path.basename(self.current_file) if self.current_file else "")
            self.refresh_list()
            self.new_template()
            messagebox.showerror("Load failed", f"Could not load JSON:\n{e}")
            self.set_status("Load failed")

    def save_json(self, silent: bool = True) -> bool:
        if not self.current_file:
            return False
        try:
            if self.wrapper is None:
                payload = self.pages
            else:
                self.wrapper["pages"] = self.pages
                payload = self.wrapper

            with open(self.current_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=4)

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

        for idx, it in enumerate(self.pages):
            label = it.get("title") or it.get("id") or "(empty)"
            self.listbox.insert(tk.END, label)

            if not title_matches_keyword(it.get("title", ""), keyword):
                self.listbox.itemconfig(idx, bg="#ffe5e5", fg="#a00000")

    def on_title_change(self, event=None):
        if self.selected_index is not None:
            return
        current_id = self.id_var.get().strip()
        if current_id:
            return
        title = self.title_var.get().strip()
        if not title:
            return
        self.id_var.set(slugify(title))

    def read_form(self):
        return {
            "id": self.id_var.get().strip(),
            "title": self.title_var.get().strip(),
            "description": self.desc_text.get("1.0", "end").strip(),
        }

    def write_form(self, it):
        self.title_var.set(it.get("title", ""))
        self.id_var.set(it.get("id", ""))
        self.desc_text.delete("1.0", "end")
        self.desc_text.insert("1.0", it.get("description", ""))

    def new_template(self):
        self.selected_index = None
        self.write_form(TEMPLATE.copy())
        self.set_status("New page")

    def find_duplicate_id(self, page_id, ignore_index=None):
        for idx, it in enumerate(self.pages):
            if ignore_index is not None and idx == ignore_index:
                continue
            if str(it.get("id", "")).strip() == page_id:
                return idx
        return None

    def goto_index(self, idx: int):
        if idx < 0 or idx >= len(self.pages):
            return
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(idx)
        self.listbox.see(idx)
        self.selected_index = idx
        self.write_form(self.pages[idx])
        self.update_page_match_status(f"Selected page {idx + 1} of {len(self.pages)}")

    def search_by_title(self):
        q = self.search_title_var.get().strip().lower()
        if not q:
            messagebox.showwarning("Missing title", "Enter a title to search.")
            return

        matches = []
        for idx, it in enumerate(self.pages):
            t = str(it.get("title", "")).strip().lower()
            if q in t:
                matches.append(idx)

        if not matches:
            messagebox.showinfo("Not found", f"No page found containing:\n{q}")
            return

        self.goto_index(matches[0])
        self.set_status(f"Found {len(matches)} match(es)")

    def add_page(self):
        it = self.read_form()
        if not it["id"] or not it["title"]:
            messagebox.showwarning("Missing fields", "Please fill Id and Title.")
            return

        dup = self.find_duplicate_id(it["id"])
        if dup is not None:
            messagebox.showerror("Duplicate id", f"A page with this id already exists at index {dup + 1}.")
            return

        self.pages.insert(0, it)
        self.refresh_list()
        self.goto_index(0)

        if not self.autosave():
            messagebox.showerror("Auto save failed", "Could not auto save after add.")

        self.update_page_match_status("Added and auto saved")

    def update_page(self):
        if self.selected_index is None:
            messagebox.showwarning("Nothing selected", "Select a page to update.")
            return

        it = self.read_form()
        if not it["id"] or not it["title"]:
            messagebox.showwarning("Missing fields", "Please fill Id and Title.")
            return

        dup = self.find_duplicate_id(it["id"], ignore_index=self.selected_index)
        if dup is not None:
            messagebox.showerror("Duplicate id", f"Another page already uses this id at index {dup + 1}.")
            return

        self.pages[self.selected_index] = it
        keep = self.selected_index
        self.refresh_list()
        self.goto_index(keep)

        if not self.autosave():
            messagebox.showerror("Auto save failed", "Could not auto save after update.")

        self.update_page_match_status("Updated and auto saved")

    def delete_page(self):
        if self.selected_index is None:
            messagebox.showwarning("Nothing selected", "Select a page to delete.")
            return

        idx = self.selected_index
        title = self.pages[idx].get("title") or self.pages[idx].get("id")
        if not messagebox.askyesno("Delete", f"Delete selected page?\n\n{title}"):
            return

        del self.pages[idx]
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
        if idx < len(self.pages):
            self.selected_index = idx
            self.write_form(self.pages[idx])
            self.update_page_match_status(f"Selected page {idx + 1} of {len(self.pages)}")


if __name__ == "__main__":
    app = JsonGui()
    app.mainloop()