"""서대리 에셋 DB 에디터 — 에셋 등록·삭제, 태그 관리, 트리뷰 조회 GUI."""

import sys
import tkinter as tk
from tkinter import messagebox, ttk

sys.path.insert(0, ".")
from server.data.asset_store import (
    delete_asset, get_all_assets, get_asset_tags, get_assets_db,
    init_asset_tables, insert_asset, link_tag, unlink_tag,
)
from server.data.tag_store import (
    ensure_tag, get_all_tag_types, get_tag_id, get_tags_by_type, seed_tag_types,
)

WINDOW_TITLE = "서대리 에셋 DB 에디터"
WINDOW_SIZE = "1000x650"
SEARCH_TYPES = ["캐릭터", "무기", "아이템"]
TREE_COLUMNS = ("ID", "타입", "폴더번호", "파일명", "태그수")
COL_WIDTHS = {"ID": 50, "타입": 80, "폴더번호": 100, "파일명": 350, "태그수": 60}
CENTER_COLS = {"ID", "타입", "태그수"}


class AssetEditor(tk.Tk):
    """에셋 에디터 메인 윈도우."""

    def __init__(self) -> None:
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)
        self.conn = get_assets_db()
        init_asset_tables(self.conn)
        seed_tag_types(self.conn)
        self.selected_asset_id: int | None = None
        self._build_form()
        self._build_tag_section()
        self._build_buttons()
        self._build_treeview()
        self._refresh()

    def _build_form(self) -> None:
        """에셋 입력 폼을 구성한다."""
        frm = ttk.LabelFrame(self, text="에셋 정보", padding=8)
        frm.pack(fill=tk.X, padx=8, pady=(8, 4))
        ttk.Label(frm, text="타입").grid(row=0, column=0, sticky=tk.W)
        self.search_type_cb = ttk.Combobox(
            frm, values=SEARCH_TYPES, state="readonly", width=10)
        self.search_type_cb.grid(row=0, column=1, sticky=tk.W, padx=4)
        self.search_type_cb.current(0)
        ttk.Label(frm, text="폴더번호").grid(row=0, column=2, sticky=tk.W)
        self.folder_number_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.folder_number_var, width=12).grid(
            row=0, column=3, padx=4)
        ttk.Label(frm, text="파일명").grid(row=0, column=4, sticky=tk.W)
        self.file_name_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.file_name_var, width=40).grid(
            row=0, column=5, sticky=tk.EW, padx=4)
        frm.columnconfigure(5, weight=1)

    def _build_tag_section(self) -> None:
        """태그 추가·삭제 영역을 구성한다."""
        frm = ttk.LabelFrame(self, text="태그", padding=8)
        frm.pack(fill=tk.X, padx=8, pady=4)
        tag_types = [t["type_name"] for t in get_all_tag_types(self.conn)]
        ttk.Label(frm, text="태그타입").grid(row=0, column=0, sticky=tk.W)
        self.tag_type_cb = ttk.Combobox(
            frm, values=tag_types, state="readonly", width=18)
        self.tag_type_cb.grid(row=0, column=1, padx=4)
        if tag_types:
            self.tag_type_cb.current(0)
        ttk.Label(frm, text="값").grid(row=0, column=2, sticky=tk.W)
        self.tag_value_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.tag_value_var, width=20).grid(
            row=0, column=3, padx=4)
        ttk.Button(frm, text="태그 추가", command=self._add_tag).grid(
            row=0, column=4, padx=4)
        self.tag_listbox = tk.Listbox(frm, height=4, width=50)
        self.tag_listbox.grid(row=1, column=0, columnspan=4, sticky=tk.EW, pady=4)
        ttk.Button(frm, text="태그 삭제", command=self._delete_tag).grid(
            row=1, column=4, padx=4)
        frm.columnconfigure(3, weight=1)

    def _build_buttons(self) -> None:
        """에셋 추가·삭제 버튼을 구성한다."""
        frm = ttk.Frame(self, padding=4)
        frm.pack(fill=tk.X, padx=8)
        ttk.Button(frm, text="에셋 추가", command=self._add_asset).pack(
            side=tk.LEFT, padx=4)
        ttk.Button(frm, text="에셋 삭제", command=self._delete_asset).pack(
            side=tk.LEFT, padx=4)

    def _build_treeview(self) -> None:
        """에셋 목록 트리뷰를 구성한다."""
        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))
        self.tree = ttk.Treeview(
            frm, columns=TREE_COLUMNS, show="headings", height=12)
        for col in TREE_COLUMNS:
            self.tree.heading(col, text=col)
            anchor = tk.CENTER if col in CENTER_COLS else tk.W
            self.tree.column(col, width=COL_WIDTHS[col], anchor=anchor)
        scroll = ttk.Scrollbar(frm, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    # ── 콜백 ───────────────────────────────────────────────

    def _add_asset(self) -> None:
        """새 에셋을 DB에 추가한다."""
        self.selected_asset_id = insert_asset(
            self.conn, self.search_type_cb.get(),
            self.folder_number_var.get(), file_name=self.file_name_var.get())
        self._refresh()

    def _delete_asset(self) -> None:
        """선택된 에셋을 삭제한다."""
        if self.selected_asset_id is None:
            messagebox.showwarning("알림", "에셋을 선택하세요.")
            return
        delete_asset(self.conn, self.selected_asset_id)
        self.selected_asset_id = None
        self._clear_form()
        self._refresh()

    def _add_tag(self) -> None:
        """선택된 에셋에 태그를 추가한다."""
        if self.selected_asset_id is None:
            messagebox.showwarning("알림", "에셋을 먼저 선택하세요.")
            return
        t_val = self.tag_value_var.get().strip()
        if not t_val:
            return
        tag_id = ensure_tag(self.conn, self.tag_type_cb.get(), t_val)
        link_tag(self.conn, self.selected_asset_id, tag_id)
        self._load_tags()
        self._refresh()

    def _delete_tag(self) -> None:
        """선택된 태그를 에셋에서 해제한다."""
        sel = self.tag_listbox.curselection()
        if not sel or self.selected_asset_id is None:
            return
        t_type, t_val = self.tag_listbox.get(sel[0]).split(":", 1)
        tag_id = get_tag_id(self.conn, t_type.strip(), t_val.strip())
        if tag_id is not None:
            unlink_tag(self.conn, self.selected_asset_id, tag_id)
        self._load_tags()
        self._refresh()

    def _on_select(self, _event: tk.Event) -> None:
        """트리뷰 행 선택 시 폼과 태그 리스트를 채운다."""
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.selected_asset_id = int(vals[0])
        self.search_type_cb.set(vals[1])
        self.folder_number_var.set(vals[2])
        self.file_name_var.set(vals[3])
        self._load_tags()

    # ── 데이터 로드 ────────────────────────────────────────

    def _refresh(self) -> None:
        """전체 에셋을 트리뷰에 다시 로드한다."""
        self.tree.delete(*self.tree.get_children())
        for a in get_all_assets(self.conn):
            tag_count = len(get_asset_tags(self.conn, a["asset_id"]))
            self.tree.insert("", tk.END, values=(
                a["asset_id"], a["search_type"],
                a["folder_number"], a["file_name"], tag_count))

    def _load_tags(self) -> None:
        """선택된 에셋의 태그를 리스트박스에 로드한다."""
        self.tag_listbox.delete(0, tk.END)
        if self.selected_asset_id is None:
            return
        for t in get_asset_tags(self.conn, self.selected_asset_id):
            self.tag_listbox.insert(tk.END, f"{t['type_name']}: {t['value']}")

    def _clear_form(self) -> None:
        """입력 폼을 초기화한다."""
        self.folder_number_var.set("")
        self.file_name_var.set("")
        self.tag_listbox.delete(0, tk.END)


if __name__ == "__main__":
    AssetEditor().mainloop()
