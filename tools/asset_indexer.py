"""에셋 전체 인덱싱 도구. 수동 실행용.

전체 에셋을 순회하며 CLIP/BGE-M3 임베딩을 생성하고
벡터 저장소에 기록한다. 이미 인덱싱된 에셋은 건너뛴다.

사용법:
    python -m tools.asset_indexer
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.data.asset_store import get_all_assets, get_assets_db, init_asset_tables
from server.system.embedding_client import (
    embed_image,
    embed_text,
    init_clip,
    init_text_model,
    is_available,
)
from server.system.vector_store import (
    get_vector_db,
    init_vector_tables,
    is_indexed,
    store_embedding,
)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def _build_tag_text(asset: dict) -> str:
    """에셋 태그를 텍스트 임베딩용 문자열로 조합한다."""
    tags = asset.get("tags", [])
    if not tags:
        return ""
    parts = [f"{t['type_name']}:{t['value']}" for t in tags]
    return " ".join(parts)


def index_all() -> None:
    """전체 에셋을 인덱싱한다."""
    print("=== 에셋 전체 인덱싱 ===")
    print("모델 로딩 중...")
    init_clip()
    init_text_model()

    clip_ok = is_available("clip")
    text_ok = is_available("text")
    print(f"  CLIP: {'활성' if clip_ok else '비활성'}")
    print(f"  BGE-M3: {'활성' if text_ok else '비활성'}")

    if not clip_ok and not text_ok:
        print("활성화된 모델 없음 — 종료")
        return

    adb = get_assets_db()
    init_asset_tables(adb)
    assets = get_all_assets(adb)
    adb.close()
    print(f"에셋 {len(assets)}건 발견")

    vdb = get_vector_db()
    init_vector_tables(vdb)

    indexed = 0
    skipped = 0
    errors = 0
    start = time.time()

    for asset in assets:
        aid = asset["asset_id"]
        fname = asset.get("file_name", "")
        fpath = asset.get("folder_path", "")

        # CLIP 이미지 임베딩
        if clip_ok and not is_indexed(vdb, aid, "clip"):
            full = Path(fpath) / fname if fpath and fname else None
            if full and full.exists() and full.suffix.lower() in IMAGE_EXTENSIONS:
                vec = embed_image(str(full))
                if vec:
                    store_embedding(vdb, aid, "clip", vec, str(full))
                    indexed += 1
                else:
                    errors += 1
            else:
                skipped += 1
        else:
            skipped += 1

        # BGE-M3 텍스트 임베딩 (태그 기반)
        if text_ok and not is_indexed(vdb, aid, "text"):
            tag_text = _build_tag_text(asset)
            if tag_text:
                vec = embed_text(tag_text)
                if vec:
                    store_embedding(vdb, aid, "text", vec)
                    indexed += 1
                else:
                    errors += 1

    vdb.close()
    elapsed = time.time() - start
    print(f"완료: {indexed}건 인덱싱, {skipped}건 건너뜀, "
          f"{errors}건 실패 ({elapsed:.1f}초)")


if __name__ == "__main__":
    index_all()
