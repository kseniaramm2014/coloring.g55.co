import tkinter as tk
from tkinter import ttk, messagebox
import random
import os
import re
import json
import base64
import urllib.request
import urllib.error

try:
    from PIL import Image
except Exception:
    Image = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, "app")
CATEGORIES_DIR = os.path.join(BASE_DIR, "categories")
STYLE_FILE = os.path.join(CATEGORIES_DIR, "style.txt")
ACTIONS_FILE = os.path.join(CATEGORIES_DIR, "actions.txt")
ENVIRONMENTS_FILE = os.path.join(CATEGORIES_DIR, "environments.txt")

POOL_FILES = {
    "intro": os.path.join(APP_DIR, "intro_pool.txt"),
    "usage": os.path.join(APP_DIR, "usage_pool.txt"),
    "ease": os.path.join(APP_DIR, "ease_pool.txt"),
    "benefit": os.path.join(APP_DIR, "benefit_pool.txt"),
}

POOLS = {k: [] for k in POOL_FILES.keys()}
LIST_NAMES = ["characters", "actions", "environments"]
COPIED_BG = "systemHighlight"

GEMINI_IMAGE_MODELS = ["gemini-3.1-flash-image", "gemini-2.5-flash-image"]
DEFAULT_GEMINI_IMAGE_MODEL = GEMINI_IMAGE_MODELS[0]
DEFAULT_ASPECT_RATIO = "2:3"
ONEBIT_THRESHOLD = 200


def list_category_folders():
    if not os.path.isdir(CATEGORIES_DIR):
        return []
    return sorted(
        d for d in os.listdir(CATEGORIES_DIR)
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
    text = " ".join(lines).strip()
    text = re.sub(r"\s{2,}", " ", text)
    return text


def load_shared_actions():
    return load_lines(ACTIONS_FILE)


def slugify(text):
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "coloring-page"


def normalize_category_key(text):
    return slugify((text or "").strip().lstrip("#"))


def load_category_environments(category_name):
    selected_key = normalize_category_key(category_name)
    shared_lines = []
    sections = {}
    active_key = None

    try:
        with open(ENVIRONMENTS_FILE, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue

                if line.startswith("#"):
                    active_key = normalize_category_key(line)
                    if active_key:
                        sections.setdefault(active_key, [])
                    continue

                if active_key is None:
                    shared_lines.append(line)
                elif active_key:
                    sections.setdefault(active_key, []).append(line)
    except Exception:
        return []

    if selected_key and sections.get(selected_key):
        return sections[selected_key]

    parent_keys = [
        key for key, lines in sections.items()
        if lines and selected_key.startswith(f"{key}-")
    ]
    if parent_keys:
        return sections[max(parent_keys, key=len)]

    return shared_lines


def load_shared_environments():
    return load_category_environments("")


def load_category_data(category_name):
    cat_dir = os.path.join(CATEGORIES_DIR, category_name)
    return {
        "characters": load_lines(os.path.join(cat_dir, "characters.txt")),
        "actions": load_shared_actions(),
        "environments": load_category_environments(category_name),
        "style": load_style(),
    }


SMALL_WORDS = {"a", "an", "the", "at", "in", "on", "to", "for", "with", "and", "or", "of", "as"}


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


def strip_leading_article(text):
    s = (text or "").strip()
    lower = s.lower()
    if lower.startswith("a "):
        return s[2:].lstrip()
    if lower.startswith("an "):
        return s[3:].lstrip()
    if lower.startswith("the "):
        return s[4:].lstrip()
    return s


def build_h1(parts):
    character = strip_leading_article(parts["character"])
    action = parts["action"].strip()
    env = parts["environment"].strip()
    base = re.sub(r"\s{2,}", " ", f"{character} {action} {env}").strip()
    return f"Free Printable {format_title(base)} Coloring Page for Kids"


def build_seo_base_for_slug(parts):
    character = strip_leading_article(parts["character"])
    action = parts["action"].strip()
    env = parts["environment"].strip()
    return re.sub(r"\s{2,}", " ", f"{character} {action} {env} coloring page").strip()


def build_id(parts):
    return slugify(build_seo_base_for_slug(parts))


def build_prompt(parts, style):
    core = f"{parts['character']} {parts['action']} {parts['environment']}"
    core = re.sub(r"\s{2,}", " ", core).strip()
    style = (style or "").strip().rstrip(".")
    return f"Coloring page on white background, {core}, {style}."


def _clean_sentence(s):
    s = re.sub(r"\s{2,}", " ", (s or "").strip()).strip(" ,")
    if not s:
        return ""
    if not s.endswith("."):
        s += "."
    return s


def load_pools():
    for key, path in POOL_FILES.items():
        POOLS[key] = load_lines(path)


def render_template(line, scene):
    return (line or "").replace("{scene}", scene)


def build_page_description(parts):
    scene = f"{parts['character'].strip()} {parts['action'].strip()} {parts['environment'].strip()}"
    scene = re.sub(r"\s{2,}", " ", scene).strip()

    patterns = [
        ("intro", "usage", "ease", "benefit"),
        ("intro", "usage", "benefit", "ease"),
        ("intro", "ease", "usage", "benefit"),
        ("intro", "ease", "benefit", "usage"),
        ("intro", "benefit", "usage", "ease"),
        ("intro", "benefit", "ease", "usage"),
    ]

    if any(not POOLS.get(k) for k in ("intro", "usage", "ease", "benefit")):
        return "Missing pool files."

    sentences = []
    for key in random.choice(patterns):
        sentences.append(_clean_sentence(render_template(random.choice(POOLS[key]), scene)))
    return " ".join(filter(None, sentences))


def generate_item(data):
    if not all(data.get(k) for k in LIST_NAMES) or not data.get("style"):
        parts = {"character": "", "action": "", "environment": ""}
        return {"parts": parts, "h1": "Missing files", "id": "missing-files", "prompt": "Missing files", "page_description": "Missing files"}

    if not all(POOLS.get(k) for k in ("intro", "usage", "ease", "benefit")):
        parts = {"character": "", "action": "", "environment": ""}
        return {"parts": parts, "h1": "Missing pool files", "id": "missing-pool-files", "prompt": "Missing pool files", "page_description": "Missing pool files"}

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
    return len(data.get("characters") or []) * len(data.get("actions") or []) * len(data.get("environments") or [])


def count_keyword_matches(lines, keyword):
    keyword = (keyword or "").strip().lower().replace("-", " ")
    if not keyword:
        return 0
    return sum(1 for line in lines or [] if keyword in (line or "").lower())


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
        if not pid or pid in existing_ids:
            skipped += 1
            continue
        existing_ids.add(pid)
        clean_add.append({"id": pid, "title": str(p.get("title", "")), "description": str(p.get("description", ""))})

    data["pages"] = clean_add + data.get("pages", [])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=0)
    return len(clean_add), skipped


def sanitize_filename(name):
    name = (name or "").strip()
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "image"


def image_output_path(category_name, page_id):
    return os.path.join(CATEGORIES_DIR, category_name, f"{sanitize_filename(page_id)}.png")


def temp_image_output_path(category_name, page_id, ext="jpg"):
    ext = (ext or "jpg").lower().strip().lstrip(".")
    if ext not in {"jpg", "jpeg", "png"}:
        ext = "jpg"
    return os.path.join(CATEGORIES_DIR, category_name, f"{sanitize_filename(page_id)}.__gemini_tmp.{ext}")


def image_is_1bit_png(path):
    if Image is None or not os.path.isfile(path):
        return False
    try:
        with Image.open(path) as im:
            return im.format == "PNG" and im.mode == "1"
    except Exception:
        return False


def validate_image(path):
    if Image is None:
        return False, "pillow_not_installed"
    if not os.path.isfile(path):
        return False, "missing_image"
    try:
        with Image.open(path) as im:
            if im.format not in {"JPEG", "PNG"}:
                return False, f"unsupported_image_format_{im.format}"
            im.verify()
        return True, ""
    except Exception as exc:
        return False, str(exc)


def detect_image_ext_from_bytes(image_bytes, fallback="jpg"):
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "jpg"
    return fallback


def convert_image_to_1bit_png(src_path, final_png_path=None, threshold=ONEBIT_THRESHOLD):
    if Image is None:
        return {"ok": False, "error": "pillow_not_installed"}
    if not os.path.isfile(src_path):
        return {"ok": False, "error": "missing_input", "path": src_path}

    if final_png_path is None:
        final_png_path = os.path.splitext(src_path)[0] + ".png"

    if os.path.abspath(src_path) == os.path.abspath(final_png_path) and image_is_1bit_png(src_path):
        return {"ok": True, "skipped": True, "path": final_png_path}

    try:
        with Image.open(src_path) as src:
            src = src.convert("RGBA")
            alpha = src.getchannel("A")
            white_bg = Image.new("RGBA", src.size, (255, 255, 255, 255))
            white_bg.paste(src, mask=alpha)
            gray = white_bg.convert("L")
            bw = gray.point(lambda px: 255 if px >= threshold else 0, mode="1")
            os.makedirs(os.path.dirname(final_png_path), exist_ok=True)
            bw.save(final_png_path, format="PNG", optimize=True)

        if os.path.abspath(src_path) != os.path.abspath(final_png_path):
            try:
                os.remove(src_path)
            except Exception:
                pass

        return {"ok": True, "skipped": False, "path": final_png_path}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "path": src_path, "final_path": final_png_path}


def gemini_generate_image(api_key, prompt, out_path, aspect_ratio=DEFAULT_ASPECT_RATIO, model_name=DEFAULT_GEMINI_IMAGE_MODEL):
    api_key = (api_key or "").strip()
    prompt = (prompt or "").strip()
    aspect_ratio = (aspect_ratio or DEFAULT_ASPECT_RATIO).strip()
    model_name = (model_name or DEFAULT_GEMINI_IMAGE_MODEL).strip()
    if model_name not in GEMINI_IMAGE_MODELS:
        model_name = DEFAULT_GEMINI_IMAGE_MODEL

    if not api_key:
        return {"ok": False, "error": "missing_api_key"}
    if not prompt:
        return {"ok": False, "error": "missing_prompt"}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["Image"],
            "imageConfig": {"aspectRatio": aspect_ratio},
        },
    }

    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as res:
            raw = res.read().decode("utf-8", errors="replace")
            status = int(getattr(res, "status", 200))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "error": "http_error", "status": exc.code, "detail": detail}
    except Exception as exc:
        return {"ok": False, "error": "request_error", "detail": str(exc)}

    if status < 200 or status >= 300:
        return {"ok": False, "error": "http_error", "status": status, "detail": raw}

    try:
        data = json.loads(raw)
    except Exception:
        return {"ok": False, "error": "bad_json", "detail": raw}

    image_b64 = None
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    for part in parts:
        inline_data = part.get("inlineData") or part.get("inline_data") or {}
        if inline_data.get("data"):
            image_b64 = inline_data.get("data")
            break

    if not image_b64:
        return {"ok": False, "error": "no_image_in_response", "detail": data}

    try:
        image_bytes = base64.b64decode(image_b64, validate=True)
    except Exception:
        return {"ok": False, "error": "base64_decode_failed"}

    final_png_path = out_path
    src_ext = detect_image_ext_from_bytes(image_bytes, fallback="jpg")
    src_path = out_path if src_ext == "png" else f"{os.path.splitext(out_path)[0]}.__gemini_tmp.{src_ext}"

    try:
        os.makedirs(os.path.dirname(src_path), exist_ok=True)
        with open(src_path, "wb") as f:
            f.write(image_bytes)
    except Exception as exc:
        return {"ok": False, "error": "write_failed", "path": src_path, "detail": str(exc)}

    ok, detail = validate_image(src_path)
    if not ok:
        try:
            os.remove(src_path)
        except Exception:
            pass
        return {"ok": False, "error": "invalid_image_output", "detail": detail}

    onebit = convert_image_to_1bit_png(src_path, final_png_path, ONEBIT_THRESHOLD)
    if not onebit.get("ok"):
        return {"ok": False, "error": "onebit_failed", "detail": onebit}

    return {"ok": True, "path": final_png_path, "source_format": src_ext, "onebit": onebit}


def generate_image_for_page(category_name, page_id, prompt, api_key, aspect_ratio, model_name, skip_existing=True):
    out_path = image_output_path(category_name, page_id)

    if skip_existing and os.path.isfile(out_path) and os.path.getsize(out_path) > 0:
        ok, detail = validate_image(out_path)
        if not ok:
            return {"ok": False, "error": "existing_image_invalid", "detail": detail, "path": out_path}
        onebit = convert_image_to_1bit_png(out_path, out_path, ONEBIT_THRESHOLD)
        if not onebit.get("ok"):
            return {"ok": False, "error": "onebit_failed", "detail": onebit, "path": out_path}
        return {"ok": True, "path": out_path, "skipped_existing": True, "onebit": onebit}

    return gemini_generate_image(api_key, prompt, out_path, aspect_ratio, model_name)


class PromptGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Coloring Prompt Generator")
        self.state("zoomed")

        self.style = ttk.Style(self)
        self.base_bg = None
        self._setup_styles()

        self.categories = list_category_folders()
        self.category_var = tk.StringVar(value=self.categories[0] if self.categories else "")
        self.count_var = tk.IntVar(value=5)
        self.model_var = tk.StringVar(value=DEFAULT_GEMINI_IMAGE_MODEL)
        self.aspect_ratio_var = tk.StringVar(value=DEFAULT_ASPECT_RATIO)
        self.data = load_category_data(self.category_var.get()) if self.category_var.get() else {}

        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Items:").pack(side="left")
        ttk.Spinbox(top, from_=1, to=200, textvariable=self.count_var, width=6).pack(side="left", padx=(6, 12))
        ttk.Button(top, text="Refresh", command=self.refresh_items).pack(side="left", padx=(0, 8))
        ttk.Button(top, text="Save All", command=self.save_all_to_json).pack(side="left", padx=(0, 8))
        ttk.Button(top, text="Generate Images + Save All", command=self.generate_images_and_save_all).pack(side="left")

        ttk.Label(top, text="Aspect:").pack(side="left", padx=(12, 4))
        ttk.Entry(top, textvariable=self.aspect_ratio_var, width=6).pack(side="left")
        ttk.Label(top, text="Model:").pack(side="left", padx=(12, 4))
        self.model_combo = ttk.Combobox(top, textvariable=self.model_var, values=GEMINI_IMAGE_MODELS, width=24, state="readonly")
        self.model_combo.pack(side="left")

        ttk.Separator(top, orient="vertical").pack(side="left", fill="y", padx=10)
        self.counters_var = tk.StringVar(value="")
        ttk.Label(top, textvariable=self.counters_var).pack(side="right")

        ttk.Separator(self).pack(fill="x", padx=10, pady=(0, 10))

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        sidebar = ttk.Frame(container, padding=(0, 0, 10, 0))
        sidebar.pack(side="left", fill="y")
        ttk.Label(sidebar, text="Categories").pack(anchor="w", pady=(0, 6))

        list_wrap = ttk.Frame(sidebar)
        list_wrap.pack(fill="y", expand=True)
        self.cat_list = tk.Listbox(list_wrap, exportselection=False, activestyle="none")
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
        self.scrollable_frame.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))

        self.rows = []
        self.h1_vars = []
        self.id_vars = []
        self.prompt_vars = []
        self.desc_vars = []

        self.update_counters()
        self.refresh_items()

    def _setup_styles(self):
        base_bg = self.style.lookup("TFrame", "background") or self.cget("bg")
        self.base_bg = base_bg
        self.style.configure("Card.TFrame", relief="solid", borderwidth=1, background=base_bg)

    def update_counters(self):
        data = self.data or {}
        category_keyword = self.category_var.get().strip()
        c = len(data.get("characters") or [])
        c_match = count_keyword_matches(data.get("characters") or [], category_keyword)
        a = len(data.get("actions") or [])
        e = len(data.get("environments") or [])
        total = calculate_total_combinations(data)
        self.counters_var.set(f"Characters: {c} ({c_match} matched)  Actions: {a}  Environments: {e}  Total: {total:,}")

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
        category_name = self.category_var.get().strip()
        page = {"id": self.id_vars[idx].get(), "title": self.h1_vars[idx].get(), "description": self.desc_vars[idx].get()}
        added, skipped = prepend_unique_pages_to_category_json(category_name, [page])
        self.mark_row(idx)
        messagebox.showinfo("Copied and Saved", f"Prompt copied to clipboard.\nAdded: {added}\nSkipped duplicates: {skipped}\nFile: {category_name}.json")

    def save_all_to_json(self):
        category_name = self.category_var.get().strip()
        pages = [
            {"id": self.id_vars[i].get(), "title": self.h1_vars[i].get(), "description": self.desc_vars[i].get()}
            for i in range(len(self.h1_vars))
        ]
        added, skipped = prepend_unique_pages_to_category_json(category_name, pages)
        messagebox.showinfo("Saved", f"Added: {added}\nSkipped duplicates: {skipped}\nFile: {category_name}.json")

    def _page_from_row(self, idx):
        return {
            "id": self.id_vars[idx].get(),
            "title": self.h1_vars[idx].get(),
            "description": self.desc_vars[idx].get(),
            "prompt": self.prompt_vars[idx].get(),
        }

    def generate_image_for_row(self, idx, save_page=True, show_done=True):
        category_name = self.category_var.get().strip()
        page = self._page_from_row(idx)
        api_key = os.getenv("GEMINI_API_KEY", "")
        aspect_ratio = self.aspect_ratio_var.get().strip() or DEFAULT_ASPECT_RATIO
        model_name = self.model_var.get().strip() or DEFAULT_GEMINI_IMAGE_MODEL

        if not category_name:
            if show_done:
                messagebox.showerror("Missing Category", "Select a category first.")
            return False, {"error": "missing_category"}

        result = generate_image_for_page(
            category_name=category_name,
            page_id=page["id"],
            prompt=page["prompt"],
            api_key=api_key,
            aspect_ratio=aspect_ratio,
            model_name=model_name,
            skip_existing=True,
        )

        if not result.get("ok"):
            if show_done:
                messagebox.showerror("Image Generation Failed", json.dumps(result, ensure_ascii=False, indent=2))
            return False, result

        added = 0
        skipped = 0
        if save_page:
            added, skipped = prepend_unique_pages_to_category_json(category_name, [page])

        self.mark_row(idx)
        if show_done:
            messagebox.showinfo("Image Generated", f"Image: {result.get('path', '')}\nAdded: {added}\nSkipped duplicates: {skipped}")
        return True, {"image": result, "added": added, "skipped": skipped}

    def generate_images_and_save_all(self):
        category_name = self.category_var.get().strip()
        if not category_name:
            messagebox.showerror("Missing Category", "Select a category first.")
            return

        ok_count = 0
        failed = []
        pages_to_add = []
        for i in range(len(self.h1_vars)):
            ok, result = self.generate_image_for_row(i, save_page=False, show_done=False)
            if ok:
                ok_count += 1
                pages_to_add.append(self._page_from_row(i))
            else:
                failed.append({"row": i + 1, "detail": result})

        added, skipped = prepend_unique_pages_to_category_json(category_name, pages_to_add)
        message = f"Images generated: {ok_count}\nPages added: {added}\nSkipped duplicates: {skipped}\nFailed: {len(failed)}\nFile: {category_name}.json"
        if failed:
            message += "\n\nFirst failures:\n" + json.dumps(failed[:3], ensure_ascii=False, indent=2)
        messagebox.showinfo("Generate Images + Save All", message)

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

            ttk.Label(card, text=f"{i+1}.", width=4, anchor="n").grid(row=0, column=1, rowspan=2, sticky="nw", padx=(0, 10))

            text_block = ttk.Frame(card)
            text_block.grid(row=0, column=2, sticky="nsew")
            ttk.Label(text_block, textvariable=h1_var, wraplength=900, justify="left", anchor="w").pack(side="top", anchor="w", fill="x")
            ttk.Label(text_block, textvariable=id_var, wraplength=900, justify="left", anchor="w").pack(side="top", anchor="w", fill="x", pady=(4, 0))
            ttk.Label(text_block, textvariable=desc_var, wraplength=900, justify="left", anchor="w").pack(side="top", anchor="w", fill="x", pady=(6, 0))
            ttk.Label(text_block, textvariable=prompt_var, wraplength=900, justify="left", anchor="w").pack(side="top", anchor="w", fill="x", pady=(6, 0))

            btns = ttk.Frame(card)
            btns.grid(row=0, column=3, rowspan=2, sticky="ne", padx=(10, 0))
            ttk.Button(btns, text="Copy Id", command=lambda idx=i: self.copy_id(idx)).pack(side="top", fill="x", pady=(0, 6))
            ttk.Button(btns, text="Copy Prompt", command=lambda idx=i: self.copy_prompt(idx)).pack(side="top", fill="x", pady=(0, 6))
            ttk.Button(btns, text="Generate Image", command=lambda idx=i: self.generate_image_for_row(idx)).pack(side="top", fill="x", pady=(0, 6))

            self.rows.append((card, indicator))


if __name__ == "__main__":
    load_pools()
    PromptGUI().mainloop()
