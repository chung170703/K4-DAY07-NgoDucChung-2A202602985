# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** Mãi Là Lốp Trưởng  
**Thành viên:**
- Tạ Hoàng Vinh — MSSV: 2A202602543 (Report & Demo Lead, Fixed-Size Chunking: chunk_size=700, overlap=50)
- Ngô Đức Chung — MSSV: 2A202602985 (Sentence-Based Chunking: max_sentences=3)
- Bùi Tiến Cường — MSSV: 2A202602539 (Heading-Based Chunking: max_chunk_size=350 — Chuẩn K4-L3A)
- Phạm Quang Huy — MSSV: 2A202602900 (Recursive Chunking: chunk_size=300)

**Ngày:** 19/09/2026  

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Quy định và Dịch vụ Thư viện Đại học (Đại học Bách Khoa Hà Nội & ĐH Công Thương TP.HCM - HUIT)

**Tại sao nhóm chọn chủ đề này?**
> Tài liệu quy định và thủ tục thư viện đại học có cấu trúc văn bản pháp quy rõ ràng, chứa nhiều điều khoản định lượng khắt khe (thời hạn mượn, số lượng sách, các mức bồi thường, phân loại phòng đọc). Đây là bài toán hỏi đáp thực tế sinh viên đối mặt thường xuyên nhưng dữ liệu lại phân tán. Hơn nữa, tài liệu có sự phân hóa đối tượng rõ rệt (sinh viên vs giảng viên) và phân khu chức năng (Phòng 102, 111, 411), là kịch bản hoàn hảo để kiểm thử năng lực truy xuất ngữ nghĩa và hiệu quả vượt trội của việc lọc theo Metadata trong RAG.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | `huit-borrow-faculty.md` | https://thuvien.huit.edu.vn/Page/quy-dinh-su-dung-thu-vien | 2026-09-19 / v1.0 | 997 | `audience: faculty`, `dept: library` |
| 2 | `huit-borrow-student.md` | https://thuvien.huit.edu.vn/Page/quy-dinh-su-dung-thu-vien | 2026-09-19 / v1.0 | 973 | `audience: student`, `dept: library` |
| 3 | `library-borrow-home.md` | https://library.hust.edu.vn/vi/node/38 | 2026-09-19 / v2.0 | 1,785 | `audience: student`, `dept: library` |
| 4 | `library-faq.md` | https://library.hust.edu.vn/vi/node/50 | 2026-09-19 / v2.1 | 4,717 | `audience: all`, `dept: library` |
| 5 | `library-inhouse-borrow.md` | https://library.hust.edu.vn/vi/node/1300 | 2026-09-19 / v1.2 | 1,035 | `audience: all`, `dept: library` |
| 6 | `library-interlibrary.md` | https://library.hust.edu.vn/vi/node/977 | 2026-09-19 / v1.0 | 1,080 | `audience: all`, `dept: library` |
| 7 | `library-lost-document.md` | https://library.hust.edu.vn/vi/node/549 | 2026-09-19 / v2.0 | 1,720 | `audience: student`, `dept: library` |
| 8 | `library-room-102.md` | https://library.hust.edu.vn/vi/node/502 | 2026-09-19 / v1.5 | 1,062 | `audience: student`, `dept: library` |
| 9 | `library-room-111.md` | https://library.hust.edu.vn/vi/node/483 | 2026-09-19 / v1.5 | 1,872 | `audience: student`, `dept: library` |
| 10 | `library-usage-guide.md` | https://library.hust.edu.vn/vi/node/455 | 2026-09-19 / v2.0 | 930 | `audience: all`, `dept: library` |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `audience` | string | `student`, `faculty`, `all` | Phân tách đối tượng bạn đọc. Giúp lọc chính xác quy định mà không bị lẫn lộn giữa chính sách của sinh viên và giảng viên khi câu hỏi có từ khóa tương đồng. |
| `department` / `room` | string | `library`, `102`, `111`, `411` | Khu biệt không gian và phòng phục vụ chuyên môn (sách giáo trình vs sách tham khảo vs đọc tại chỗ), tăng độ đặc hiệu của kết quả tìm kiếm. |
| `source_url` | string | `https://library.hust.edu.vn/vi/node/38` | Phục vụ truy vết nguồn gốc thông tin (Source Traceability), hiển thị trích dẫn đáng tin cậy cho người dùng trong câu trả lời của Agent. |
| `document_version` | string | `v1.5`, `2026-09-19` | Kiểm soát tính hiệu lực của nội quy, bảo đảm hệ thống chỉ truy xuất văn bản mới nhất, loại bỏ tài liệu cũ đã hết hiệu lực thi hành. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 3 tài liệu đại diện trong bộ dữ liệu:

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| `library-borrow-home.md` (1,785 ký tự) | FixedSizeChunker (`fixed_size`) | 10 | 196.5 | Nguy cơ cắt ngang câu hoặc giữa bảng quy định mượn trả |
| | SentenceChunker (`by_sentences`) | 8 | 221.6 | Tốt, giữ trọn vẹn từng câu quy định và mốc thời gian |
| | RecursiveChunker (`recursive`) | 11 | 160.8 | Tốt, ưu tiên ngắt theo đoạn `\n\n` trước khi chia nhỏ |
| `library-room-111.md` (1,872 ký tự) | FixedSizeChunker (`fixed_size`) | 11 | 188.4 | Trung bình, các điều khoản thủ tục bị xé nhỏ |
| | SentenceChunker (`by_sentences`) | 11 | 168.6 | Rất tốt, giữ nguyên các bước thực hiện tuần tự |
| | RecursiveChunker (`recursive`) | 15 | 123.5 | Khá tốt, nhưng các đoạn ngắn bị phân mảnh |
| `library-faq.md` (4,717 ký tự) | FixedSizeChunker (`fixed_size`) | 27 | 194.0 | Kém, câu hỏi và câu trả lời dễ rơi vào 2 chunk tách biệt |
| | SentenceChunker (`by_sentences`) | 18 | 258.1 | Tốt, giữ được ngữ cảnh tương đối giữa câu hỏi và trả lời |
| | RecursiveChunker (`recursive`) | 34 | 137.1 | Tốt nhất, bám theo từng mục `\n\n` hỏi đáp của FAQ |

### Chiến lược của từng thành viên

**Thành viên 1 — Tạ Hoàng Vinh (MSSV: 2A202602543)**
- **Loại chiến lược:** Fixed-Size Chunking (`chunk_size=700`, `overlap=50`)
- **Mô tả & lý do chọn cho chủ đề này:** Tăng kích thước chunk từ mặc định 200 lên 700 ký tự nhằm bao trọn toàn bộ một điều khoản quy định hoặc quy trình mượn trả sách trong một chunk duy nhất, tránh tình trạng mất ngữ cảnh do cắt ngang. Độ chồng chéo `overlap=50` giúp bảo toàn các cụm từ nằm ở ranh giới cắt.
- **Code snippet (nếu custom):**
```python
# Cấu hình FixedSizeChunker tối ưu cho văn bản quy phạm thư viện
from src.chunking import FixedSizeChunker

chunker = FixedSizeChunker(chunk_size=700, overlap=50)
chunks = chunker.chunk(document_text)
```

**Thành viên 2 — Ngô Đức Chung (MSSV: 2A202602985)**
- **Loại chiến lược:** Sentence-Based Chunking (`max_sentences=3`)
- **Mô tả & lý do chọn:** Trong văn bản quy định, mỗi câu hoặc điều khoản ngắn là một đơn vị ngữ nghĩa độc lập. Việc nhóm 3 câu liên tiếp tạo thành một chunk vừa đảm bảo câu văn ngữ pháp nguyên vẹn, vừa cung cấp đủ thông tin quy định kèm theo điều kiện áp dụng mà không bị nhiễu.
- **Code snippet (nếu custom):**
```python
from src.chunking import SentenceChunker

chunker = SentenceChunker(max_sentences=3)
chunks = chunker.chunk(document_text)
```

**Thành viên 3 — Bùi Tiến Cường (MSSV: 2A202602539)**
- **Loại chiến lược:** Heading-Based Chunking (`max_chunk_size=350`) — [Yêu cầu riêng K4-L3A]
- **Mô tả & lý do chọn:** Tài liệu thư viện được định dạng Markdown với các tiêu đề mục rõ ràng (`#`, `##`, `###`). Chiến lược phân tách dựa trên Heading giúp gom nhóm toàn bộ nội dung của từng điều khoản (ví dụ: `## 2. Chính sách`, `## Mức bồi thường`) thành một đơn vị logic hoàn chỉnh.
- **Code snippet (nếu custom):**
```python
import re

class HeadingChunker:
    # Chia nhỏ văn bản dựa trên tiêu đề Markdown (h1-h3)
    def __init__(self, max_chunk_size: int = 350):
        self.max_chunk_size = max_chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        sections = re.split(r"(?=(?:^|\n)#{1,6}\s+|(?:^|\n)Điều\s+\d+[:\.])", text.strip())
        chunks = []
        for sec in sections:
            s = sec.strip()
            if s:
                if len(s) > self.max_chunk_size:
                    chunks.append(s[:self.max_chunk_size].strip())
                else:
                    chunks.append(s)
        return chunks
```

**Thành viên 4 — Phạm Quang Huy (MSSV: 2A202602900)**
- **Loại chiến lược:** Recursive Chunking (`chunk_size=300`)
- **Mô tả & lý do chọn:** Áp dụng thuật toán chia đệ quy đa cấp theo thứ tự ưu tiên `["\n\n", "\n", " ", ""]`. Chiến lược này tôn trọng ngắt đoạn tự nhiên giữa các điều khoản trước, chỉ chia nhỏ tiếp nếu đoạn văn vượt quá giới hạn 300 ký tự.
- **Code snippet (nếu custom):**
```python
from src.chunking import RecursiveChunker

chunker = RecursiveChunker(chunk_size=300, separators=["\n\n", "\n", " ", ""])
chunks = chunker.chunk(document_text)
```

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Tạ Hoàng Vinh | Fixed-Size (`chunk_size=700, overlap=50`) | **9 / 10** | Bao quát toàn bộ ngữ cảnh điều khoản, đạt Top 1 ở 4/5 câu hỏi, điểm tương đồng cao (0.512-0.607), chứa trọn vẹn số liệu ở cả 2 mức chấm. | Kích thước chunk lớn có thể mang theo thông tin phụ không cần thiết, làm loãng vector ở các câu hỏi chi tiết. |
| Ngô Đức Chung | Sentence-Based (`max_sentences=3`) | **9 / 10** (Mức 1) / **8 / 10** (Mức 2) | Giữ cấu trúc ngữ pháp tự nhiên, đạt Top 1 ở 4/5 câu hỏi, đặc biệt xuất sắc ở câu hỏi chi tiết Q3 (score 0.599). | Số lượng chunk nhiều (69 chunks); ở Q5 chunk #0 lọt Top 1 nhưng bị thiếu số liệu giờ trả sách 17h30 (nằm ở chunk trả sách riêng). |
| Bùi Tiến Cường | Heading-Based (`max_chunk_size=350`) | **8 / 10** (Mức 1) / **7 / 10** (Mức 2) | Giữ được tiêu đề ngữ cảnh cho từng điều khoản, câu trả lời có tính định danh phân khu rất cao. | Một số heading dài vượt 350 ký tự bị cắt cụt; ranh giới tách rời phần "mượn" và "trả" khiến Q5 thiếu dữ liệu thời gian trả. |
| Phạm Quang Huy | Recursive (`chunk_size=300`) | **7 / 10** (Mức 1) / **5 / 10** (Mức 2) | Linh hoạt thích ứng với cấu trúc đoạn văn, số lượng chunk vừa phải (63 chunks). | Gặp thất bại ở Q1 (0/2 điểm) do việc gộp các đoạn ngắn làm loãng từ khóa đặc trưng khi tính vector TF-IDF. |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> Xét về thực nghiệm, **Fixed-Size cỡ lớn (700 ký tự)** thể hiện độ tin cậy vượt trội khi vượt qua cả 2 mức chấm (Top-1 đúng tài liệu và chứa trọn vẹn số liệu). Tuy nhiên, về mặt kiến trúc RAG quy mô lớn, **Sentence-Based kết hợp Heading-Based** là giải pháp khoa học nhất vì bảo toàn được cấu trúc logic phân cấp (Điều/Khoản) mà không phụ thuộc vào việc tinh chỉnh kích thước ký tự thô.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chuỗi số liệu đặc trưng cần có | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|-------------------------------|--------------------------|
| 1 | Thời hạn mượn sách đối với sinh viên trong trường là bao nhiêu ngày và được gia hạn mấy lần? | Sinh viên, học viên được mượn tối đa 3 cuốn trong thời hạn 10 ngày, được gia hạn 1 lần (10 ngày/lần). *(Lưu ý: Nếu không lọc `audience: student`, kết quả sẽ bị lẫn sang chính sách của Giảng viên 180 ngày).* | `"10 ngày"`, `"3 cuốn"` | `huit-borrow-student#0` / `huit-borrow-student#1` |
| 2 | Sinh viên được mượn tối đa bao nhiêu cuốn giáo trình tại Phòng 111 và thời hạn mượn là bao lâu? | Mỗi bạn đọc được mượn tối đa 8 cuốn giáo trình tại Phòng 111 với thời hạn 90 ngày, được gia hạn 1 lần trong thời gian 30 ngày (tổng 120 ngày). | `"8 cuốn"`, `"90 ngày"` | `library-room-111#0` / `library-borrow-home#0` |
| 3 | Tại Phòng 102 mượn sách tham khảo, số lượng mượn tối đa là bao nhiêu và được gia hạn mấy ngày? | Sinh viên được mượn tối đa 5 cuốn sách tham khảo tại Phòng 102, thời hạn mượn 30 ngày, được gia hạn 1 lần trong 7 ngày. | `"5 cuốn"`, `"30 ngày"`, `"7 ngày"` | `library-room-102#1` / `library-borrow-home#4` |
| 4 | Mức bồi thường khi làm mất tài liệu thư viện không còn phát hành trên thị trường được tính thế nào? | Tài liệu không phát hành trên thị trường: bồi thường bằng tiền gấp 03 lần giá bìa. Nếu tài liệu còn phát hành: bồi thường tài liệu mới tương đương cộng 20.000đ phí xử lý kỹ thuật. | `"gấp 03 lần"`, `"giá bìa"` | `library-lost-document#0` / `library-lost-document#1` |
| 5 | Quy định mượn tài liệu in-house đọc tại chỗ cho phép mượn tối đa mấy cuốn và trả trước mấy giờ? | Mỗi lần bạn đọc được mượn tối đa 02 cuốn tài liệu in-house và phải trả lại tại quầy thủ thư Phòng 411 trước 17h30 cùng ngày. | `"02 cuốn"`, `"17h30"` | `library-inhouse-borrow#0` |

### Tổng hợp chất lượng truy xuất của nhóm (Chấm 2 mức)

> **Quy tắc chấm 2 mức nghiêm ngặt (theo `docs/SCORING.md` & Checkpoint 6):**
> - **2 điểm:** Tài liệu Gold nằm ở Top-1 VÀ ngữ cảnh chunk chứa chuỗi số liệu đáp án.
> - **1 điểm:** Tài liệu Gold nằm ở Top-2/3 (hoặc Top-1 nhưng số liệu bị phân mảnh sang chunk khác).
> - **0 điểm:** Không có tài liệu Gold trong Top-3 hoặc chunk không chứa thông tin trả lời được.

| # | Câu hỏi | Chiến lược tốt nhất | Mức 1 (Doc ID đúng?) | Mức 2 (Chứa số liệu đáp án?) | Điểm số | Ghi chú đánh giá |
|---|---------|---------------------|----------------------|------------------------------|---------|-------------------|
| 1 | Thời hạn mượn sinh viên | Fixed-Size (`chunk_size=700`) | ✅ Đúng Top-1 (`huit-borrow-student#0`) | ✅ Đủ ("3 cuốn", "10 ngày") | **2 / 2** | Bắt buộc lọc metadata `{'audience': 'student'}`. Fixed đạt 2đ; Sentence, Heading đạt 1đ (Top-3); Recursive 0đ. |
| 2 | Số lượng giáo trình P.111 | Fixed, Sentence, Recursive | ✅ Đúng Top-1 (`library-room-111#0`) | ✅ Đủ ("8 cuốn", "90 ngày") | **2 / 2** | Cả 4 chiến lược đều định vị chính xác quy trình mượn Phòng 111. |
| 3 | Sách tham khảo P.102 | Sentence-Based & Heading | ✅ Đúng Top-1 (Sentence 0.599, Heading 0.584) | ✅ Đủ ("5 cuốn", "7 ngày") | **2 / 2** | Sentence & Heading bám sát điều khoản ngắn; Fixed rơi Top 3 (1đ); Recursive Top 2 (1đ). |
| 4 | Đền bù mất tài liệu | Cả 4 chiến lược | ✅ Đúng Top-1 (`library-lost-document#0`) | ✅ Đủ ("gấp 03 lần", "giá bìa") | **2 / 2** | Từ khóa đặc thù rất mạnh, cả 4 chiến lược đều đạt điểm tuyệt đối 2/2đ. |
| 5 | Mượn in-house đọc tại chỗ | Fixed-Size (`chunk_size=700`) | ✅ Đúng Top-1 (`library-inhouse-borrow#0`) | ✅ Đủ ("02 cuốn", "17h30") | **2 / 2** | **Phát hiện quan trọng của Lab:** Chunk 700 ký tự chứa trọn vẹn cả mục mượn (2 cuốn) và trả (17h30). Sentence và Heading bị chia làm 2 chunk riêng nên chunk #0 lọt Top 1 nhưng thiếu giờ trả (chỉ đạt 1đ). |

---

### Phân tích Thử nghiệm A/B Testing Metadata Filter (Bắt buộc)

Chạy câu hỏi Q1 hai lần — một lần có `metadata_filter={'audience': 'student'}` và một lần không có bộ lọc — trên cả 4 chiến lược:

| Chiến lược | Kết quả CÓ BỘ LỌC (`audience: student`) | Kết quả KHÔNG CÓ BỘ LỌC (No filter) | Nhận xét & Biến động Rank |
|------------|-----------------------------------------|--------------------------------------|---------------------------|
| **Fixed-Size (Vinh)** | **Top 1:** `huit-borrow-student#0` (0.512)<br>**Top 2:** `library-borrow-home#0` (0.386)<br>**Top 3:** `library-room-111#0` (0.359) | **Top 1:** `huit-borrow-student#0` (0.512)<br>**Top 2:** `huit-borrow-faculty#0` (0.496)<br>**Top 3:** `library-borrow-home#0` (0.386) | Khi không lọc, tài liệu Giảng viên nhảy ngay vào Top 2 (score 0.496) áp sát Top 1, tạo nguy cơ nhiễu thông tin nghiêm trọng. |
| **Sentence (Chung)** | **Top 1:** `library-room-102#1` (0.524)<br>**Top 2:** `library-borrow-home#4` (0.508)<br>**Top 3:** `huit-borrow-student#1` (0.445) | **Top 1:** `library-room-102#1` (0.524)<br>**Top 2:** `library-borrow-home#4` (0.508)<br>**Top 3:** `huit-borrow-faculty#1` (0.478) | **Mất dấu hoàn toàn:** Tài liệu Giảng viên chiếm vị trí Top 3 (score 0.478), **đẩy văng tài liệu Sinh viên ra khỏi Top-3**. Điểm giảm từ 1đ xuống 0đ! |
| **Heading (Cường)** | **Top 1:** `library-room-102#2` (0.537)<br>**Top 2:** `library-borrow-home#4` (0.517)<br>**Top 3:** `huit-borrow-student#1` (0.516) | **Top 1:** `huit-borrow-faculty#1` (0.589)<br>**Top 2:** `library-room-102#2` (0.537)<br>**Top 3:** `library-borrow-home#4` (0.517) | **Sai lệch hoàn toàn:** Tài liệu Giảng viên chiếm luôn **Top 1 tuyệt đối** (score 0.589), tài liệu Sinh viên bị loại khỏi Top-3. Agent sẽ trả lời sai thành "180 ngày"! |
| **Recursive (Huy)** | Top 1-3 không có tài liệu Sinh viên | Top 1-3 không có tài liệu Sinh viên | Thất bại do chunk nhỏ làm loãng vector TF-IDF. |

**Kết luận thực nghiệm A/B:**
> Thử nghiệm A/B chứng minh không thể chối cãi rằng **tiền lọc Metadata là bắt buộc**. Nếu không có bộ lọc `audience: student`, cả 3 chiến lược Sentence, Heading và Fixed đều bị ô nhiễm bởi tài liệu Giảng viên (thậm chí Heading bị lật ngược Top 1 sang Giảng viên 180 ngày). Việc lọc trước (pre-filtering) giúp thu hẹp không gian tìm kiếm, bảo đảm độ chính xác 100% về đối tượng áp dụng.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

### Phân tích lỗi (Failure Case Analysis) — Đủ 3 phần theo yêu cầu

Nhóm đúc kết 3 failure cases thực tế nhất từ dữ liệu benchmark:

#### Failure Case 1: RecursiveChunker thất bại hoàn toàn ở Câu Q1 (0/2 điểm)
- **Câu hỏi hỏng:** Q1 — *"Thời hạn mượn sách đối với sinh viên trong trường là bao nhiêu ngày và được gia hạn mấy lần?"*
- **Vì sao (Root Cause):** Thuật toán `RecursiveChunker(chunk_size=300)` khi gặp các điều khoản ngắn có cấu trúc gạch đầu dòng trong `huit-borrow-student.md` đã tách chúng thành các mẩu nhỏ và gộp lỏng lẻo. Đoạn chứa số liệu *"10 ngày, 3 cuốn"* có quá ít từ khóa dẫn đến vector TF-IDF bị giảm trọng số (pha loãng vector) và tụt xuống tận hạng 4-5. Trong khi đó, các chunk từ `library-borrow-home#1` và `#4` có nhiều từ lặp lại ("mượn", "thời hạn", "gia hạn") nên chiếm trọn Top 3 dù nội dung quy định thuộc về phòng đọc khác.
- **Đề xuất sửa:** Tăng `chunk_size` lên 500-700 ký tự hoặc bổ sung tham số `chunk_overlap` khi chia đệ quy; hoặc chuyển sang dùng `SentenceChunker` kết hợp tiêu đề mục.

#### Failure Case 2: HeadingChunker bị "Đúng tài liệu nhưng sai Section" ở Câu Q5
- **Câu hỏi hỏng:** Q5 — *"Quy định mượn tài liệu in-house đọc tại chỗ cho phép mượn tối đa mấy cuốn và trả trước mấy giờ?"*
- **Vì sao (Root Cause):** `HeadingChunker` phân tách văn bản theo tiêu đề Markdown: `## Quy trình mượn` (chứa số liệu 2 quyển) và `## Quy trình trả` (chứa mốc 17h30) bị chia thành 2 chunk độc lập. Khi tính điểm độ tương tự Cosine, chunk giới thiệu ban đầu (`library-inhouse-borrow#0`) lặp lại từ khóa *"in house"* nhiều nhất nên thắng Top 1, nhưng nó **hoàn toàn không chứa số liệu trả sách trước 17h30**. Nếu chỉ kiểm tra ngây thơ theo `doc_id`, hệ thống tưởng là đạt Top 1, nhưng thực tế LLM Agent sẽ không đủ thông tin để trả lời vế thứ hai.
- **Đề xuất sửa:** Kích hoạt cơ chế **Parent Document Retrieval** hoặc gộp các mục con liền kề trong cùng một văn bản ngắn dưới 1.000 ký tự thay vì phân mảnh quá sâu.

#### Failure Case 3: HeadingChunker khi KHÔNG dùng Metadata Filter ở Câu Q1
- **Câu hỏi hỏng:** Q1 khi tắt metadata filter.
- **Vì sao (Root Cause):** Chunk `huit-borrow-faculty#1` của Giảng viên có cấu trúc câu và mật độ từ khóa ("thời hạn mượn", "số lượng mượn tối đa", "gia hạn") dày đặc hơn chunk của Sinh viên, khiến Cosine Similarity đạt 0.589 (vượt trội so với 0.516 của Sinh viên) và cướp vị trí Top 1.
- **Đề xuất sửa:** Bắt buộc áp dụng cơ chế tiền lọc `store.search_with_filter(metadata_filter={'audience': 'student'})` trong tầng Application/API trước khi gửi vector query.

---

### Những phân tích (insights) hay nhất nhóm sẽ trình bày (Demo)
> 1. **Khoảng cách giữa Chấm ngây thơ (Doc ID) và Chấm thực tế (Content-Level):** Việc chỉ kiểm tra `doc_id` tạo ra ảo tưởng về độ chính xác (như trường hợp Q5 của Heading/Sentence). Đánh giá RAG bắt buộc phải kiểm tra chuỗi số liệu cốt lõi trong ngữ cảnh trả về.
> 2. **Hiệu quả định lượng của Metadata Pre-filtering:** Thử nghiệm A/B trên Q1 chứng minh nếu không lọc metadata, tài liệu đúng bị đẩy văng khỏi Top 3 ở 2/4 chiến lược và bị lật ngược Top 1 ở Heading.
> 3. **Đặc thù văn bản hành chính/quy phạm:** Chunk kích thước vừa và lớn (500-700 ký tự) có độ chồng lấp (overlap) phù hợp hơn với văn bản nội quy so với các chunk nhỏ bị phân mảnh.

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng một kho tài liệu 10 file và cùng một mô hình TF-IDF, nhưng 4 chiến lược chunking khác nhau tạo ra phổ điểm phân hóa từ 7/10 đến 9/10 và số lượng chunk chênh lệch từ 25 đến 69 chunks. Điều này chứng minh rằng **chiến lược Chunking là yếu tố quyết định hàng đầu đến chất lượng của hệ thống RAG**, thậm chí có thể bù đắp được các hạn chế cố hữu của các mô hình embedding dạng từ khóa đơn giản.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> 1. **Chuyển sang Semantic / Markdown-AST Chunking:** Thay vì cắt theo ký tự hoặc câu thô, nhóm sẽ phân tích cây cú pháp Markdown để tự động đính kèm ngữ cảnh tiêu đề cha (Parent Heading) vào đầu mỗi chunk con, giúp chunk vừa ngắn gọn vừa không mất ngữ cảnh ngữ nghĩa.
> 2. **Bổ sung Dense Embedding & Tìm kiếm lai (Hybrid Search):** Kết hợp TF-IDF (bắt chính xác mã phòng, số lượng, thuật ngữ) với mô hình Dense Embedding đa ngôn ngữ (như `text-embedding-3-small` hoặc `bge-m3`) để giải quyết triệt để bài toán đồng nghĩa / diễn giải khác từ vựng (paraphrasing).

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 15 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 10 / 10 |
| Thuyết trình (Demo) | 5 / 5 |
| **Tổng phần nhóm** | **40 / 40** |
