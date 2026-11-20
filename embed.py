import argparse
import os
from pathlib import Path

from settings import EMBED_MODEL, MODEL_FOLDER

ROOT = Path(__file__).resolve().parent
_MODEL = None


def _local_snapshot_dir(cache_dir):
    repo_dir = cache_dir / f"models--{EMBED_MODEL.replace('/', '--')}" / "snapshots"
    if not repo_dir.exists():
        return None
    snapshots = sorted(
        (p for p in repo_dir.iterdir() if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return snapshots[0] if snapshots else None


def get_model(download=False):
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    cache_dir = ROOT / MODEL_FOLDER
    cache_dir.mkdir(parents=True, exist_ok=True)

    if not download:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    from sentence_transformers import SentenceTransformer

    snapshot = None if download else _local_snapshot_dir(cache_dir)
    if snapshot is not None:
        _MODEL = SentenceTransformer(str(snapshot), local_files_only=True)
    else:
        _MODEL = SentenceTransformer(
            EMBED_MODEL,
            cache_folder=str(cache_dir),
            local_files_only=not download,
        )
    return _MODEL


def embed(text):
    return get_model(download=False).encode(text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="로컬 임베딩 모델 실행 및 준비")
    parser.add_argument(
        "--download",
        action="store_true",
        help="models 폴더에 임베딩 모델을 내려받습니다.",
    )
    args = parser.parse_args()

    sample = "나는 떡볶이를 좋아해"
    model = get_model(download=args.download)
    vector = model.encode(sample)
    print(f"문장: {sample}")
    print(f"벡터 길이: {len(vector)}")
    print(f"앞 5개 값: {vector[:5]}")
