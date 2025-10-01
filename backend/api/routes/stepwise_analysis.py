"""
Stepwise Analysis API Routes
Provides rule-by-rule analysis endpoints for interactive frontend control
"""

from flask import Blueprint, jsonify, request, session
import pandas as pd
import io
from ...services.stepwise_analyzer import StepwiseAnalyzer

stepwise_bp = Blueprint('stepwise', __name__)

# Global analyzer instance (in production, use session storage or database)
analyzers = {}


def get_analyzer(session_id: str) -> StepwiseAnalyzer:
    """Get or create analyzer for session"""
    if session_id not in analyzers:
        analyzers[session_id] = StepwiseAnalyzer()
    return analyzers[session_id]


@stepwise_bp.route('/api/stepwise/upload', methods=['POST'])
def upload_data():
    """
    Step 0: Upload and preprocess data

    Request: CSV file upload
    Returns: Preprocessing results with feature statistics
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400

        # Read CSV
        content = file.read().decode('utf-8')
        df = pd.read_csv(io.StringIO(content))

        # Get session ID (or generate one)
        session_id = request.args.get('session_id', 'default')
        data_type = request.args.get('data_type', 'Porcine')

        # Get analyzer and load data
        analyzer = get_analyzer(session_id)
        analyzer.reset()  # Reset previous state

        result = analyzer.load_data(df, data_type)
        result['session_id'] = session_id

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stepwise_bp.route('/api/stepwise/rule1', methods=['POST'])
def execute_rule1():
    """
    Step 1: Execute Rule 1 - Prefix-based Regression

    Returns: Regression results with classification
    """
    try:
        session_id = request.json.get('session_id', 'default')
        analyzer = get_analyzer(session_id)

        result = analyzer.execute_rule1()

        if 'error' in result:
            return jsonify(result), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stepwise_bp.route('/api/stepwise/rule23', methods=['POST'])
def execute_rule23():
    """
    Step 2: Execute Rules 2-3 - Sugar Count & Isomer Classification

    Returns: Sugar analysis and isomer detection results
    """
    try:
        session_id = request.json.get('session_id', 'default')
        analyzer = get_analyzer(session_id)

        result = analyzer.execute_rule23()

        if 'error' in result:
            return jsonify(result), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stepwise_bp.route('/api/stepwise/rule4', methods=['POST'])
def execute_rule4():
    """
    Step 3: Execute Rule 4 - O-acetylation Validation

    Returns: O-acetylation validation results
    """
    try:
        session_id = request.json.get('session_id', 'default')
        analyzer = get_analyzer(session_id)

        result = analyzer.execute_rule4()

        if 'error' in result:
            return jsonify(result), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stepwise_bp.route('/api/stepwise/rule5', methods=['POST'])
def execute_rule5():
    """
    Step 4: Execute Rule 5 - Fragmentation Detection

    Returns: Fragmentation analysis results
    """
    try:
        session_id = request.json.get('session_id', 'default')
        analyzer = get_analyzer(session_id)

        result = analyzer.execute_rule5()

        if 'error' in result:
            return jsonify(result), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stepwise_bp.route('/api/stepwise/summary', methods=['GET'])
def get_summary():
    """
    Get final analysis summary

    Returns: Comprehensive summary of all rules
    """
    try:
        session_id = request.args.get('session_id', 'default')
        analyzer = get_analyzer(session_id)

        result = analyzer.get_final_summary()

        if 'error' in result:
            return jsonify(result), 400

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stepwise_bp.route('/api/stepwise/reset', methods=['POST'])
def reset_analysis():
    """
    Reset analysis state

    Returns: Confirmation
    """
    try:
        session_id = request.json.get('session_id', 'default')

        if session_id in analyzers:
            analyzers[session_id].reset()
            return jsonify({'status': 'reset', 'session_id': session_id}), 200
        else:
            return jsonify({'status': 'no_session', 'session_id': session_id}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stepwise_bp.route('/api/stepwise/status', methods=['GET'])
def get_status():
    """
    Get current analysis status

    Returns: Current state and completed rules
    """
    try:
        session_id = request.args.get('session_id', 'default')

        if session_id not in analyzers:
            return jsonify({
                'status': 'no_session',
                'session_id': session_id,
                'analysis_state': 'not_started'
            }), 200

        analyzer = analyzers[session_id]

        return jsonify({
            'status': 'active',
            'session_id': session_id,
            'analysis_state': analyzer.analysis_state,
            'completed_rules': list(analyzer.rule_results.keys())
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
