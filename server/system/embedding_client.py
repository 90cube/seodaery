"""임베딩 클라이언트. CLIP(이미지) + BGE-M3(텍스트) 임베딩 생성.

CLIP은 이미지-텍스트 교차 검색, BGE-M3는 텍스트 전용 시맨틱 검색에 사용한다.
의존 패키지 미설치 시 해당 기능만 비활성화된다.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_clip_model = None
_clip_preprocess = None
_text_model = None
_available = {"clip": False, "text": False}


def init_clip() -> None:
    """CLIP 모델을 로드한다. 실패 시 이미지 검색만 비활성화."""
    global _clip_model, _clip_preprocess, _available
    try:
        import open_clip
        import torch  # noqa: F401

        model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="laion2b_s34b_b79k"
        )
        model.eval()
        _clip_model = model
        _clip_preprocess = preprocess
        _available["clip"] = True
        logger.info("CLIP 모델 로드 완료")
    except Exception as e:
        logger.warning("CLIP 로드 실패 (이미지 검색 비활성): %s", e)


def init_text_model() -> None:
    """BGE-M3 텍스트 임베딩 모델을 로드한다."""
    global _text_model, _available
    try:
        from sentence_transformers import SentenceTransformer

        _text_model = SentenceTransformer("BAAI/bge-m3")
        _available["text"] = True
        logger.info("BGE-M3 텍스트 임베딩 로드 완료")
    except Exception as e:
        logger.warning("BGE-M3 로드 실패 (텍스트 임베딩 비활성): %s", e)


def is_available(model_type: str = "clip") -> bool:
    """모델 사용 가능 여부를 반환한다."""
    return _available.get(model_type, False)


def embed_image(image_path: str) -> list[float] | None:
    """이미지를 CLIP 벡터(512차원)로 변환한다."""
    if not _available["clip"]:
        return None
    try:
        import torch
        from PIL import Image

        image = _clip_preprocess(Image.open(image_path)).unsqueeze(0)
        with torch.no_grad():
            features = _clip_model.encode_image(image)
            features /= features.norm(dim=-1, keepdim=True)
        return features[0].cpu().numpy().tolist()
    except Exception as e:
        logger.warning("이미지 임베딩 실패 %s: %s", image_path, e)
        return None


def embed_text(text: str) -> list[float] | None:
    """텍스트를 BGE-M3 벡터로 변환한다."""
    if not _available["text"]:
        return None
    try:
        vec = _text_model.encode(text, normalize_embeddings=True)
        return vec.tolist()
    except Exception as e:
        logger.warning("텍스트 임베딩 실패: %s", e)
        return None


def embed_text_clip(text: str) -> list[float] | None:
    """텍스트를 CLIP 벡터로 변환한다 (이미지-텍스트 교차 검색용)."""
    if not _available["clip"]:
        return None
    try:
        import torch
        import open_clip

        tokenizer = open_clip.get_tokenizer("ViT-B-32")
        tokens = tokenizer([text])
        with torch.no_grad():
            features = _clip_model.encode_text(tokens)
            features /= features.norm(dim=-1, keepdim=True)
        return features[0].cpu().numpy().tolist()
    except Exception as e:
        logger.warning("CLIP 텍스트 임베딩 실패: %s", e)
        return None
