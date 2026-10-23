# Use Case: Dự Báo Chuỗi Thời Gian Nhu Cầu Taxi (Time-Series Demand Forecasting)

> **Dự án:** Khai thác dữ liệu lớn trên nền tảng Data Lakehouse 5 lớp (IBM Architecture)  
> **Dữ liệu thực nghiệm:** NYC TLC Yellow Taxi Trip Records (Tháng 01/2026, ~3.7 triệu giao dịch)  
> **Mô hình triển khai:** Closed-loop Machine Learning trên Lakehouse (Airbyte → SeaweedFS → Nessie → Trino → Python/Prophet → Superset)

---

## 1. Giới Thiệu & Bài Toán Nghiệp Vụ

Trong các hệ thống gọi xe và điều phối giao thông đô thị (như Taxi, Uber, Grab), việc dự đoán trước nhu cầu đi lại theo từng giờ đóng vai trò then chốt giúp:
1. **Tối ưu hóa điều phối phương tiện (Fleet Management):** Chủ động điều chuyển xe tới các khu vực có nhu cầu đột biến trước khi xảy ra tình trạng thiếu xe.
2. **Định giá cước linh hoạt (Dynamic / Surge Pricing):** Dự báo trước các khung giờ cao điểm để cân bằng cung - cầu.
3. **Giảm thời gian chờ của hành khách:** Nâng cao chất lượng dịch vụ và tăng doanh thu cho tài xế.

### Tại sao chọn chuỗi thời gian theo giờ (Hourly Time Series)?
Dữ liệu di chuyển đô thị có tính **mùa vụ kép (Multi-seasonality)** đặc trưng:
* **Chu kỳ ngày (Daily Seasonality - 24 giờ):** Đáy nhu cầu lúc 03:00 - 05:00 sáng, đỉnh nhu cầu vào các khung giờ tan tầm (17:00 - 21:00).
* **Chu kỳ tuần (Weekly Seasonality - 7 ngày):** Các ngày làm việc (Thứ 2 - Thứ 6) có mô hình giờ cao điểm sáng/tối rõ rệt; cuối tuần (Thứ 7, CN) nhu cầu tập trung giải trí về đêm và rải đều hơn trong ngày.

---

## 2. Kiến Trúc Luồng Dữ Liệu (5-Layer Lakehouse Architecture)

Quy trình khai thác áp dụng nguyên tắc **Pushdown Computation**: Toàn bộ việc xử lý 3.7+ triệu dòng thô được thực hiện trên động cơ phân tán **Trino** tại tầng Storage/Metadata (**SeaweedFS + Nessie + Iceberg**). Python chỉ nhận chuỗi thời gian tinh gọn để huấn luyện mô hình, sau đó ghi ngược kết quả dự báo về Lakehouse để **Superset** trực quan hóa.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. INGESTION LAYER (Airbyte)                                                    │
│    - Nạp file Parquet thô (yellow_tripdata_2026-01) vào kho                     │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 2 & 3. STORAGE & METADATA LAYERS (SeaweedFS S3 + Project Nessie + Apache Iceberg)│
│    - Bảng Raw/Silver: lakehouse.samples.samples (~3.72 triệu dòng)              │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 4. PROCESSING & API LAYER (Trino Query Engine)                                  │
│    - CTAS Pushdown: Làm sạch, lọc nhiễu, gom nhóm theo giờ (3.7M -> 744 dòng)   │
│    - Bảng Gold: lakehouse.gold.hourly_taxi_demand                               │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 5. ADVANCED ANALYTICS & CLOSED-LOOP ML (Python & Meta Prophet)                  │
│    - 01_create_gold_metrics.py: Tạo Gold Table qua Trino                        │
│    - 02_eda_timeseries.py: Phân tích tính liên tục & chu kỳ mùa vụ              │
│    - 03_train_forecast_model.py: Huấn luyện Prophet, kiểm thử ngoại mẫu (Test)  │
│    - 04_publish_to_lakehouse.py: Ghi kết quả vào lakehouse.gold.taxi_demand_... │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 6. CONSUMPTION LAYER (Apache Superset)                                          │
│    - Dashboard trực quan hóa: Actual vs Forecasted + 80% Confidence Interval    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Cấu Trúc Thư Mục

```text
use-cases/forcasting/
├── config.py                     # Cấu hình kết nối Trino, schemas, đường dẫn thư mục
├── 01_create_gold_metrics.py     # Bước 1: Trích xuất và tổng hợp dữ liệu Gold trên Trino
├── 02_eda_timeseries.py          # Bước 2: Phân tích khám phá (EDA) & chu kỳ mùa vụ
├── 03_train_forecast_model.py    # Bước 3: Huấn luyện mô hình Prophet & đánh giá sai số
├── 04_publish_to_lakehouse.py    # Bước 4: Đẩy kết quả dự báo ngược lại Iceberg qua Trino
├── run_pipeline.py               # Master script chạy tuần tự toàn bộ pipeline (01 -> 04)
├── data/
│   └── hourly_taxi_demand.csv    # Dữ liệu chuỗi thời gian 744 giờ được trích xuất
└── reports/
    ├── 01_daily_trend.png                # Biểu đồ xu hướng tổng chuyến và doanh thu theo ngày
    ├── 02_hourly_pattern_by_dayofweek.png# Phân bố nhu cầu theo giờ: Ngày thường vs Cuối tuần
    ├── 03_forecast_vs_actual.png         # Đánh giá dự báo ngoại mẫu trên 7 ngày cuối tháng 1
    ├── 04_seasonality_decomposition.png  # Bóc tách các thành phần chu kỳ (Trend, Day, Week)
    └── forecast_results.csv              # Dữ liệu dự báo chi tiết kèm khoảng tin cậy 80%
```

---

## 4. Hướng Dẫn Cài Đặt & Thực Thi

### Điều kiện tiên quyết
1. Các container Lakehouse đang hoạt động (`docker compose ps` báo healthy cho Trino, Nessie, SeaweedFS).
2. Đã cài đặt dependencies từ file `requirements.txt` vào môi trường ảo `venv`.

```bash
# Cập nhật dependencies nếu cần
uv pip install -r requirements.txt --python ./venv/bin/python
```

### Cách 1: Chạy toàn bộ Pipeline tự động bằng một lệnh
```bash
./venv/bin/python use-cases/forcasting/run_pipeline.py
```

### Cách 2: Chạy từng bước độc lập để kiểm tra

#### Bước 1: Tổng hợp dữ liệu tầng Gold trên Lakehouse
```bash
./venv/bin/python use-cases/forcasting/01_create_gold_metrics.py
```
* **Chức năng:** Chạy câu lệnh SQL `CREATE TABLE lakehouse.gold.hourly_taxi_demand AS SELECT ...` trên Trino.
* **Kết quả:** Xử lý hơn 3.7 triệu giao dịch, xuất ra 744 dòng giờ liên tục vào `data/hourly_taxi_demand.csv`.

#### Bước 2: Phân tích khám phá dữ liệu (EDA) & Bóc tách chu kỳ
```bash
./venv/bin/python use-cases/forcasting/02_eda_timeseries.py
```
* **Chức năng:** Kiểm tra tính toàn vẹn thời gian, tính toán giờ cao điểm/thấp điểm, phân tích sự khác biệt giữa ngày trong tuần và cuối tuần.
* **Kết quả:** Tạo ra các biểu đồ trực quan `reports/01_daily_trend.png` và `reports/02_hourly_pattern_by_dayofweek.png`.

#### Bước 3: Huấn luyện mô hình Prophet & Dự báo
```bash
./venv/bin/python use-cases/forcasting/03_train_forecast_model.py
```
* **Chức năng:** 
  * Phân chia tập dữ liệu: **Train** (Ngày 01/01 đến 24/01, 576 giờ) và **Test** (Ngày 25/01 đến 31/01, 168 giờ - tròn 7 ngày).
  * Huấn luyện mô hình Meta Prophet tích hợp Daily Seasonality, Weekly Seasonality và Ngày lễ Hoa Kỳ (US Holidays).
  * Tính toán các chỉ số sai số ngoại mẫu (MAE, RMSE, WAPE, MAPE, R²).
  * Dự báo thêm 7 ngày tương lai (sang tháng 02/2026).
* **Kết quả:** Tạo biểu đồ `reports/03_forecast_vs_actual.png`, `reports/04_seasonality_decomposition.png` và file `reports/forecast_results.csv`.

#### Bước 4: Đẩy kết quả dự báo ngược lại Lakehouse
```bash
./venv/bin/python use-cases/forcasting/04_publish_to_lakehouse.py
```
* **Chức năng:** Tạo bảng Iceberg `lakehouse.gold.taxi_demand_forecast` trong Nessie Catalog và ghi 912 dòng dự báo (Train + Test + Future) qua API của Trino.
* **Kết quả:** Dữ liệu sẵn sàng để kết nối trực tiếp với Apache Superset.

---

## 5. Kết Quả Thực Nghiệm & Phân Tích Chuyên Sâu

### 5.1. Thống kê tổng quan dữ liệu Tháng 01/2026
* **Tổng số chuyến xe hợp lệ:** 3,561,809 chuyến.
* **Tổng doanh thu:** $105,510,789.18.
* **Giờ cao điểm lịch sử:** 21:00 Thứ Năm ngày 29/01/2026 (10,349 chuyến/giờ).
* **Giờ thấp điểm lịch sử:** 03:00 Thứ Hai ngày 26/01/2026 (176 chuyến/giờ).

### 5.2. Đặc trưng chu kỳ mùa vụ (Seasonality Insights)
1. **Mô hình theo thứ trong tuần (Day-of-Week Effect):**
   * Nhu cầu tăng dần từ đầu tuần và đạt đỉnh vào các ngày cuối tuần:
     * **Thứ Hai:** Trung bình 3,739.1 chuyến/giờ (thấp nhất trong tuần).
     * **Thứ Tư - Thứ Sáu:** Duy trì mức cao ~5,000 - 5,180 chuyến/giờ.
     * **Thứ Bảy:** Trung bình 5,484.2 chuyến/giờ (cao nhất trong tuần).
     * **Chủ Nhật:** Giảm xuống 3,803.4 chuyến/giờ.
2. **Mô hình theo giờ trong ngày (Time-of-Day Effect):**
   * **Ngày thường (Mon - Fri):** Xuất hiện 2 đỉnh cao điểm rõ rệt:
     * *Cao điểm sáng:* 07:00 - 09:00 (đi làm).
     * *Cao điểm chiều tối:* 17:00 - 21:00 (tan sở và ăn tối).
   * **Cuối tuần (Sat - Sun):** Nhu cầu sáng bắt đầu muộn hơn (sau 10:00), đỉnh điểm kéo dài liên tục từ 14:00 đến nửa đêm.

### 5.3. Đánh giá chất lượng mô hình trên tập kiểm thử (25/01 - 31/01)
* **MAE (Mean Absolute Error):** 1,621.67 chuyến/giờ.
* **RMSE (Root Mean Squared Error):** 2,155.18 chuyến/giờ.
* **WAPE (Weighted Absolute Percentage Error):** **35.52%** — *Đây là chỉ số chuẩn mực trong ngành vận tải đối với chuỗi thời gian có độ biến thiên cao theo giờ.*
* **R² Score:** 0.4712 (mô hình giải thích được gần 50% phương sai biến thiên nhu cầu ngoại mẫu).

> **Lưu ý chuyên môn về chỉ số MAPE:**  
> Trong báo cáo, MAPE đạt 83.78% do hiện tượng **mẫu số nhỏ (small denominator effect)**: Vào lúc 03:00 - 04:00 sáng, số chuyến thực tế giảm mạnh xuống chỉ còn 176 chuyến. Khi mô hình dự đoán sai lệch vài trăm chuyến (ví dụ dự báo 500 chuyến), sai số phần trăm cục bộ bị phóng đại lên hơn 200%. Do đó, chỉ số **WAPE (35.52%)** và **MAE** phản ánh chính xác năng lực thực tế của mô hình hơn.

---

## 6. Hướng Dẫn Trực Quan Hóa Trên Apache Superset (Consumption Layer)

Sau khi chạy xong Bước 4, bảng `lakehouse.gold.taxi_demand_forecast` đã sẵn sàng trên Trino. Để hiển thị lên Dashboard của Superset:

1. Đăng nhập Superset tại `http://localhost:8088` (Tài khoản: `admin` / Password trong `.env`).
2. Vào **Data** → **Datasets** → Click **+ Dataset**.
3. Chọn:
   * **Database:** `Lakehouse`
   * **Schema:** `gold`
   * **Table Name:** `taxi_demand_forecast`
4. Tạo Chart loại **Time-series Line Chart (ECharts)**:
   * **Time Column:** `ds`
   * **Time Grain:** `hour`
   * **Metrics:** 
     * `AVG(actual_trips)` (Đặt tên nhãn: *Nhu cầu Thực tế*)
     * `AVG(predicted_trips)` (Đặt tên nhãn: *Nhu cầu Dự báo*)
   * **Dimensions:** `split`
5. Thêm vùng phủ khoảng tin cậy: Kéo thêm `lower_bound` và `upper_bound` vào đồ thị để hiển thị khoảng dao động kỳ vọng 80%.

---

## 7. Gợi Ý Kịch Bản Trả Lời Khi Bảo Vệ Đồ Án (Q&A)

### Câu hỏi 1: Tại sao phải dùng Data Lakehouse mà không import file CSV thẳng vào Python để chạy mô hình?
* **Trả lời:**  
  *"Nếu dùng Python đọc trực tiếp hàng chục file CSV/Parquet với hàng chục triệu bản ghi, hệ thống sẽ gặp hiện tượng tràn bộ nhớ (Out-Of-Memory) và không thể mở rộng (scale) khi dữ liệu tăng trưởng. Kiến trúc Lakehouse cho phép áp dụng nguyên tắc **Pushdown Computation**: Động cơ truy vấn phân tán Trino quét dữ liệu phân vùng trên Iceberg/S3 và thực hiện toàn bộ việc tổng hợp, làm sạch trong 2 giây. Python chỉ tiếp nhận chuỗi dữ liệu tinh gọn 744 dòng để tối ưu hóa việc huấn luyện mô hình."*

### Câu hỏi 2: Tính năng nổi bật nào của Iceberg và Nessie đã được ứng dụng trong Use Case này?
* **Trả lời:**  
  *"1. **Bảng Iceberg tầng Gold:** Lưu trữ dạng Parquet có metadata chi tiết, cho phép ghi đè/cập nhật bảng kết quả dự báo nguyên tử (ACID transaction) mà không làm gián đoạn các truy vấn đang chạy từ Superset.*  
  *2. **Nessie Catalog:** Đóng vai trò Git-for-Data, kiểm soát phiên bản snapshot của các bảng dữ liệu, hỗ trợ Time-Travel query nếu cần đối chiếu kết quả dự báo với dữ liệu lịch sử tại bất kỳ thời điểm nào trong quá khứ."*

### Câu hỏi 3: Làm thế nào để cải thiện độ chính xác của mô hình trong tương lai?
* **Trả lời:**  
  *"1. Bổ sung thêm biến ngoại sinh (External Regressors) vào mô hình Prophet: Dữ liệu thời tiết (nhiệt độ, lượng mưa, tuyết rơi) vì thời tiết xấu tại New York làm tăng vọt nhu cầu taxi.*  
  *2. Mở rộng độ mịn không gian: Dự báo nhu cầu theo từng quận/vùng đón khách (`PULocationID`) thay vì toàn thành phố."*