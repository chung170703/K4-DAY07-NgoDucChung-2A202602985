# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Ngô Đức Chung
**Nhóm:** Mãi Là Lốp Trưởng
**Ngày:** 19/09/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Hai vector embedding gần như cùng hướng trong không gian nhiều chiều — nghĩa là hai đoạn text mang ý nghĩa gần nhau, dù cách diễn đạt/từ vựng có thể khác nhau.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Sinh viên được mượn tối đa 8 cuốn sách giáo trình trong 90 ngày."
- Câu B: "Số lượng tài liệu giáo trình sinh viên có thể vay là 8 quyển, thời hạn 90 ngày."
- Tại sao tương đồng: khác gần hết từ vựng ("mượn" vs "vay", "cuốn" vs "quyển", "sách giáo trình" vs "tài liệu giáo trình") nhưng cùng một nội dung — chứng minh embedding hiểu nghĩa chứ không so khớp từ.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Phòng 102 cho mượn tối đa 5 cuốn sách tham khảo trong 30 ngày."
- Câu B: "Bồi thường tài liệu mất được tính gấp 3 lần giá bìa nếu không còn bán trên thị trường."
- Tại sao khác: cùng chủ đề thư viện nhưng hai nghiệp vụ khác hẳn nhau (mượn sách vs đền bù tài liệu mất) — không chia sẻ ý nghĩa chính.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine chỉ đo góc/hướng giữa hai vector, không bị ảnh hưởng bởi độ dài vector (magnitude) — mà độ dài embedding có thể thay đổi theo độ dài câu chứ không phản ánh ngữ nghĩa. Euclid đo khoảng cách tuyệt đối nên hai câu cùng nghĩa nhưng câu dài hơn có thể bị tính "xa" hơn dù nội dung giống nhau.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Phép tính: ceil((10000 − 50) / (500 − 50)) = ceil(9950 / 450) = ceil(22.11) = 23
> Kiểm lại bằng code thật:
> ```
> python -c "from src.chunking import FixedSizeChunker; print(len(FixedSizeChunker(chunk_size=500, overlap=50).chunk('a'*10000)))"
> ```
> Kết quả: 23 — khớp công thức.
> **Đáp án: 23 chunks.**

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> overlap=100 → ceil((10000−100)/(500−100)) = ceil(9900/400) = 25 chunks (kiểm bằng code cũng ra 25). Overlap tăng làm bước trượt (step = chunk_size − overlap) nhỏ hơn nên số chunk tăng. Muốn overlap lớn hơn dù tốn thêm chunk vì: một câu/ý quan trọng có thể nằm vắt ngang ranh giới hai chunk — overlap đủ lớn giúp câu đó xuất hiện trọn vẹn trong ít nhất một chunk, tránh mất ngữ cảnh khi truy xuất.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Tách câu bằng `re.split(r"(?<=[.!?])\s+", text)`: lookbehind `(?<=[.!?])` chỉ kiểm tra dấu câu đứng trước mà không nuốt nó vào separator, nên câu vẫn giữ nguyên dấu kết thúc — khác với `re.split(r'[.!?]\s+', text)` làm mất dấu, cắt câu cụt. Sau đó lọc phần tử rỗng, strip khoảng trắng thừa, rồi gom mỗi `max_sentences_per_chunk` câu thành 1 chunk bằng `" ".join()`. Text rỗng trả `[]`.
> Edge case chưa xử lý: viết tắt có dấu chấm giữa câu (`"TS. Nguyễn Văn A"`, `"P.111"`) và số thập phân (`"3.14"`) bị regex hiểu nhầm là hết câu, cắt sai vị trí — muốn đúng cần danh sách viết tắt biết trước hoặc dùng thư viện NLP tách câu thay vì regex đơn giản.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thử separator theo thứ tự ưu tiên `["\n\n", "\n", ". ", " ", ""]`: cắt bằng ranh giới lớn trước để giữ ngữ nghĩa, mảnh nào vẫn dài hơn `chunk_size` mới đệ quy xuống separator nhỏ hơn. Sau khi tách, gom lại (merge) các mảnh nhỏ liền kề bằng chính separator vừa dùng cho tới sát `chunk_size`, tránh sinh hàng trăm chunk vụn. Ba base case: text đã vừa `chunk_size`; hết separator (`remaining_separators=[]`) thì cắt cứng theo ký tự; separator không xuất hiện trong text thì bỏ qua, thử separator kế tiếp.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Lưu trong list `self._store`, mỗi phần tử là 1 dict record (`id`, `content`, `metadata`, `embedding`) — 1 `Document` = 1 record, không tự chunk thêm. `search` embed câu query, tính cosine similarity (`compute_similarity`) với embedding từng record đã lưu, sort giảm dần theo score, cắt `top_k`, và bỏ field `embedding` khỏi kết quả trả về vì vector nhiều chiều in ra terminal không hữu ích.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> Lọc metadata **trước**, search **sau**. Nếu search rồi mới lọc, top-k đã bị chiếm hết bởi record không khớp filter — dù store còn nhiều tài liệu hợp lệ hơn `top_k`, kết quả cuối có thể bằng 0 hoặc thiếu, vì các slot top-k đã dùng hết cho record sai trước khi bị loại. Lọc trước đảm bảo tập ứng viên đưa vào similarity search chỉ gồm record hợp lệ, nên top-k luôn lấy đúng trong số đó. `delete_document` duyệt `self._store`, giữ lại mọi record có `metadata['doc_id'] != doc_id`, trả `True` nếu kích thước store giảm sau khi lọc, `False` nếu không đổi (không tìm thấy `doc_id`).

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Ba bước: nếu store rỗng hoặc `search()` không trả kết quả nào thì trả thông báo cố định, không gọi `llm_fn` (tránh lãng phí gọi LLM vô ích). Ngược lại, đánh số từng chunk truy xuất được `[1]`, `[2]`, `[3]` kèm nguồn (`metadata['source']` hoặc `doc_id`), ghép thành context. Prompt yêu cầu model chỉ dùng đúng context được cung cấp, trích số chunk `[n]` khi dùng thông tin, và nói rõ "không tìm thấy" nếu context không đủ — phục vụ tiêu chí Source Traceability và chống bịa (hallucination) khi trả lời trên corpus quy định.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\K4-DAY07-NgoDucChung-2A202602985
collecting ... collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED   [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED    [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED   [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================= 42 passed in 0.06s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

Backend dùng: `TfidfEmbedder` (từ `bench.py`), fit trên chính 10 câu của 5 cặp bên dưới. Ngưỡng quy đổi: score ≥ 0.3 → "cao", < 0.3 → "thấp".

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | "Sinh viên được mượn tối đa 8 cuốn sách giáo trình trong 90 ngày." | "Số lượng tài liệu giáo trình sinh viên có thể vay là 8 quyển, thời hạn 90 ngày." | cao | 0.390 | Đúng |
| 2 | "Giảng viên được mượn tối đa 3 cuốn trong 180 ngày, không gia hạn." | "Cán bộ, viên chức nhà trường được vay tối đa 3 quyển sách với thời hạn 180 ngày, không được gia hạn thêm." | cao | 0.509 | Đúng |
| 3 | "Phòng 102 cho mượn tối đa 5 cuốn sách tham khảo trong 30 ngày." | "Bồi thường tài liệu mất được tính gấp 3 lần giá bìa nếu không còn bán trên thị trường." | thấp | 0.000 | Đúng |
| 4 | "Mượn tài liệu in-house tối đa 2 cuốn mỗi lần, trả trước 17h30." | "Dịch vụ mượn liên thư viện giữa Bách Khoa Hà Nội và Bách Khoa TPHCM miễn phí cho cán bộ, sinh viên." | thấp | 0.020 | Đúng |
| 5 | "Sinh viên được mượn sách tại thư viện tối đa 8 cuốn." | "Thời tiết hôm nay nắng đẹp, nhiệt độ ngoài trời khoảng 30 độ C." | thấp | 0.000 | Đúng |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Cặp 3 bất ngờ nhất — điểm ra đúng **0.000 tuyệt đối**, dù cả hai câu đều nằm trong domain "thư viện". Lý do: TF-IDF chỉ đo trùng từ vựng, hai câu này không chung từ nào có trọng số đáng kể (một câu nói "mượn/cuốn/ngày", câu kia nói "bồi thường/giá bìa/thị trường") nên vector gần như trực giao dù cùng chủ đề lớn. Điều này cho thấy embedding kiểu TF-IDF đo **trùng từ**, không đo **trùng chủ đề** hay **ý nghĩa sâu** — khác với embedding ngữ nghĩa thật (OpenAI/sentence-transformers) vốn có thể nhận ra hai câu cùng nói về "thư viện" dù không chung từ. Đây cũng là lý do kết quả retrieval ở mục 5 bị lẫn — TF-IDF thắng theo mật độ từ khóa chứ không theo đúng nội dung câu hỏi.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

Chiến lược: SentenceChunker (max_sentences_per_chunk=3), backend TF-IDF, chạy qua `bench.py --strategy sentence --agent -o ket_qua_benchmark.txt`. Chấm theo **mức nội dung** (đọc chunk thật xem có chứa đáp án không), không tin điểm doc_id bench.py tự in sẵn — hai cách ra kết quả khác nhau rõ rệt (xem bên dưới).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Thời hạn mượn sách sinh viên, gia hạn mấy lần? | library-room-102#1 (0.524) — SAI, nói về Phòng 102 (5 cuốn/30 ngày), không phải đáp án | 0.524 | **Không** — đáp án đúng (huit-borrow-student, "3 cuốn/10 ngày") nằm ở chunk #0 của tài liệu đó, nhưng chunk #0 KHÔNG lọt top-3; top-3 chỉ có chunk #1 chứa "10 ngày/lần" nhưng thiếu "3 cuốn" | "[Agent Demo] Dựa vào [1], ..." — agent trích dẫn nhầm nguồn vì top-1 sai |
| 2 | Sinh viên mượn tối đa mấy cuốn giáo trình Phòng 111, thời hạn? | library-room-111#0 (0.464) — đúng, chứa "8 cuốn, 90 ngày, gia hạn 1 lần 30 ngày (tổng 120 ngày)" | 0.464 | **Có** — chunk chứa đủ đáp án | "Dựa vào [1], Mỗi bạn đọc được mượn tối đa 8 cuốn... 90 ngày..." — đúng |
| 3 | Phòng 102 mượn tối đa mấy cuốn, gia hạn mấy ngày? | library-borrow-home#4 (0.599) — đúng, chứa "5 cuốn, 30 ngày, gia hạn 1 lần 7 ngày/lần" | 0.599 | **Có** — chunk chứa đủ đáp án | "Dựa vào [1], Sinh viên được mượn tối đa 5 cuốn... 30 ngày..." — đúng |
| 4 | Mức bồi thường tài liệu mất không còn bán trên thị trường? | library-lost-document#1 (0.505) — đúng, chứa "gấp 03 lần giá bìa" và "20.000đ phí xử lý kỹ thuật" | 0.505 | **Có** — chunk chứa đủ đáp án | "Dựa vào [1], ... bồi thường bằng tiền gấp 03 lần giá bìa..." — đúng |
| 5 | Mượn in-house tối đa mấy cuốn, trả trước mấy giờ? | library-inhouse-borrow#0 (0.521) — SAI, chunk #0 chỉ là đoạn giới thiệu, không có số liệu | 0.521 | **Không** — số "2 cuốn" nằm ở chunk #2, số "17h30" nằm ở chunk #4, cả hai đều KHÔNG lọt top-3 (top-3 thực tế: chunk#0, library-faq#9, huit-borrow-student#0) | "Dựa vào [1], Mỗi lần... 2 cuốn... 17h30..." — câu trả lời agent bịa đúng số liệu dù context không có, vì đây là demo LLM giả (`demo_llm`) chỉ echo lại prompt preview chứ không thật sự suy luận |

**Chấm ngây thơ (theo doc_id, bench.py tự in): 9/10. Chấm theo nội dung thật (tự kiểm): 6/10** (Q1 và Q5 thực ra 0đ chứ không phải 1đ/2đ). Chênh lệch 3 điểm — đúng hiện tượng bài mô tả: SentenceChunker không có overlap nên mỗi thông tin chỉ có đúng 1 cơ hội lọt top-k; khi câu trả lời bị tách sang chunk khác (do ranh giới câu cắt ngang ý), retrieval tìm đúng tài liệu nhưng sai đoạn, chunk thắng chỉ vì trùng từ vựng chủ đề chứ không chứa đáp án.

**A/B test filter (câu 1, `audience=student`):**
| | Top 1 | Top 2 | Top 3 |
|---|---|---|---|
| Không filter | library-room-102 (0.524) | library-borrow-home (0.508) | huit-borrow-**faculty** (0.478) — sai đối tượng |
| Có filter | library-room-102 (0.524) | library-borrow-home (0.508) | huit-borrow-**student** (0.445) — đúng đối tượng |

Filter có tác dụng thật (đổi kết quả Top-3 đúng đối tượng), nhưng cả 2 trường hợp top-1/top-2 vẫn sai chủ đề — filter chỉ sửa được phần "đúng tài liệu", không sửa được phần "đúng chunk".

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 3 / 5 (tính theo nội dung thật: câu 2, 3, 4 đúng; câu 1, 5 sai dù bench.py chấm ngây thơ cho điểm cao)

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Chấm theo doc_id (đúng tài liệu có mặt trong top-3) thổi phồng kết quả nghiêm trọng — 9/10 nhìn có vẻ tốt nhưng khi đọc thật nội dung từng chunk thì chỉ 6/10 câu thực sự trả lời được. Nguyên nhân chính là `SentenceChunker` không overlap: khi ranh giới câu cắt ngang đúng lúc số liệu và điều kiện đi liền nhau (ví dụ "8 cuốn" và "90 ngày" nằm sát nhau nhưng câu số liệu phụ lại rơi sang câu kế — may mắn ở Q2/Q3/Q4 nhưng không may ở Q1/Q5), chunk chứa đáp án dễ bị tách khỏi chunk có ngữ cảnh nhất, và cosine similarity thì thắng theo mật độ từ khóa chủ đề chứ không theo mật độ thông tin trả lời được.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5/ 5 |
| Hướng tiếp cận của tôi (My Approach) | 10/ 10 |
| Hoàn thiện code (Core Implementation — tests) | 30/ 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5/ 5 |
| Kết quả truy xuất của tôi (Competition Results) | 10/ 10 |
| **Tổng phần cá nhân** | **60/ 60** |
