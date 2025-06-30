import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import json
import os
import schedule
import time
import threading
import re
import csv
from openpyxl import load_workbook
from openpyxl.styles import Border, Side
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
now = datetime.now()
year = now.year
month = now.month
day = now.day

# excel 데이터에서 심박, 호흡, 산포도의 평균을 구하는 함수
# 조건1) 평균을 구하는 값은 오전 8 ~ 오전 9시 데이터
# 조건2) 평균 계산 시 값이 0인 값들이 있으면 제외
import os
import re
import csv
from datetime import datetime, timedelta

# 현재는 scheduler를 통해 다운받은 데이터를 7~8, 15~ 16 시간대 평균 계산 
def get_average_data():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "HospitalData")
    json_dir = os.path.join(script_dir, "json")

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    target_times = [
        datetime.strptime(f"{today_str} 08:00", "%Y-%m-%d %H:%M"),
        datetime.strptime(f"{today_str} 16:00", "%Y-%m-%d %H:%M")
    ]

    # 병원별로 저장할 전체 결과 딕셔너리
    hospital_results = {}

    for filename in os.listdir(json_dir):
        if filename.endswith(".json"):
            hospital_name = filename.split('_')[0].upper()

            results = {
                "08:00": {"hr": [], "breath": [], "spo2": [], "rooms": []},
                "16:00": {"hr": [], "breath": [], "spo2": [], "rooms": []},
            }

            hospital_base_dir = os.path.join(data_dir, hospital_name)
            today_date_dir = os.path.join(hospital_base_dir, today_str)

            if not os.path.isdir(today_date_dir):
                print(f"[{hospital_name}] 오늘 날짜 폴더 없음: {today_date_dir}")
                continue

            print(f"[{hospital_name}] 오늘 날짜 폴더 존재: {today_date_dir}")

            for data_file in os.listdir(today_date_dir):
                if not data_file.endswith(".csv"):
                    continue

                print(f"[{hospital_name}] 처리 중: {data_file}")

                match = re.search(r"^\d+\.\d+\.\d+_(\d+)_(\d+)_", data_file)
                if match:
                    room_id = f"{match.group(1)}_{match.group(2)}"
                else:
                    print(f"[{hospital_name}] 파일명에서 room_id 추출 실패: {data_file}")
                    continue

                file_path = os.path.join(today_date_dir, data_file)

                for target_time in target_times:
                    start_time = target_time - timedelta(hours=1)
                    time_key = target_time.strftime("%H:%M")

                    hr_list = []
                    breath_list = []
                    spo2_list = []

                    with open(file_path, 'r', encoding='utf-8') as csvfile:
                        reader = csv.reader(csvfile, delimiter=',')
                        next(reader, None)  # skip header

                        for i, row in enumerate(reader):
                            try:
                                timestamp_str = row[0].strip()
                                full_timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                                timestamp = full_timestamp.replace(second=0)

                                if not (start_time <= timestamp <= target_time):
                                    continue

                                hr = int(row[3])
                                breath = int(row[4])
                                spo2 = int(row[5])

                                if hr != 0:
                                    hr_list.append(hr)
                                if breath != 0:
                                    breath_list.append(breath)
                                if spo2 != 0:
                                    spo2_list.append(spo2)

                            except (IndexError, ValueError) as e:
                                print(f"에러 ({hospital_name} {data_file} 줄 {i+1}): {e}")
                                continue

                    avg_hr = int(round(sum(hr_list) / len(hr_list))) if hr_list else 0
                    avg_breath = int(round(sum(breath_list) / len(breath_list))) if breath_list else 0
                    avg_spo2 = int(round(sum(spo2_list) / len(spo2_list))) if spo2_list else 0

                    results[time_key]["hr"].append(avg_hr)
                    results[time_key]["breath"].append(avg_breath)
                    results[time_key]["spo2"].append(avg_spo2)
                    results[time_key]["rooms"].append(room_id)

                    print(f"[{hospital_name}] [{time_key}] {room_id} → HR: {avg_hr}, BR: {avg_breath}, SPO2: {avg_spo2}")

            hospital_results[hospital_name] = results

    return hospital_results

def get_average_from_custom_folder():
    try:
        folder_path = input("csv를 저장한 폴더 경로를 입력하세요.")
        folder_path = os.path.abspath(folder_path)
        input_str = input("평균을 구할 시간을 입력하세요 (예: 2025-05-20 09:00): ")
        input_datetime = datetime.strptime(input_str, "%Y-%m-%d %H:%M")
    except ValueError:
        print("입력 형식이 잘못되었습니다. 예: 2025-05-20 09:00")
        return [], [], [], []

    start_time = input_datetime - timedelta(hours=1)

    all_avg_hr = []
    all_avg_breath = []
    all_avg_spo2 = []
    room_id_list = []

    if not os.path.isdir(folder_path):
        print(f"지정한 폴더가 존재하지 않습니다: {folder_path}")
        return [], [], [], []

    for data_file in os.listdir(folder_path):
        if data_file.endswith(".csv"):
            print(f"처리 중: {data_file}")
            hr_list = []
            breath_list = []
            spo2_list = []

            match = re.search(r"^(\d+_\d+)_", data_file)
            room_id = match.group(1) if match else "Unknown"

            file_path = os.path.join(folder_path, data_file)

            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile, delimiter=',')
                next(reader, None)  # 헤더 스킵

                for i, row in enumerate(reader):
                    try:
                        timestamp_str = row[0].strip()
                        full_timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                        timestamp = full_timestamp.replace(second=0)

                        if not (start_time <= timestamp <= input_datetime):
                            continue

                        hr = int(row[3])
                        breath = int(row[4])
                        spo2 = int(row[5])

                        if hr != 0:
                            hr_list.append(hr)
                        if breath != 0:
                            breath_list.append(breath)
                        if spo2 != 0:
                            spo2_list.append(spo2)


                    except (IndexError, ValueError) as e:
                        print(f"에러 발생 (줄 {i+1}): {e}")
                        continue

            avg_hr = int(round(sum(hr_list) / len(hr_list))) if hr_list else 0
            avg_breath = int(round(sum(breath_list) / len(breath_list))) if breath_list else 0
            avg_spo2 = int(round(sum(spo2_list) / len(spo2_list))) if spo2_list else 0

            all_avg_hr.append(avg_hr)
            all_avg_breath.append(avg_breath)
            all_avg_spo2.append(avg_spo2)
            room_id_list.append(room_id)

            print(f"{data_file} ({room_id}) 평균 심박: {avg_hr}, 호흡: {avg_breath}, 산소포화도: {avg_spo2}")

    return all_avg_hr, all_avg_breath, all_avg_spo2, room_id_list





# 심박, 호흡, 산포도 평균 값들을 엑셀에 저장하는 함수

def make_averdata_to_excel(avr_heart, avr_breath, avr_spo2, room_id, filename="averdata.xlsx"):
    # 리스트 길이 체크
    if not (len(avr_heart) == len(avr_breath) == len(avr_spo2) == len(room_id)):
        raise ValueError("모든 리스트 길이가 같아야 합니다.")
    
    # DataFrame 생성
    df = pd.DataFrame({
        "room_id": room_id,
        "심박수": avr_heart,
        "호흡수": avr_breath,
        "산소포화도": avr_spo2
      
    })

    
    
    # 엑셀 저장 (덮어쓰기)
    df.to_excel(filename, index=False)
    print(f"{filename} 파일에 저장 완료")

    # excel 스타일 만들기

def make_scheduler_averdata_to_excel_by_hospital(hospital_results):
    for hospital_name, results in hospital_results.items():
        data_rows = []

        for time_key in results:
            for i in range(len(results[time_key]['rooms'])):
                data_rows.append({
                    "시간대": time_key,
                    "room_id": results[time_key]['rooms'][i],
                    "심박수": results[time_key]['hr'][i],
                    "호흡수": results[time_key]['breath'][i],
                    "산소포화도": results[time_key]['spo2'][i],
                })

        df = pd.DataFrame(data_rows)
        filename = f"{hospital_name}_averdata.xlsx"
        df.to_excel(filename, index=False)
        print(f"[{hospital_name}] 엑셀 저장 완료: {filename}")


def fetch_prometheus_metrics(job_name, metrics, start_time, end_time, step=10, timezone_offset=9, output_csv=None, room_id=None):
    """
    Parameters:
        job_name (str): Prometheus job 이름
        metrics (list): 조회할 metric 리스트
        start_time (datetime): 조회 시작 시간 (datetime 객체)
        end_time (datetime): 조회 종료 시간 (datetime 객체)
        step (int): step 간격 (초 단위)
        timezone_offset (int): 타임존 오프셋 (기본 KST: +9)
        output_csv (str): 저장할 CSV 디렉토리 경로 (None이면 저장하지 않음)
        room_id (str): CSV 파일명에 사용할 ID (예: "room1")

    Returns:
        pd.DataFrame 또는 None
    """
    import os
    import requests
    import pandas as pd
    from datetime import timezone, timedelta

    query_url = 'https://3iztvmb7bj.execute-api.ap-northeast-2.amazonaws.com/prometheus/v1/query_range'
    kst = timezone(timedelta(hours=timezone_offset))

    start = int(start_time.timestamp())
    end = int(end_time.timestamp())

    dataframes = []

    for metric in metrics:
        query = f'{metric}{{job="{job_name}"}}'
        params = {
            "query": query,
            "start": start,
            "end": end,
            "step": step
        }

        response = requests.get(query_url, params=params)

        if response.status_code == 200:
            res_data = response.json()
            results = res_data["data"]["result"]

            for idx, series in enumerate(results):
                metric_name = series["metric"].get("__name__", metric)
                values = series["values"]

                df = pd.DataFrame(values, columns=["timestamp", metric_name])
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.tz_convert('Asia/Seoul')
                df["timestamp"] = df["timestamp"].dt.strftime('%Y-%m-%d %H:%M:%S')
                df[metric_name] = pd.to_numeric(df[metric_name], errors="coerce")
                df.set_index("timestamp", inplace=True)

                dataframes.append(df)
        else:
            print(f"[ERROR] {metric} 응답 실패: {response.status_code}")

    if dataframes:
        # 데이터프레임들을 시간 기준으로 병합
        merged_df = pd.concat(dataframes, axis=1).sort_index()

        # CSV 저장 (한 번만)
        if output_csv:
            # 년, 월, 일 받아오기
            uid = job_name.split('/')[1]
            os.makedirs(output_csv, exist_ok=True)
            csv_file_path = os.path.join(output_csv, f"{room_id}_{uid}.csv")
            merged_df.to_csv(csv_file_path)

        return merged_df
    else:
        print("데이터가 없습니다.")
        return None
    
#9시 10분 마다 데이터 저장 함수
def save_all_hospital_data():
    today_str = datetime.now().strftime("%Y-%m-%d")
    # 엑셀 데이터 저장 경로 설정
    script_dir = os.path.dirname(os.path.abspath(__file__))  # 현재 스크립트 파일의 경로
    uid_dir = os.path.join(script_dir, "json")  # JSON 파일들이 들어있는 폴더 경로

    today = datetime.now()
    year = today.year
    month = today.month
    day = today.day
    
    for filename in os.listdir(uid_dir):
        if filename.endswith(".json"):
            file_path = os.path.join(uid_dir, filename)

            # 병원명 추출 (예: 'Yn_Uid_Filename.json' → 'Yn')
            hospital_name = filename.split('_')[0].upper()  # 대문자로 통일: 'YN', 'HYO', 'JJ' 등

            # 저장 경로 구성
            base_path = os.path.join(script_dir, "HospitalData", hospital_name, today_str)
            os.makedirs(base_path, exist_ok=True)

            # JSON 데이터 로드
            uid_data = load_json(file_path)

            for room_id, uid in uid_data.items():
                job_name1 = uid.split('/')[0]  # job name : '21b7'
                uid_value = uid.split('/')[1]  # uid : '0559E31031701'
                df = fetch_prometheus_metrics(
                    job_name= (job_name1 + '/' + uid_value ),
                    metrics=metrics,
                    start_time=yesterday_16pm,  
                    end_time=today_16pm,
                    step=10,
                    room_id=room_id
                )

                # 엑셀로 데이터 저장
                df.to_csv(os.path.join(base_path, f"{year}.{month}.{day}_{room_id}_{uid_value}.csv"))

    # scheduler를 통해 받아온 데이터 평균 계산
    results = get_average_data()
    # 엑셀 파일로 저장
    make_scheduler_averdata_to_excel_by_hospital(results)

# 입력 시간으로 데이터를 추출 및 저장하는 함수
def save_input_hospital_data():
    hospital_input = input("병원 코드를 입력하세요 (ex: hyo, jj, yn5): ").strip()

    hospital_code = ''.join(filter(str.isalpha, hospital_input))
    hospital_num = ''.join(filter(str.isdigit, hospital_input))

    if hospital_code == 'yn' and hospital_num:
        expected_filename = f"{hospital_code}_uid_list_{hospital_num}.json"
    else:
        expected_filename = f"{hospital_code}_uid_list.json"

    # 실행 중인 스크립트의 절대 경로 기준으로 경로 설정
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, 'json', expected_filename)

    print(f"filepath : {file_path}")

    if not os.path.exists(file_path):
        print(f"파일을 찾을 수 없습니다: {file_path}")
        return

    input_str = input("시간을 입력하세요 (예: 20250520 0900): ")
    input_datetime = datetime.strptime(input_str, "%Y%m%d %H%M")
    yesterday_datetime = input_datetime - timedelta(days=1)
    
    output_csv1 = input("엑셀 저장 경로를 입력하세요 :")

    uid_data = load_json(file_path)

    for room_id, uid in uid_data.items():
        job_name = uid.split('/')[0]  # 예: '21b7'
        uid_value = uid.split('/')[1]  # 예: '0559E31031701'
        job_name1 = f"{job_name}/{uid_value}"
    
        df = fetch_prometheus_metrics(
            job_name=job_name1,
            metrics=metrics,
            start_time=yesterday_datetime,
            end_time=input_datetime,
            step=10,
            output_csv=output_csv1,
            room_id=room_id,
        )
   
# run_scheduler 함수
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)   

# json 파일 열기
def load_json(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)
        
# json 파일 저장
def save_json(file_name, data):
    # 폴더 경로 생성
    directory = os.path.join('.', 'json')
    os.makedirs(directory, exist_ok=True)

    # 전체 파일 경로
    full_path = os.path.join(directory, file_name)

    # JSON 파일 저장
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

#json 파일 추가 및 수정
def add_or_change_uid(file_path,room_id,uid):
    data = load_json(file_path)
    data[room_id] = uid
    save_json(file_path, data)
    print(f"[INFO] UID '{uid}' has been added/updated.")

#json 파일 삭제
def delete_json(file_path,room_id):
    data = load_json(file_path)
    if room_id in data:
        data[room_id] = ""
        save_json(file_path, data)
        print(f"[INFO] UID '{room_id}' has been deleted.")
    else:
        print(f"[WARN] UID '{room_id}' not found.")

# -------------------------
# 실행 구문
# -------------------------
if __name__ == "__main__":
    # 시간 설정 (KST 기준 어제 16시 ~ 오늘 16시)
    kst = timezone(timedelta(hours=9))
    today_16pm = datetime.now(tz=kst).replace(hour=16, minute=0, second=0, microsecond=0)
    yesterday_16pm = today_16pm - timedelta(days=1)
    lhour_ago = today_16pm -timedelta(hours=1)
    # metric 및 job 설정
    metrics = [
        'radar_v3_state', 'radar_v3_heart_detection', 'radar_v3_heart',
        'radar_v3_breath', 'radar_v3_sp02', 'radar_v3_drop', 'radar_v3_radar_rssi'
    ]
   
    # At 16:10 save all hospital data
    # Keep the main thread alive so the scheduler can run
    schedule.every().day.at("17:49").do(save_all_hospital_data)
    thread = threading.Thread(target=run_scheduler)
    thread.daemon = True
    thread.start()

    aver_hr=[]
    aver_br = []
    aver_spo2 = []
    room_id_list = []
# command를 받아서 데이터를 저장 및 평균 계산
    
    while True:
        command = input("명령어를 입력하세요 (command : 데이터 다운로드 , average : 평균 계산) (exit 입력 시 종료): ").strip()
        if command == "command":
            save_input_hospital_data()
            command = input("명령어를 입력하세요 (average 입력 시 호실별 평균 계산) (exit 입력 시 종료): ").strip()
        if command == "average":
            aver_hr, aver_br, aver_spo2 , room_id_list= get_average_from_custom_folder()
            # 엑셀에 저장하는 함수
            make_averdata_to_excel(aver_hr, aver_br, aver_spo2,room_id_list)
        elif command == "exit":
            print("프로그램 종료 중...")
            break
        else:
            print("알 수 없는 명령어입니다.")

    print("메인 루프 종료, 프로그램 종료.")
      
    
   





       



