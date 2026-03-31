"""서대리 지식 DB 에디터 — 글로벌 지식 데이터베이스 관리 GUI."""

import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

sys.path.insert(0, ".")  # 프로젝트 루트에서 서버 패키지 임포트 허용
from server.data.knowledge_store import (
    get_knowledge_db, init_knowledge_tables,
    insert_knowledge, update_knowledge, delete_knowledge,
    get_all_knowledge, get_categories,
)

# 기본 카테고리 프리셋
PRESET_CATEGORIES = [
    "character", "weapon", "item", "patch",
    "skill", "quest", "npc", "system",
]
TREE_COLUMNS = ("id", "category", "title", "description", "tags", "image")
TREE_HEADINGS = ("ID", "카테고리", "제목", "설명", "태그", "이미지")
TREE_WIDTHS = (40, 80, 120, 200, 100, 50)
DESC_TRUNCATE = 50


class KnowledgeEditor(tk.Tk):
    """지식 DB CRUD GUI."""

    def __init__(self) -> None:
        super().__init__()
        self.title("서대리 지식 DB 에디터")
        self.geometry("900x600")
        self.conn = get_knowledge_db()
        init_knowledge_tables(self.conn)
        self._build_form()
        self._build_buttons()
        self._build_search_and_tree()
        self._refresh_tree()

    # ── 폼 영역 ──────────────────────────────────────────
    def _build_form(self) -> None:
        frm = ttk.LabelFrame(self, text="항목 입력")
        frm.pack(fill="x", padx=8, pady=(8, 4))
        # 카테고리
        ttk.Label(frm, text="카테고리:").grid(row=0, column=0, sticky="e", padx=4, pady=2)
        self.cat_var = tk.StringVar()
        self.cat_cb = ttk.Combobox(frm, textvariable=self.cat_var, values=PRESET_CATEGORIES, width=30)
        self.cat_cb.grid(row=0, column=1, columnspan=2, sticky="w", pady=2)
        # 제목
        ttk.Label(frm, text="제목:").grid(row=1, column=0, sticky="e", padx=4, pady=2)
        self.title_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.title_var, width=50).grid(row=1, column=1, columnspan=2, sticky="w", pady=2)
        # 설명 (Text 위젯, 3줄)
        ttk.Label(frm, text="설명:").grid(row=2, column=0, sticky="ne", padx=4, pady=2)
        self.desc_text = tk.Text(frm, width=50, height=3)
        self.desc_text.grid(row=2, column=1, columnspan=2, sticky="w", pady=2)
        # 태그
        ttk.Label(frm, text="태그:").grid(row=3, column=0, sticky="e", padx=4, pady=2)
        self.tags_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.tags_var, width=50).grid(row=3, column=1, columnspan=2, sticky="w", pady=2)
        # 이미지 경로
        ttk.Label(frm, text="이미지:").grid(row=4, column=0, sticky="e", padx=4, pady=2)
        self.img_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.img_var, width=40).grid(row=4, column=1, sticky="w", pady=2)
        ttk.Button(frm, text="찾기", command=self._browse_image).grid(row=4, column=2, padx=4, pady=2)

    # ── 버튼 영역 ─────────────────────────────────────────
    def _build_buttons(self) -> None:
        frm = ttk.Frame(self)
        frm.pack(fill="x", padx=8, pady=4)
        ttk.Button(frm, text="추가", command=self._add).pack(side="left", padx=4)
        ttk.Button(frm, text="수정", command=self._edit).pack(side="left", padx=4)
        ttk.Button(frm, text="삭제", command=self._delete).pack(side="left", padx=4)

    # ── 검색 + 트리뷰 ────────────────────────────────────
    def _build_search_and_tree(self) -> None:
        frm = ttk.LabelFrame(self, text="목록")
        frm.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        # 검색
        sf = ttk.Frame(frm)
        sf.pack(fill="x", padx=4, pady=4)
        ttk.Label(sf, text="검색:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh_tree())
        ttk.Entry(sf, textvariable=self.search_var, width=30).pack(side="left", padx=4)
        # 트리뷰
        container = ttk.Frame(frm)
        container.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self.tree = ttk.Treeview(container, columns=TREE_COLUMNS, show="headings", selectmode="browse")
        for col, heading, width in zip(TREE_COLUMNS, TREE_HEADINGS, TREE_WIDTHS):
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, minwidth=width)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    # ── 트리뷰 갱신 ──────────────────────────────────────
    def _refresh_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        rows = get_all_knowledge(self.conn)
        query = self.search_var.get().strip().lower()
        for r in rows:
            if query:
                haystack = f"{r['category']} {r['title']} {r['description']} {r['tags']}".lower()
                if query not in haystack:
                    continue
            desc = r["description"][:DESC_TRUNCATE] + ("…" if len(r["description"]) > DESC_TRUNCATE else "")
            img_mark = "✓" if r.get("image_path") else ""
            self.tree.insert("", "end", iid=str(r["id"]), values=(
                r["id"], r["category"], r["title"], desc, r["tags"], img_mark,
            ))

    # ── 행 선택 → 폼 채우기 ──────────────────────────────
    def _on_select(self, _event: tk.Event) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        kid = int(sel[0])
        # DB에서 원본 데이터 조회
        row = self.conn.execute(
            "SELECT category, title, description, tags, image_path FROM knowledge WHERE id=?",
            (kid,),
        ).fetchone()
        if not row:
            return
        self.cat_var.set(row[0])
        self.title_var.set(row[1])
        self.desc_text.delete("1.0", "end")
        self.desc_text.insert("1.0", row[2])
        self.tags_var.set(row[3])
        self.img_var.set(row[4] or "")

    # ── 이미지 찾기 ──────────────────────────────────────
    def _browse_image(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("이미지 파일", "*.png *.jpg *.jpeg *.webp"), ("모든 파일", "*.*")],
        )
        if path:
            self.img_var.set(path)

    # ── 폼 값 읽기 ───────────────────────────────────────
    def _read_form(self) -> dict | None:
        cat = self.cat_var.get().strip()
        title = self.title_var.get().strip()
        if not cat or not title:
            messagebox.showwarning("입력 오류", "카테고리와 제목은 필수입니다.")
            return None
        return {
            "category": cat,
            "title": title,
            "description": self.desc_text.get("1.0", "end-1c").strip(),
            "tags": self.tags_var.get().strip(),
            "image_path": self.img_var.get().strip() or None,
        }

    # ── CRUD 동작 ─────────────────────────────────────────
    def _add(self) -> None:
        data = self._read_form()
        if not data:
            return
        insert_knowledge(self.conn, **data)
        self._refresh_tree()

    def _edit(self) -> None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("선택 오류", "수정할 항목을 선택하세요.")
            return
        data = self._read_form()
        if not data:
            return
        update_knowledge(self.conn, int(sel[0]), **data)
        self._refresh_tree()

    def _delete(self) -> None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("선택 오류", "삭제할 항목을 선택하세요.")
            return
        if not messagebox.askyesno("삭제 확인", "선택한 항목을 삭제하시겠습니까?"):
            return
        delete_knowledge(self.conn, int(sel[0]))
        self._refresh_tree()


if __name__ == "__main__":
    app = KnowledgeEditor()
    app.mainloop()
