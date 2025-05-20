import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import json
import os
import schedule
import time
import threading
import re
now = datetime.now()
year = now.year
month = now.month
day = now.day

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
            csv_file_path = os.path.join(output_csv, f"({year}.{month}.{day}){room_id}_{uid}.csv")
            merged_df.to_csv(csv_file_path)

        return merged_df
    else:
        print("데이터가 없습니다.")
        return None
    
#9시 30분 마다 데이터 저장 함수
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
                    start_time=yesterday_9am,
                    end_time=today_9am,
                    step=10,
                    room_id=room_id
                )

                # 엑셀로 데이터 저장
                df.to_csv(os.path.join(base_path, f"{year}.{month}.{day}_{room_id}_{uid_value}.csv"))
    print("stop thread")           
   
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
    # 시간 설정 (KST 기준 어제 9시 ~ 오늘 9시)
    kst = timezone(timedelta(hours=9))
    today_9am = datetime.now(tz=kst).replace(hour=9, minute=0, second=0, microsecond=0)
    yesterday_9am = today_9am - timedelta(days=1)

   

    # metric 및 job 설정
    metrics = [
        'radar_v3_state', 'radar_v3_heart_detection', 'radar_v3_heart',
        'radar_v3_breath', 'radar_v3_sp02', 'radar_v3_drop', 'radar_v3_radar_rssi'
    ]
    
     # 아침 9시 반, 데이터 저장
    #save_all_hospital_data()
    schedule.every().day.at("09:18").do(save_all_hospital_data)
    #job = schedule.every(2).seconds.do(save_all_hospital_data)
    #schedule.every(2).seconds.do(message2,'2초마다 알려줄게요')
    thread = threading.Thread(target=run_scheduler)
    thread.daemon = True
    thread.start()

    # Keep the main thread alive so the scheduler can run
    #count =0
    '''
    while True:
        command = input("명령어를 입력하세요 (exit 입력 시 종료): ").strip()
        if command == "metrics":
            fetch_prometheus_metrics()
        elif command == "exit":
            print("프로그램 종료 중...")
            break
        else:
            print("알 수 없는 명령어입니다.")

    print("메인 루프 종료, 프로그램 종료.")
    '''
    #------------------------------input 받아서 데이터 저장하는 코드-------------------------------------------------   
    # 병원 코드 입력
    base_json_dir = 'json'
    hospital_code = input("병원 코드를 입력하세요 (예: hyo, jj): ").strip()

    for filename in os.listdir(base_json_dir):
        if filename.endswith('_uid_list.json'):
            file_head = filename.split('_')[0] # [yn,hyo,jj]
            if hospital_code == file_head:
                # 해당하는 병원의 json 파일 url 만들기 및 load
                file_path = ('json/' + hospital_code.lower() + '_uid_list.json')
                print(f"??{file_path}")
                output_csv1 = input("엑셀 저장 경로를 입력하세요 :")
                uid_data = load_json(file_path)

                for room_id, uid in uid_data.items():
                    job_name = uid.split('/')[0]  # job name : '21b7'
                    uid_value = uid.split('/')[1]  # uid : '0559E31031701'
                    job_name1= (job_name + '/' + uid_value )
                
                    df = fetch_prometheus_metrics(
                        job_name= (job_name + '/' + uid_value ),
                        metrics=metrics,
                        start_time=yesterday_9am,
                        end_time=today_9am,
                        step=10,
                        output_csv=output_csv1,
                        room_id =room_id,
                    )





       



