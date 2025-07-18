# Hospital Patient Vital Data Collector
Prometheus에서 병원별 환자 생체 데이터(심박수, 호흡수, 산소포화도 등)를 수집하여 병실 단위 CSV 파일로 저장하고, 일일 평균을 계산해 병원별 Excel로 저장하는 Python 기반 자동화 도구입니다.
---
## 기능 요약

- 병원별 UID 리스트(json 파일) 기반으로 Prometheus에 쿼리
- `16:00 ~ 익일 16:00` 사이의 데이터를 가져옴
- 병실별 CSV 파일 저장
- 일일 평균값을 병원별 Excel 파일로 저장
- 수동 모드 및 자동 모드 지원

---

## 📂디렉터리 구조

```
project/
│
├── json/                      # 병원별 room_id-UID 매핑 JSON 파일
│   ├── hyo_uid_list.json
│   ├── jj_uid_list.json
│   └── yn_uid_list_5.json
│
├── main.py                     # 실행 파일
├── 심박수_전체요약_확장.xlsx    # 평균값이 저장된 Excel 파일
└── README.md                  # 설명서
```

---

## 사용 방법

### 1. scheduler를 통한 자동 실행 (모든 병원 수집 및 저장)

```bash
python run_Measure.py
```

### 2. 수동 실행 (병원, 날짜, 경로 직접 지정)

```bash
python run_Measure.py
```

병원 코드를 입력하세요 (예: hyo, jj, yn5): jj
시간을 입력하세요 (예: 20250717 0900): 20250717 0900
CSV 저장 폴더 경로를 입력하세요: ./output_csv
```
> `yn5`처럼 병원 코드 뒤에 숫자를 붙이면 `yn_uid_list_5.json` 파일을 자동 참조합니다.
---

## ⏰ 수집 구간 설명

- **수집 대상 기간은 전날 16시부터 입력한 날짜의 16시까지**
- 예: `20250717 0900` 입력 → 수집 기간: `2025-07-16 16:00 ~ 2025-07-17 16:00`

- **scheduler를 통한 데이터 수집 시간은 16시, 데이터 평균은 8, 16시**

---

## 📊 결과 파일 구조

project/
│
├── HospitalData/    # 병원 전체 폴더                 
│   ├── HYO
│   ├── JJ
│   ├── YN ├──2025-07-10         # 오늘자 날짜
              ├── 2025.7.10_501_01_0558B5C030719.csv # 데이터 파일

- 병실별 CSV: `2025.6.13_216_05_05583E8161226.csv`
- 병원별 평균 Excel: `output_excel/hyo_20250717.xlsx`

Excel 파일은 다음 형식으로 구성됩니다:

| Room ID  | heart_rate | breath_rate | spo2 |
|----------|------------|-------------|------|
| room101  | 85.2       | 18.3        | 97.5 |
| room102  | 87.0       | 19.0        | 98.1 |
| ...      | ...        | ...         | ...  |

---

## 🔧 UID JSON 파일 예시

`json/hyo_uid_list.json`:

```json
{
  "room101": "hyo/uid123",
  "room102": "hyo/uid456"
}
```

---

## 📈 Prometheus 쿼리 대상 메트릭

기본 설정된 메트릭 목록 (코드에서 정의 필요):

- `heart_rate`
- `breath_rate`
- `spo2`

쿼리 형태:
```
avg_over_time(metric_name{job="hyo/uid123"}[10s])
```

---

## 🧪 주요 함수 설명

- `fetch_prometheus_metrics(...)`  
  Prometheus로부터 메트릭 데이터를 가져와 병실별 CSV로 저장

- `save_average_metrics_to_excel(...)`  
  병실별 CSV를 읽어 평균값을 Excel 파일로 저장

- `save_all_hospital_data()`  
  모든 병원의 데이터를 자동으로 저장 (자동 모드)

- `save_input_hospital_data()`  
  수동으로 병원/시간/경로를 입력받아 저장 (수동 모드)

---

## ❓ 자주 묻는 질문

### Q. `yn5`와 같은 병원 코드는 무엇인가요?
- `yn`은 병원 코드이며, `5`는 별도의 인스턴스나 장비 세트를 구분하기 위한 넘버링입니다.
- 해당 경우 `yn_uid_list_5.json` 파일을 자동으로 불러옵니다.

### Q. Prometheus가 연결되지 않으면 어떻게 되나요?
- 서버 접속이 실패할 경우 메시지 출력 후 해당 병실은 건너뜁니다.
- `http://your-prometheus-url`을 실제 주소로 변경해야 합니다 (코드 상에 설정 필요).

---

## 📄 라이선스

MIT License  
© 2025 YourName or YourTeam
