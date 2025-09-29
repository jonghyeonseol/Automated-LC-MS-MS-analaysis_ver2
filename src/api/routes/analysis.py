"""
Analysis API Routes - 데이터 분석 관련 API 엔드포인트들
"""

import io
import traceback
from datetime import datetime

import pandas as pd
import numpy as np
from flask import Blueprint, jsonify, request, send_file

# 전역 변수로 서비스 인스턴스들을 가져올 예정
processor = None
regression_analyzer = None
visualization_service = None

# Blueprint 생성
analysis_bp = Blueprint('analysis', __name__, url_prefix='/api')


def init_services(ganglioside_processor, reg_analyzer, vis_service):
    """서비스 인스턴스들을 초기화"""
    global processor, regression_analyzer, visualization_service
    processor = ganglioside_processor
    regression_analyzer = reg_analyzer
    visualization_service = vis_service


def convert_to_serializable(obj):
    """NumPy/pandas 객체를 JSON 직렬화 가능한 형태로 변환"""
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    return obj


@analysis_bp.route("/upload", methods=["POST"])
def upload_csv():
    """CSV 파일 업로드 및 기본 검증"""
    try:
        if "file" not in request.files:
            return jsonify({"error": "파일이 없습니다."}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "파일이 선택되지 않았습니다."}), 400

        if not file.filename.lower().endswith('.csv'):
            return jsonify({"error": "CSV 파일만 업로드 가능합니다."}), 400

        # CSV 파일 읽기
        try:
            df = pd.read_csv(file)
        except Exception as e:
            return jsonify({"error": f"CSV 파일을 읽을 수 없습니다: {str(e)}"}), 400

        # 필수 컬럼 검사
        required_columns = ["Name", "RT", "Volume"]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            return jsonify({
                "error": f"필수 컬럼이 누락되었습니다: {', '.join(missing_columns)}"
            }), 400

        # 기본 통계 정보 반환
        file_info = {
            "filename": file.filename,
            "rows": len(df),
            "columns": list(df.columns),
            "preview": df.head().to_dict('records'),
            "upload_time": datetime.now().isoformat()
        }

        return jsonify({
            "message": "파일 업로드 성공",
            "file_info": file_info
        })

    except Exception as e:
        print(f"Upload error: {str(e)}")
        return jsonify(
            {"error": f"파일 처리 중 오류 발생: {str(e)}"}
        ), 500


@analysis_bp.route("/analyze", methods=["POST"])
def analyze_data():
    """데이터 분석 실행"""
    try:
        # 파일 및 설정 가져오기
        if "file" not in request.files:
            return jsonify({"error": "분석할 파일이 없습니다."}), 400

        file = request.files["file"]
        data_type = request.form.get("data_type", "Porcine")
        outlier_threshold = float(request.form.get("outlier_threshold", 3.0))
        r2_threshold = float(request.form.get("r2_threshold", 0.99))
        rt_tolerance = float(request.form.get("rt_tolerance", 0.1))

        # CSV 파일 읽기
        df = pd.read_csv(file)
        print(f"🔬 분석 시작: {len(df)}개 화합물, 모드: {data_type}")

        # 설정 업데이트
        processor.update_settings(
            outlier_threshold=outlier_threshold,
            r2_threshold=r2_threshold,
            rt_tolerance=rt_tolerance,
        )

        # 데이터 분석 실행
        results = processor.process_data(df, data_type)

        # 직렬화 가능한 형태로 변환
        serialized_results = convert_to_serializable(results)

        return jsonify({
            "message": "분석 완료",
            "results": serialized_results,
            "settings": {
                "data_type": data_type,
                "outlier_threshold": outlier_threshold,
                "r2_threshold": r2_threshold,
                "rt_tolerance": rt_tolerance,
            },
            "analysis_time": datetime.now().isoformat()
        })

    except Exception as e:
        error_msg = f"분석 중 오류 발생: {str(e)}"
        print(f"Analysis error: {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": error_msg}), 500


@analysis_bp.route("/sample-test", methods=["POST"])
def sample_test():
    """샘플 데이터 테스트"""
    try:
        # 요청에서 설정 가져오기
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON 데이터가 필요합니다."}), 400

        data_type = data.get("data_type", "Porcine")
        outlier_threshold = float(data.get("outlier_threshold", 3.0))
        r2_threshold = float(data.get("r2_threshold", 0.99))
        rt_tolerance = float(data.get("rt_tolerance", 0.1))

        # 샘플 데이터 생성
        sample_data = pd.DataFrame({
            "Name": [
                "GD1a(36:1;O2)",
                "GM1a(36:1;O2)",
                "GM3(36:1;O2)",
                "GD3(36:1;O2)",
                "GT1b(34:1;O2)"
            ],
            "RT": [9.572, 10.452, 10.606, 10.126, 8.701],
            "Volume": [1000000, 500000, 2000000, 800000, 1200000]
        })

        print(f"🔬 분석 시작: {len(sample_data)}개 화합물, 모드: {data_type}")

        # 설정 업데이트
        processor.update_settings(
            outlier_threshold=outlier_threshold,
            r2_threshold=r2_threshold,
            rt_tolerance=rt_tolerance,
        )

        # 데이터 분석 실행
        results = processor.process_data(sample_data, data_type)

        # 직렬화 가능한 형태로 변환
        serialized_results = convert_to_serializable(results)

        return jsonify({
            "message": "샘플 데이터 분석 완료",
            "results": serialized_results,
            "settings": {
                "data_type": data_type,
                "outlier_threshold": outlier_threshold,
                "r2_threshold": r2_threshold,
                "rt_tolerance": rt_tolerance,
            },
            "sample_data": sample_data.to_dict('records'),
            "analysis_time": datetime.now().isoformat()
        })

    except Exception as e:
        error_msg = f"샘플 테스트 중 오류 발생: {str(e)}"
        print(f"Sample test error: {error_msg}")
        return jsonify({"error": error_msg}), 500


@analysis_bp.route("/download-results", methods=["POST"])
def download_results():
    """분석 결과 다운로드"""
    try:
        data = request.get_json()
        if not data or "results" not in data:
            return jsonify({"error": "분석 결과 데이터가 없습니다."}), 400

        results = data["results"]

        # CSV 형태로 변환
        output_data = []

        # 유효한 화합물들
        if "valid_compounds" in results:
            for compound in results["valid_compounds"]:
                output_data.append({
                    "Name": compound.get("Name", ""),
                    "RT": compound.get("RT", ""),
                    "Volume": compound.get("Volume", ""),
                    "Classification": "Valid",
                    "Log P": compound.get("Log P", ""),
                    "Prefix": compound.get("prefix", ""),
                    "Suffix": compound.get("suffix", "")
                })

        # 이상치들
        if "outliers" in results:
            for outlier in results["outliers"]:
                output_data.append({
                    "Name": outlier.get("Name", ""),
                    "RT": outlier.get("RT", ""),
                    "Volume": outlier.get("Volume", ""),
                    "Classification": "Outlier",
                    "Log P": outlier.get("Log P", ""),
                    "Prefix": outlier.get("prefix", ""),
                    "Suffix": outlier.get("suffix", ""),
                    "Outlier_Reason": outlier.get("outlier_reason", "")
                })

        # DataFrame으로 변환 후 CSV 생성
        df = pd.DataFrame(output_data)
        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)

        # 파일로 전송
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'ganglioside_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )

    except Exception as e:
        print(f"Download error: {str(e)}")
        return jsonify({"error": f"다운로드 중 오류 발생: {str(e)}"}), 500