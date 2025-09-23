"""
Ganglioside Analyzer - Flask Main Application
산성 당지질 LC-MS/MS 데이터 자동 분석 웹 서비스
"""

import io
import os
import traceback
from datetime import datetime

import pandas as pd
from flask import Flask, jsonify, render_template, request, send_file
from flask_cors import CORS

# 분석 서비스 import
try:
    from backend.services.data_processor import \
        GangliosideDataProcessor as GangliosideProcessor
    from backend.services.regression_analyzer import RegressionAnalyzer
    from backend.services.visualization_service import VisualizationService

    print("✅ 실제 분석 모듈 로드 성공")
except ImportError as e:
    print(f"⚠️ 분석 모듈 로드 실패: {e}")
    print("더미 모듈을 사용합니다...")
    from backend.services.dummy import \
        DummyGangliosideDataProcessor as GangliosideProcessor
    from backend.services.dummy import \
        DummyVisualizationService as VisualizationService

    # 더미 RegressionAnalyzer 클래스
    class RegressionAnalyzer:
        def __init__(self):
            print("🔬 Dummy Regression Analyzer 초기화")

        def analyze(self, data):
            return {"message": "더미 회귀분석 결과"}


# Flask 앱 초기화
app = Flask(
    __name__,
    template_folder="backend/templates",
    static_folder="backend/static"
)
CORS(app)  # CORS 설정

# 설정
app.config.update(
    MAX_CONTENT_LENGTH=50 * 1024 * 1024,  # 50MB 최대 파일 크기
    UPLOAD_FOLDER="uploads",
    OUTPUT_FOLDER="outputs",
)

# 디렉토리 생성
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["OUTPUT_FOLDER"], exist_ok=True)

# 서비스 인스턴스 초기화
ganglioside_processor = GangliosideProcessor()
visualization_service = VisualizationService()
regression_analyzer = RegressionAnalyzer()

print("🧬 Ganglioside Analyzer Flask 서버 초기화 완료")


@app.route("/")
def index():
    """메인 페이지 - 인터랙티브 분석기"""
    return render_template("interactive_analyzer.html")


@app.route("/interactive")
def interactive_analyzer():
    """인터랙티브 분석기 페이지"""
    return render_template("interactive_analyzer.html")


@app.route("/simple")
def simple_analyzer():
    """기존 단순 분석기"""
    return render_template("analyzer.html")


@app.route("/api/health")
def health_check():
    """헬스 체크 엔드포인트"""
    return jsonify(
        {
            "status": "healthy",
            "service": "ganglioside-analyzer-flask",
            "version": "2.0.0",
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.route("/api/upload", methods=["POST"])
def upload_csv():
    """CSV 파일 업로드 및 기본 검증"""
    try:
        if "file" not in request.files:
            return jsonify({"error": "파일이 없습니다."}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "파일명이 없습니다."}), 400

        if not file.filename.endswith(".csv"):
            return jsonify(
                {"error": "CSV 파일만 업로드 가능합니다."}
            ), 400

        # CSV 읽기
        contents = file.read().decode("utf-8")
        df = pd.read_csv(io.StringIO(contents))

        # 필수 컬럼 검증
        required_columns = ["Name", "RT", "Volume", "Log P", "Anchor"]
        missing_columns = [
            col for col in required_columns if col not in df.columns
        ]

        if missing_columns:
            return jsonify({
                "error": f"필수 컬럼이 누락되었습니다: {missing_columns}"
            }), 400

        # 기본 통계
        stats = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "columns": df.columns.tolist(),
            "anchor_count": len(df[df["Anchor"] == "T"]),
            "rt_range": [float(df["RT"].min()), float(df["RT"].max())],
            "log_p_range": [
                float(df["Log P"].min()), float(df["Log P"].max())
            ],
            "sample_data": df.head(3).to_dict("records"),
        }

        return jsonify({
            "message": "파일 업로드 성공",
            "filename": file.filename,
            "stats": stats
        })

    except Exception as e:
        print(f"Upload error: {str(e)}")
        return jsonify(
            {"error": f"파일 처리 중 오류 발생: {str(e)}"}
        ), 500


@app.route("/api/analyze", methods=["POST"])
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

        # 설정 업데이트
        ganglioside_processor.update_settings(
            outlier_threshold=outlier_threshold,
            r2_threshold=r2_threshold,
            rt_tolerance=rt_tolerance,
        )

        # CSV 읽기
        contents = file.read().decode("utf-8")
        df = pd.read_csv(io.StringIO(contents))

        print(
            f"🔬 분석 시작: {len(df)}개 화합물, 모드: {data_type}"
        )
        print(
            f"⚙️ 설정: outlier={outlier_threshold}, "
            f"r2={r2_threshold}, rt={rt_tolerance}"
        )

        # 분석 실행
        results = ganglioside_processor.process_data(df, data_type=data_type)

        # 결과에 설정 정보 추가
        results["analysis_settings"] = {
            "outlier_threshold": outlier_threshold,
            "r2_threshold": r2_threshold,
            "rt_tolerance": rt_tolerance,
            "data_type": data_type,
            "analysis_timestamp": datetime.now().isoformat(),
        }

        success_rate = results['statistics']['success_rate']
        print(f"✅ 분석 완료: {success_rate:.1f}% 성공률")

        return jsonify({
            "message": "분석 완료",
            "filename": file.filename,
            "results": results
        })

    except Exception as e:
        print(f"Analysis error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": f"분석 중 오류 발생: {str(e)}"}), 500


@app.route("/api/visualize", methods=["POST"])
def create_visualizations():
    """시각화 생성"""
    try:
        data = request.get_json()
        if not data or "results" not in data:
            return jsonify(
                {"error": "분석 결과 데이터가 필요합니다."}
            ), 400

        results = data["results"]

        # 시각화 생성
        plots = visualization_service.create_all_plots(results)

        return jsonify({"message": "시각화 생성 완료", "plots": plots})

    except Exception as e:
        print(f"Visualization error: {str(e)}")
        return jsonify(
            {"error": f"시각화 생성 중 오류 발생: {str(e)}"}
        ), 500


@app.route("/api/visualize-3d", methods=["POST"])
def create_3d_visualization():
    """3D 분포 시각화 전용 엔드포인트"""
    try:
        data = request.get_json()
        if not data or "results" not in data:
            return jsonify(
                {"error": "분석 결과 데이터가 필요합니다."}
            ), 400

        results = data["results"]

        # 3D 시각화만 생성
        plot_html = visualization_service._create_3d_distribution_plot(results)

        # 구조화된 데이터도 함께 제공
        viz_data = visualization_service.create_visualization_data(results)

        return jsonify({
            "message": "3D 시각화 생성 완료",
            "plot_html": plot_html,
            "visualization_data": {
                "title": viz_data.title,
                "data_points": len(viz_data.x_data),
                "x_range": [min(viz_data.x_data), max(viz_data.x_data)] if viz_data.x_data else [0, 0],
                "y_range": [min(viz_data.y_data), max(viz_data.y_data)] if viz_data.y_data else [0, 0],
                "z_range": [min(viz_data.z_data), max(viz_data.z_data)] if viz_data.z_data else [0, 0],
                "axis_labels": {
                    "x": viz_data.x_label,
                    "y": viz_data.y_label,
                    "z": viz_data.z_label
                }
            }
        })

    except Exception as e:
        print(f"3D Visualization error: {str(e)}")
        return jsonify(
            {"error": f"3D 시각화 생성 중 오류 발생: {str(e)}"}
        ), 500


@app.route("/api/settings", methods=["GET", "POST"])
def manage_settings():
    """설정 관리"""
    try:
        if request.method == "GET":
            # 현재 설정 반환
            return jsonify(
                {
                    "current_settings": ganglioside_processor.get_settings(),
                    "default_settings": {
                        "outlier_threshold": 3.0,
                        "r2_threshold": 0.99,
                        "rt_tolerance": 0.1,
                    },
                    "setting_ranges": {
                        "outlier_threshold": {
                            "min": 1.0, "max": 5.0, "step": 0.1
                        },
                        "r2_threshold": {
                            "min": 0.90, "max": 0.999, "step": 0.001
                        },
                        "rt_tolerance": {
                            "min": 0.05, "max": 0.5, "step": 0.01
                        },
                    },
                }
            )

        elif request.method == "POST":
            # 설정 업데이트
            data = request.get_json()

            outlier_threshold = data.get("outlier_threshold", 3.0)
            r2_threshold = data.get("r2_threshold", 0.99)
            rt_tolerance = data.get("rt_tolerance", 0.1)

            # 설정 범위 검증
            if not (1.0 <= outlier_threshold <= 5.0):
                return jsonify({
                    "error": "outlier_threshold는 1.0-5.0 범위여야 합니다."
                }), 400
            if not (0.90 <= r2_threshold <= 0.999):
                return jsonify({
                    "error": "r2_threshold는 0.90-0.999 범위여야 합니다."
                }), 400
            if not (0.05 <= rt_tolerance <= 0.5):
                return jsonify({
                    "error": "rt_tolerance는 0.05-0.5 범위여야 합니다."
                }), 400

            # 설정 업데이트
            ganglioside_processor.update_settings(
                outlier_threshold=outlier_threshold,
                r2_threshold=r2_threshold,
                rt_tolerance=rt_tolerance,
            )

            return jsonify(
                {
                    "message": "설정이 업데이트되었습니다.",
                    "updated_settings": ganglioside_processor.get_settings(),
                    "timestamp": datetime.now().isoformat(),
                }
            )

    except Exception as e:
        print(f"Settings error: {str(e)}")
        return jsonify(
            {"error": f"설정 처리 중 오류 발생: {str(e)}"}
        ), 500


@app.route("/api/download-results", methods=["POST"])
def download_results():
    """분석 결과 다운로드"""
    try:
        data = request.get_json()
        if not data or "results" not in data:
            return jsonify(
                {"error": "분석 결과 데이터가 필요합니다."}
            ), 400

        results = data["results"]

        # CSV 생성
        csv_content = _generate_results_csv(results)

        # 파일 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ganglioside_analysis_results_{timestamp}.csv"
        filepath = os.path.join(app.config["OUTPUT_FOLDER"], filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(csv_content)

        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype="text/csv"
        )

    except Exception as e:
        print(f"Download error: {str(e)}")
        return jsonify(
            {"error": f"다운로드 중 오류 발생: {str(e)}"}
        ), 500


@app.route("/api/sample-test", methods=["POST"])
def sample_test():
    """샘플 데이터 테스트"""
    try:
        test_type = request.form.get("test_type", "basic")
        data_type = request.form.get("data_type", "Porcine")
        outlier_threshold = float(request.form.get("outlier_threshold", 3.0))
        r2_threshold = float(request.form.get("r2_threshold", 0.99))
        rt_tolerance = float(request.form.get("rt_tolerance", 0.1))

        # 샘플 데이터 생성
        if test_type == "basic":
            sample_data = _get_basic_sample_data()
        elif test_type == "complex":
            sample_data = _get_complex_sample_data()
        elif test_type == "challenge":
            sample_data = _get_challenge_sample_data()
        else:
            return jsonify(
                {"error": "지원하지 않는 테스트 타입입니다."}
            ), 400

        df = pd.DataFrame(sample_data)

        # 설정 업데이트
        ganglioside_processor.update_settings(
            outlier_threshold=outlier_threshold,
            r2_threshold=r2_threshold,
            rt_tolerance=rt_tolerance,
        )

        # 분석 실행
        results = ganglioside_processor.process_data(df, data_type=data_type)

        return jsonify(
            {
                "message": f"{test_type} 샘플 테스트 완료",
                "test_type": test_type,
                "results": results,
            }
        )

    except Exception as e:
        print(f"Sample test error: {str(e)}")
        return jsonify(
            {"error": f"샘플 테스트 중 오류 발생: {str(e)}"}
        ), 500


def _generate_results_csv(results):
    """분석 결과를 CSV 형태로 변환"""
    lines = [
        "Name,RT,Volume,Log P,Anchor,Status,Classification,"
        "Predicted_RT,Residual,Std_Residual,Outlier_Reason\n"
    ]

    # 유효 화합물
    for compound in results.get("valid_compounds", []):
        predicted_rt = compound.get("predicted_rt", "N/A")
        residual = compound.get("residual", "N/A")
        std_residual = compound.get("std_residual", "N/A")

        if isinstance(predicted_rt, (int, float)):
            predicted_rt = f"{predicted_rt:.3f}"
        if isinstance(residual, (int, float)):
            residual = f"{residual:.3f}"
        if isinstance(std_residual, (int, float)):
            std_residual = f"{std_residual:.3f}"

        lines.append(
            f'"{compound["Name"]}",{compound["RT"]},'
            f'{compound["Volume"]},{compound["Log P"]},'
            f'{compound["Anchor"]},Valid,"True Positive",'
            f'{predicted_rt},{residual},{std_residual},""\n'
        )

    # 이상치
    for outlier in results.get("outliers", []):
        predicted_rt = outlier.get("predicted_rt", "N/A")
        residual = outlier.get("residual", "N/A")
        std_residual = outlier.get("std_residual", "N/A")
        reason = outlier.get("outlier_reason", "Unknown").replace('"', '""')

        if isinstance(predicted_rt, (int, float)):
            predicted_rt = f"{predicted_rt:.3f}"
        if isinstance(residual, (int, float)):
            residual = f"{residual:.3f}"
        if isinstance(std_residual, (int, float)):
            std_residual = f"{std_residual:.3f}"

        lines.append(
            f'"{outlier["Name"]}",{outlier["RT"]},'
            f'{outlier["Volume"]},{outlier["Log P"]},'
            f'{outlier["Anchor"]},Outlier,"False Positive",'
            f'{predicted_rt},{residual},{std_residual},"{reason}"\n'
        )

    return "".join(lines)


def _get_basic_sample_data():
    """기본 샘플 데이터"""
    return {
        "Name": [
            "GD1a(36:1;O2)",
            "GM1a(36:1;O2)",
            "GM3(36:1;O2)",
            "GD3(36:1;O2)",
            "GT1b(36:1;O2)",
        ],
        "RT": [9.572, 10.452, 10.606, 10.126, 8.701],
        "Volume": [1000000, 500000, 2000000, 800000, 1200000],
        "Log P": [1.53, 4.00, 7.74, 5.27, -0.94],
        "Anchor": ["T", "F", "F", "T", "T"],
    }


def _get_complex_sample_data():
    """복합 샘플 데이터"""
    return {
        "Name": [
            "GD1a(36:1;O2)",
            "GD1b(36:1;O2)",
            "GD1a+OAc(36:1;O2)",
            "GM1a(34:1;O2)",
            "GM1a+2OAc(34:1;O2)",
            "GM3(36:1;O2)",
            "GD3(36:1;O2)",
            "GT1b(36:1;O2)",
            "GQ1c(36:1;O2)",
            "GP1(36:1;O2)",
            "GD1+dHex(36:1;O2)",
            "GD1+HexNAc(36:1;O2)",
        ],
        "RT": [
            9.572,
            9.823,
            10.125,
            10.452,
            11.234,
            10.606,
            10.126,
            8.701,
            8.234,
            7.851,
            9.823,
            9.572,
        ],
        "Volume": [
            1000000,
            850000,
            650000,
            500000,
            320000,
            2000000,
            800000,
            1200000,
            580000,
            300000,
            750000,
            690000,
        ],
        "Log P": [
            1.53,
            1.48,
            2.15,
            4.00,
            4.85,
            7.74,
            5.27,
            -0.94,
            -3.36,
            -5.88,
            1.48,
            1.53,
        ],
        "Anchor": ["T", "F", "F", "F", "F", "F", "T", "T", "F", "F", "F", "F"],
    }


def _get_challenge_sample_data():
    """도전 데이터"""
    return {
        "Name": [
            "GD1a(36:1;O2)",
            "GM1a(36:1;O2)",
            "GM3(36:1;O2)",
            "GD3(36:1;O2)",
            "GT1b(36:1;O2)",
            "Unknown_1(36:1;O2)",
            "Contamination(36:1;O2)",
            "Noise_signal(unknown)",
            "Fragment_ion(36:1;O2)",
            "Artifact(36:1;O2)",
        ],
        "RT": [
            9.572,
            10.852,
            10.306,
            11.726,
            8.201,
            12.543,
            15.234,
            8.765,
            10.456,
            14.123,
        ],
        "Volume": [
            1000000,
            500000,
            2000000,
            800000,
            1200000,
            450000,
            150000,
            50000,
            2500000,
            80000,
        ],
        "Log P": [
            1.53, 4.20, 7.94, 5.47, -0.74, 8.25, 12.45, -2.15, 7.82, 9.87
        ],
        "Anchor": ["T", "F", "F", "F", "T", "F", "F", "F", "F", "F"],
    }


if __name__ == "__main__":
    print("🚀 Ganglioside Analyzer Flask 서버 시작")
    print("🌐 http://localhost:5000 에서 접속 가능")
    app.run(host="0.0.0.0", port=5000, debug=True)
