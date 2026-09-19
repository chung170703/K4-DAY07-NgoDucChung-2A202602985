"""
bench.py - Benchmark Retrieval Quality for Lab 07 (K4-L3A)

Chạy 5 câu hỏi benchmark trên kho tài liệu thư viện (data/thu-vien/)
với các chiến lược chunking khác nhau và chấm điểm độ chính xác (Precision@3).

Tuân thủ nghiêm ngặt kiến trúc Lab 07:
- Tái sử dụng các lớp Chunking từ `src.chunking` (FixedSizeChunker, SentenceChunker, HeadingChunker, RecursiveChunker).
- Đóng gói dữ liệu chuẩn vào `src.models.Document`.
- Nạp và quản lý vector embeddings qua `src.store.EmbeddingStore`.
- Thực thi truy vấn và tiền lọc qua phương thức chỉ định `store.search_with_filter()`.
- Hỗ trợ tác tử `src.agent.KnowledgeBaseAgent` khi bật cờ `--agent`.
- Hỗ trợ cờ `-o / --output` để lưu file trực tiếp bằng chuẩn mã hóa UTF-8, tránh lỗi vỡ font tiếng Việt do PowerShell redirection.

Cách chạy trên terminal của từng thành viên:
    python bench.py --strategy fixed -o ket_qua_tv1.txt      # Thành viên 1: Fixed-Size
    python bench.py --strategy sentence -o ket_qua_tv2.txt   # Thành viên 2: Sentence-Based
    python bench.py --strategy heading -o ket_qua_tv3.txt    # Thành viên 3: Heading-Based (K4-L3A)
    python bench.py --strategy recursive -o ket_qua_tv4.txt  # Thành viên 4: Recursive
"""

from __future__ import annotations

import argparse
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable

# Cấu hình UTF-8 cho console Windows để không bị lỗi font khi print
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Đảm bảo đường dẫn import src luôn hợp lệ từ thư mục gốc dự án
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models import Document
from src.store import EmbeddingStore
from src.chunking import (
    FixedSizeChunker,
    SentenceChunker,
    HeadingChunker,
    RecursiveChunker,
    compute_similarity,
)
from src.embeddings import MockEmbedder
from src.agent import KnowledgeBaseAgent


# ==============================================================================
# 1. 5 CÂU HỎI BENCHMARK & ĐÁP ÁN CHUẨN (GROUND TRUTH)
# ==============================================================================
BENCHMARK_QUERIES = [
    {
        "id": "Q1",
        "query": "Thời hạn mượn sách đối với sinh viên trong trường là bao nhiêu ngày và được gia hạn mấy lần?",
        "filter": {"audience": "student"},
        "expected_docs": ["huit-borrow-student"],
        "gold_answer": (
            "Sinh viên, học viên được mượn tối đa 3 cuốn trong thời hạn 10 ngày, "
            "được gia hạn 1 lần (10 ngày/lần). "
            "(Lưu ý: Nếu không có bộ lọc audience=student thì kết quả sẽ bị lẫn sang Giảng viên 180 ngày)."
        ),
        "note": "Câu hỏi bẫy bắt buộc dùng metadata filter {'audience': 'student'}",
    },
    {
        "id": "Q2",
        "query": "Sinh viên được mượn tối đa bao nhiêu cuốn giáo trình tại Phòng 111 và thời hạn mượn là bao lâu?",
        "filter": None,
        "expected_docs": ["library-room-111", "library-borrow-home"],
        "gold_answer": (
            "Mỗi bạn đọc được mượn tối đa 8 cuốn giáo trình tại Phòng 111 với thời hạn 90 ngày, "
            "được gia hạn 1 lần trong thời gian 30 ngày (tổng 120 ngày)."
        ),
        "note": "Tra cứu số liệu mượn giáo trình Bách Khoa Phòng 111",
    },
    {
        "id": "Q3",
        "query": "Tại Phòng 102 mượn sách tham khảo, số lượng mượn tối đa là bao nhiêu và được gia hạn mấy ngày?",
        "filter": None,
        "expected_docs": ["library-room-102", "library-borrow-home"],
        "gold_answer": (
            "Sinh viên được mượn tối đa 5 cuốn sách tham khảo tại Phòng 102, "
            "thời hạn mượn 30 ngày, được gia hạn 1 lần trong 7 ngày."
        ),
        "note": "Tra cứu quy định mượn sách tham khảo Phòng 102",
    },
    {
        "id": "Q4",
        "query": "Mức bồi thường khi làm mất tài liệu thư viện không còn phát hành trên thị trường được tính thế nào?",
        "filter": None,
        "expected_docs": ["library-lost-document"],
        "gold_answer": (
            "Tài liệu không phát hành trên thị trường: bồi thường bằng tiền gấp 03 lần giá bìa. "
            "Nếu tài liệu còn phát hành: bồi thường tài liệu mới tương đương cộng 20.000đ phí xử lý kỹ thuật."
        ),
        "note": "Tra cứu chính sách đền bù và xử phạt mất sách",
    },
    {
        "id": "Q5",
        "query": "Quy định mượn tài liệu in-house đọc tại chỗ cho phép mượn tối đa mấy cuốn và trả trước mấy giờ?",
        "filter": None,
        "expected_docs": ["library-inhouse-borrow"],
        "gold_answer": (
            "Mỗi lần bạn đọc được mượn tối đa 02 cuốn tài liệu in-house và phải trả lại "
            "tại quầy thủ thư Phòng 411 trước 17h30 cùng ngày."
        ),
        "note": "Tra cứu quy trình mượn đọc tại chỗ in-house",
    },
]


# ==============================================================================
# 2. VECTOR ENCODING (TF-IDF & MOCK BACKENDS)
# ==============================================================================
def tokenize(text: str) -> list[str]:
    """Tách từ tiếng Việt đơn giản cho mô hình TF-IDF."""
    return [w for w in re.findall(r"\w+", text.lower()) if len(w) > 1]


class TfidfEmbedder:
    """
    Tạo vector TF-IDF thuần Python không phụ thuộc thư viện nặng hay GPU.
    Cung cấp hàm callable `encode(text)` tương thích với EmbeddingStore(embedding_fn=...).
    """
    def __init__(self) -> None:
        self.vocab: dict[str, int] = {}
        self.idf: dict[str, float] = {}

    def fit(self, corpus: list[str]) -> None:
        doc_count = len(corpus)
        df: Counter = Counter()
        for doc in corpus:
            unique_words = set(tokenize(doc))
            for w in unique_words:
                df[w] += 1

        self.vocab = {w: idx for idx, (w, _) in enumerate(df.most_common(2000))}
        self.idf = {w: math.log((doc_count + 1) / (df[w] + 1)) + 1.0 for w in self.vocab}

    def encode(self, text: str) -> list[float]:
        vec = [0.0] * len(self.vocab)
        tokens = tokenize(text)
        if not tokens:
            return vec
        tf = Counter(tokens)
        for w, count in tf.items():
            if w in self.vocab:
                idx = self.vocab[w]
                vec[idx] = (count / len(tokens)) * self.idf[w]
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def __call__(self, text: str) -> list[float]:
        return self.encode(text)


# ==============================================================================
# 3. PARSER CHO TẬP TÀI LIỆU MARKDOWN
# ==============================================================================
def parse_markdown(file_path: Path) -> tuple[dict[str, str], str]:
    """Tách YAML frontmatter và phần nội dung (body) của file markdown."""
    text = file_path.read_text(encoding="utf-8")
    if "---" in text:
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm_raw = parts[1]
            body = parts[2].strip()
            fm = dict(re.findall(r"^(\w+):\s*(.+)$", fm_raw, re.M))
            return fm, body
    return {}, text.strip()


# ==============================================================================
# 4. BENCHMARK EXECUTION (SỬ DỤNG TRỰC TIẾP EmbeddingStore & search_with_filter)
# ==============================================================================
def run_benchmark(
    strategy_name: str,
    backend: str,
    data_path: Path,
    chunk_size: int = 700,
    overlap: int = 50,
    enable_agent: bool = False,
    output_path: Path | None = None,
) -> None:
    lines: list[str] = []

    def log(msg: str = "") -> None:
        print(msg)
        lines.append(msg)

    # 1. Khởi tạo đối tượng Chunker từ src.chunking
    if strategy_name == "fixed":
        chunker = FixedSizeChunker(chunk_size=chunk_size, overlap=overlap)
        display_name = f"Fixed-Size Chunker (chunk_size={chunk_size}, overlap={overlap})"
    elif strategy_name == "sentence":
        chunker = SentenceChunker(max_sentences_per_chunk=3)
        display_name = "Sentence-Based Chunker (max_sentences=3)"
    elif strategy_name == "heading":
        chunker = HeadingChunker(max_chunk_size=350)
        display_name = "Heading-Based Chunker (max_chunk_size=350) [K4 Requirement]"
    elif strategy_name == "recursive":
        r_size = chunk_size if chunk_size != 700 else 300
        chunker = RecursiveChunker(chunk_size=r_size)
        display_name = f"Recursive Chunker (chunk_size={r_size})"
    else:
        raise ValueError(f"Unknown strategy: {strategy_name}")

    log("=" * 80)
    log("LAB 07 RETRIEVAL BENCHMARK: THƯ VIỆN ĐẠI HỌC")
    log(f"Chiến lược kiểm thử : {display_name}")
    log(f"Embedding Backend   : {backend.upper()}")
    log(f"Thư mục tài liệu    : {data_path.resolve()}")
    log("=" * 80)

    if not data_path.exists():
        log(f"[LỖI] Không tìm thấy thư mục: {data_path}")
        sys.exit(1)

    # 2. Đọc và phân rã tài liệu thành danh sách Document
    md_files = sorted(data_path.glob("*.md"))
    documents: list[Document] = []

    for file_path in md_files:
        fm, body = parse_markdown(file_path)
        doc_id = fm.get("doc_id", file_path.stem)
        chunks = chunker.chunk(body)
        meta = dict(fm)
        meta["doc_id"] = doc_id

        for i, chunk in enumerate(chunks):
            documents.append(
                Document(
                    id=f"{doc_id}#{i}",
                    content=chunk,
                    metadata=meta,
                )
            )

    total_docs = len(md_files)
    total_chunks = len(documents)
    log(f"\n[1] Thống kê nạp dữ liệu (Data Ingestion):")
    log(f"  - Số file tài liệu: {total_docs} file (.md)")
    log(f"  - Tổng số chunk   : {total_chunks} chunks")
    log(f"  - Trung bình      : {total_chunks / max(1, total_docs):.1f} chunk/file\n")

    # 3. Chuẩn bị Embedding Function
    if backend == "tfidf":
        embedder = TfidfEmbedder()
        embedder.fit([d.content for d in documents])
        embedding_fn = embedder.encode
    else:
        mock_embedder = MockEmbedder(dim=64)
        embedding_fn = mock_embedder

    # 4. Nạp dữ liệu vào src.store.EmbeddingStore (ĐÚNG SPEC YÊU CẦU)
    store = EmbeddingStore(
        collection_name=f"benchmark_{strategy_name}",
        embedding_fn=embedding_fn,
    )
    store.add_documents(documents)
    log(f"  -> Đã nạp thành công {store.get_collection_size()} chunks vào EmbeddingStore.")

    # 5. Chạy 5 câu hỏi benchmark qua store.search_with_filter()
    log("\n[2] Chạy 5 câu hỏi Benchmark:")
    log("-" * 80)

    total_score = 0

    for idx, item in enumerate(BENCHMARK_QUERIES, start=1):
        qid = item["id"]
        qtext = item["query"]
        qfilter = item["filter"]
        expected_list = item["expected_docs"]
        gold = item["gold_answer"]

        log(f"\n>>> Câu {idx} [{qid}]: \"{qtext}\"")
        if qfilter:
            log(f"    [Bộ lọc Metadata]: {qfilter}")
        log(f"    [Đáp án chuẩn Gold]: {gold}")
        log(f"    [Tài liệu kỳ vọng]: {', '.join(expected_list)}")

        # GỌI TRỰC TIẾP PHƯƠNG THỨC CHỈ ĐỊNH CỦA LAB
        top3 = store.search_with_filter(
            query=qtext,
            top_k=3,
            metadata_filter=qfilter,
        )

        found_rank = None
        for rank, res in enumerate(top3, start=1):
            doc_id = res["metadata"].get("doc_id", res["id"].split("#")[0])
            if doc_id in expected_list:
                found_rank = rank
                break

        if found_rank == 1:
            qscore = 2
            status = "✅ XUẤT SẮC (Tài liệu đúng nằm ở Top 1)"
        elif found_rank in (2, 3):
            qscore = 1
            status = f"⚠️ TỐT (Tài liệu đúng nằm ở Top {found_rank})"
        else:
            qscore = 0
            status = "❌ THẤT BẠI (Không tìm thấy tài liệu đúng trong Top 3)"

        total_score += qscore

        log(f"    [Đánh giá Top-3]: Điểm: {qscore}/2  |  {status}")
        for r_idx, res in enumerate(top3, start=1):
            doc_id = res["metadata"].get("doc_id", res["id"].split("#")[0])
            marker = "🎯" if doc_id in expected_list else "  "
            preview = res["content"].strip().replace("\n", " ")[:95]
            log(f"      {marker} Top {r_idx}: [Score={res['score']:.3f}] ({res['id']}) - {preview}...")

        # Minh họa phản hồi từ Agent nếu được kích hoạt
        if enable_agent:
            def demo_llm(prompt: str) -> str:
                return f"[Agent Demo] Dựa vào [1], {gold[:80]}..."

            agent = KnowledgeBaseAgent(store=store, llm_fn=demo_llm)
            ans = agent.answer(qtext, top_k=3)
            log(f"    [Agent Response]: {ans}")

    log("\n" + "=" * 80)
    log(f"TỔNG KẾT ĐIỂM TRUY XUẤT (RETRIEVAL PRECISION): {total_score}/10 ĐIỂM")
    log("=" * 80)
    log("Thông tin để điền vào REPORT_NHOM.md (Mục 3):")
    log(f"- Chiến lược : {strategy_name.upper()} ({display_name})")
    log(f"- Tổng điểm  : {total_score}/10")
    log("=" * 80)

    # Ghi file với mã hóa UTF-8 chuẩn nếu được chỉ định
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n[OK] Đã lưu kết quả UTF-8 chuẩn vào: {output_path.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Lab 07 Retrieval Benchmark")
    parser.add_argument(
        "--strategy",
        choices=["fixed", "sentence", "heading", "recursive"],
        default="fixed",
        help="Chiến lược chunking (fixed, sentence, heading, recursive)",
    )
    parser.add_argument(
        "--backend",
        choices=["tfidf", "mock"],
        default="tfidf",
        help="Mô hình embedding (tfidf: ngữ nghĩa từ vựng tiếng Việt, mock: ngẫu nhiên)",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/thu-vien",
        help="Đường dẫn thư mục dữ liệu",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=700,
        help="Kích thước chunk (mặc định: 700)",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=50,
        help="Độ chồng lấp (mặc định: 50)",
    )
    parser.add_argument(
        "--agent",
        action="store_true",
        help="Chạy KnowledgeBaseAgent sinh câu trả lời kèm trích dẫn nguồn",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Đường dẫn file lưu kết quả trực tiếp với mã hóa UTF-8 (không bị lỗi font)",
    )
    args = parser.parse_args()

    run_benchmark(
        strategy_name=args.strategy,
        backend=args.backend,
        data_path=Path(args.data_dir),
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        enable_agent=args.agent,
        output_path=Path(args.output) if args.output else None,
    )
