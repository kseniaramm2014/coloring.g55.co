import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import random
import os
import re
import json


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, "app")

CATEGORIES_DIR = os.path.join(BASE_DIR, "categories")
STYLE_FILE = os.path.join(CATEGORIES_DIR, "style.txt")
ACTIONS_FILE = os.path.join(CATEGORIES_DIR, "actions.txt")

POOL_FILES = {
    "intro": os.path.join(APP_DIR, "intro_pool.txt"),
    "usage": os.path.join(APP_DIR, "usage_pool.txt"),
    "ease": os.path.join(APP_DIR, "ease_pool.txt"),
    "benefit": os.path.join(APP_DIR, "benefit_pool.txt"),
}

POOLS = {k: [] for k in POOL_FILES.keys()}

LIST_NAMES = ["characters", "actions", "environments"]

COPIED_BG = "systemHighlight"


def list_category_folders():
    if not os.path.isdir(CATEGORIES_DIR):
        return []
    return sorted(
        d
        for d in os.listdir(CATEGORIES_DIR)
        if os.path.isdir(os.path.join(CATEGORIES_DIR, d))
    )


def load_lines(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            out = []
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    out.append(line)
            return out
    except Exception:
        return []


def load_style():
    lines = load_lines(STYLE_FILE)
    return lines[0] if lines else ""


def load_shared_actions():
    return load_lines(ACTIONS_FILE)


def load_category_data(category_name):
    cat_dir = os.path.join(CATEGORIES_DIR, category_name)
    data = {
        "characters": load_lines(os.path.join(cat_dir, "characters.txt")),
        "actions": load_shared_actions(),
        "environments": load_lines(os.path.join(cat_dir, "environments.txt")),
    }
    data["style"] = load_style()
    return data


SMALL_WORDS = {
    "a",
    "an",
    "the",
    "at",
    "in",
    "on",
    "to",
    "for",
    "with",
    "and",
    "or",
    "of",
    "as",
}


def format_title(title: str) -> str:
    words = title.strip().split()
    out = []

    for i, word in enumerate(words):
        lw = word.lower()
        if i != 0 and lw in SMALL_WORDS:
            out.append(lw)
        else:
            out.append(lw.capitalize())

    return " ".join(out)


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "coloring-page"


def strip_leading_article(text):
    s = (text or "").strip()
    lower = s.lower()
    if lower.startswith("a "):
        return s[2:].lstrip()
    if lower.startswith("an "):
        return s[3:].lstrip()
    return s


def build_h1(parts):
    character = strip_leading_article(parts["character"])
    action = parts["action"].strip()
    env = parts["environment"].strip()

    base = f"{character} {action} {env}"
    base = re.sub(r"\s{2,}", " ", base).strip()
    return f"Free Printable {format_title(base)} Coloring Page for Kids"


def build_seo_base_for_slug(parts):
    character = strip_leading_article(parts["character"])
    action = parts["action"].strip()
    env = parts["environment"].strip()

    base = f"{character} {action} {env} coloring page"
    base = re.sub(r"\s{2,}", " ", base).strip()
    return base


def build_id(parts):
    return slugify(build_seo_base_for_slug(parts))


def build_prompt(parts, style):
    core = f"{parts['character']} {parts['action']} {parts['environment']}"
    core = re.sub(r"\s{2,}", " ", core).strip()
    return "Coloring page on white background, " f"{core}, " f"{style}."


def _clean_sentence(s):
    s = re.sub(r"\s{2,}", " ", (s or "").strip())
    s = s.strip(" ,")
    if not s.endswith("."):
        s += "."
    return s


def load_pools():
    for key, path in POOL_FILES.items():
        POOLS[key] = load_lines(path)


def render_template(line, scene):
    return (line or "").replace("{scene}", scene)


def build_page_description(parts):
    character = parts["character"].strip()
    action = parts["action"].strip()
    env = parts["environment"].strip()

    scene = f"{character} {action} {env}"
    scene = re.sub(r"\s{2,}", " ", scene).strip()

    intro_pool = POOLS.get("intro") or []
    usage_pool = POOLS.get("usage") or []
    ease_pool = POOLS.get("ease") or []
    benefit_pool = POOLS.get("benefit") or []

    patterns = [
        ("intro", "usage", "ease", "benefit"),
        ("intro", "usage", "benefit", "ease"),
        ("intro", "ease", "usage", "benefit"),
        ("intro", "ease", "benefit", "usage"),
        ("intro", "benefit", "usage", "ease"),
        ("intro", "benefit", "ease", "usage"),
    ]

    pools = {
        "intro": intro_pool,
        "usage": usage_pool,
        "ease": ease_pool,
        "benefit": benefit_pool,
    }

    if any(not pools[k] for k in ("intro", "usage", "ease", "benefit")):
        return "Missing pool files."

    pattern = random.choice(patterns)
    sentences = []

    for key in pattern:
        line = random.choice(pools[key])
        sentences.append(_clean_sentence(render_template(line, scene)))

    return " ".join(sentences)


def generate_item(data):
    if not all(data.get(k) for k in LIST_NAMES) or not data.get("style"):
        parts = {"character": "", "action": "", "environment": ""}
        return {
            "parts": parts,
            "h1": "Missing files",
            "id": "missing-files",
            "prompt": "Missing files",
            "page_description": "Missing files",
        }

    if not all(POOLS.get(k) for k in ("intro", "usage", "ease", "benefit")):
        parts = {"character": "", "action": "", "environment": ""}
        return {
            "parts": parts,
            "h1": "Missing pool files",
            "id": "missing-pool-files",
            "prompt": "Missing pool files",
            "page_description": "Missing pool files",
        }

    parts = {
        "character": random.choice(data["characters"]),
        "action": random.choice(data["actions"]),
        "environment": random.choice(data["environments"]),
    }

    return {
        "parts": parts,
        "h1": build_h1(parts),
        "id": build_id(parts),
        "prompt": build_prompt(parts, data["style"]),
        "page_description": build_page_description(parts),
    }


def calculate_total_combinations(data):
    c = len(data.get("characters") or [])
    a = len(data.get("actions") or [])
    e = len(data.get("environments") or [])
    return c * a * e


def count_keyword_matches(lines, keyword):
    keyword = (keyword or "").strip().lower().replace("-", " ")
    if not keyword:
        return 0

    count = 0
    for line in lines or []:
        if keyword in (line or "").lower():
            count += 1
    return count


def category_json_path(category_name):
    return os.path.join(CATEGORIES_DIR, f"{category_name}.json")


def _safe_read_category_json(path):
    if not os.path.isfile(path):
        return {"pages": []}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {"pages": []}

    if not isinstance(data, dict):
        data = {"pages": []}
    if "pages" not in data or not isinstance(data["pages"], list):
        data["pages"] = []
    return data


def prepend_unique_pages_to_category_json(category_name, pages_to_add):
    path = category_json_path(category_name)
    data = _safe_read_category_json(path)

    existing_ids = set()
    for p in data.get("pages", []):
        if isinstance(p, dict) and p.get("id"):
            existing_ids.add(str(p["id"]))

    clean_add = []
    skipped = 0

    for p in pages_to_add:
        pid = str(p.get("id", "")).strip()
        if not pid:
            skipped += 1
            continue
        if pid in existing_ids:
            skipped += 1
            continue
        existing_ids.add(pid)
        clean_add.append(
            {
                "id": pid,
                "title": str(p.get("title", "")),
                "description": str(p.get("description", "")),
            }
        )

    data["pages"] = clean_add + data.get("pages", [])

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=0)

    return len(clean_add), skipped


class PromptGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Coloring Prompt Generator")
        self.state("zoomed")

        self.style = ttk.Style(self)
        self.base_bg = None
        self._setup_styles()

        self.categories = list_category_folders()

        self.category_var = tk.StringVar(
            value=self.categories[0] if self.categories else ""
        )
        self.count_var = tk.IntVar(value=4)

        self.data = (
            load_category_data(self.category_var.get())
            if self.category_var.get()
            else {}
        )

        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Items:").pack(side="left")

        ttk.Spinbox(top, from_=1, to=200, textvariable=self.count_var, width=6).pack(
            side="left", padx=(6, 12)
        )

        ttk.Button(top, text="Refresh", command=self.refresh_items).pack(
            side="left", padx=(0, 8)
        )

        ttk.Button(top, text="Save All", command=self.save_all_to_json).pack(side="left")

        ttk.Separator(top, orient="vertical").pack(side="left", fill="y", padx=10)

        self.counters_var = tk.StringVar(value="")
        counters = ttk.Label(top, textvariable=self.counters_var)
        counters.pack(side="right")

        ttk.Separator(self).pack(fill="x", padx=10, pady=(0, 10))

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        sidebar = ttk.Frame(container, padding=(0, 0, 10, 0))
        sidebar.pack(side="left", fill="y")

        ttk.Label(sidebar, text="Categories").pack(anchor="w", pady=(0, 6))

        list_wrap = ttk.Frame(sidebar)
        list_wrap.pack(fill="y", expand=True)

        self.cat_list = tk.Listbox(
            list_wrap,
            exportselection=False,
            activestyle="none",
        )
        cat_scroll = ttk.Scrollbar(list_wrap, orient="vertical", command=self.cat_list.yview)
        self.cat_list.configure(yscrollcommand=cat_scroll.set)

        self.cat_list.pack(side="left", fill="y", expand=True)
        cat_scroll.pack(side="right", fill="y")

        for c in self.categories:
            self.cat_list.insert("end", c)

        self.cat_list.bind("<<ListboxSelect>>", self.on_category_select)

        if self.categories:
            try:
                initial_idx = self.categories.index(self.category_var.get())
            except Exception:
                initial_idx = 0
                self.category_var.set(self.categories[0])
            self.cat_list.selection_set(initial_idx)
            self.cat_list.see(initial_idx)

        right = ttk.Frame(container)
        right.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(right, highlightthickness=0)
        scrollbar = ttk.Scrollbar(right, orient="vertical", command=self.canvas.yview)

        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw"
        )

        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width),
        )

        self.rows = []
        self.h1_vars = []
        self.id_vars = []
        self.prompt_vars = []
        self.desc_vars = []

        self.update_counters()
        self.refresh_items()

    def _setup_styles(self):
        base_bg = self.style.lookup("TFrame", "background")
        if not base_bg:
            base_bg = self.cget("bg")
        self.base_bg = base_bg

        self.style.configure(
            "Card.TFrame",
            relief="solid",
            borderwidth=1,
            background=base_bg,
        )

    def update_counters(self):
        data = self.data or {}
        category_keyword = self.category_var.get().strip()

        c = len(data.get("characters") or [])
        c_match = count_keyword_matches(data.get("characters") or [], category_keyword)
        a = len(data.get("actions") or [])
        e = len(data.get("environments") or [])
        total = calculate_total_combinations(data)
        total_fmt = f"{total:,}"

        self.counters_var.set(
            f"Characters: {c} ({c_match} matched)  Actions: {a}  Environments: {e}  Total: {total_fmt}"
        )

    def on_category_select(self, _event=None):
        sel = self.cat_list.curselection()
        if not sel:
            return
        idx = int(sel[0])
        if idx < 0 or idx >= len(self.categories):
            return
        new_cat = self.categories[idx]
        if new_cat == self.category_var.get():
            return
        self.category_var.set(new_cat)
        self.on_category_change()

    def on_category_change(self, _event=None):
        self.data = load_category_data(self.category_var.get())
        self.update_counters()
        self.refresh_items()

    def mark_row(self, idx):
        if idx >= len(self.rows):
            return
        try:
            _card, indicator = self.rows[idx]
            indicator.configure(bg=COPIED_BG)
        except Exception:
            pass

    def copy_id(self, idx):
        self.clipboard_clear()
        self.clipboard_append(self.id_vars[idx].get())
        self.update()
        self.mark_row(idx)

    def copy_prompt(self, idx):
        self.clipboard_clear()
        self.clipboard_append(self.prompt_vars[idx].get())
        self.update()
        self.mark_row(idx)

    def save_one_to_json(self, idx):
        category_name = self.category_var.get().strip()

        page = {
            "id": self.id_vars[idx].get(),
            "title": self.h1_vars[idx].get(),
            "description": self.desc_vars[idx].get(),
        }

        added, skipped = prepend_unique_pages_to_category_json(category_name, [page])
        self.mark_row(idx)

        messagebox.showinfo(
            "Saved",
            f"Added: {added}\nSkipped duplicates: {skipped}\nFile: {category_name}.json",
        )

    def save_all_to_json(self):
        category_name = self.category_var.get().strip()

        pages = [
            {
                "id": self.id_vars[i].get(),
                "title": self.h1_vars[i].get(),
                "description": self.desc_vars[i].get(),
            }
            for i in range(len(self.h1_vars))
        ]

        added, skipped = prepend_unique_pages_to_category_json(category_name, pages)

        messagebox.showinfo(
            "Saved",
            f"Added: {added}\nSkipped duplicates: {skipped}\nFile: {category_name}.json",
        )

    def refresh_items(self):
        for child in self.scrollable_frame.winfo_children():
            child.destroy()

        self.rows.clear()
        self.h1_vars.clear()
        self.id_vars.clear()
        self.prompt_vars.clear()
        self.desc_vars.clear()

        self.update_counters()

        try:
            count = int(self.count_var.get())
        except Exception:
            count = 10
            self.count_var.set(10)

        for i in range(count):
            item = generate_item(self.data)

            h1_var = tk.StringVar(value=item["h1"])
            id_var = tk.StringVar(value=item["id"])
            desc_var = tk.StringVar(value=item["page_description"])
            prompt_var = tk.StringVar(value=item["prompt"])

            self.h1_vars.append(h1_var)
            self.id_vars.append(id_var)
            self.desc_vars.append(desc_var)
            self.prompt_vars.append(prompt_var)

            card = ttk.Frame(self.scrollable_frame, style="Card.TFrame", padding=10)
            card.pack(fill="x", pady=6)

            card.grid_columnconfigure(2, weight=1)

            indicator = tk.Frame(card, width=6, bg=self.base_bg)
            indicator.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(0, 6))
            indicator.grid_propagate(False)

            idx_label = ttk.Label(card, text=f"{i+1}.", width=4, anchor="n")
            idx_label.grid(row=0, column=1, rowspan=2, sticky="nw", padx=(0, 10))

            text_block = ttk.Frame(card)
            text_block.grid(row=0, column=2, sticky="nsew")

            ttk.Label(
                text_block,
                textvariable=h1_var,
                wraplength=900,
                justify="left",
                anchor="w",
            ).pack(side="top", anchor="w", fill="x")

            ttk.Label(
                text_block,
                textvariable=id_var,
                wraplength=900,
                justify="left",
                anchor="w",
            ).pack(side="top", anchor="w", fill="x", pady=(4, 0))

            ttk.Label(
                text_block,
                textvariable=desc_var,
                wraplength=900,
                justify="left",
                anchor="w",
            ).pack(side="top", anchor="w", fill="x", pady=(6, 0))

            ttk.Label(
                text_block,
                textvariable=prompt_var,
                wraplength=900,
                justify="left",
                anchor="w",
            ).pack(side="top", anchor="w", fill="x", pady=(6, 0))

            btns = ttk.Frame(card)
            btns.grid(row=0, column=3, rowspan=2, sticky="ne", padx=(10, 0))

            ttk.Button(
                btns,
                text="Copy Id",
                command=lambda idx=i: self.copy_id(idx),
            ).pack(side="top", fill="x", pady=(0, 6))

            ttk.Button(
                btns,
                text="Copy Prompt",
                command=lambda idx=i: self.copy_prompt(idx),
            ).pack(side="top", fill="x", pady=(0, 6))

            ttk.Button(
                btns,
                text="Save",
                command=lambda idx=i: self.save_one_to_json(idx),
            ).pack(side="top", fill="x")

            self.rows.append((card, indicator))


if __name__ == "__main__":
    load_pools()
    PromptGUI().mainloop()