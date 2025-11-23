"""
Main blueprint - Home and basic routes
"""
from flask import Blueprint, render_template, request, jsonify
from app.utils.cache import cached
import logging

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home page"""
    return render_template('home.html')


@main_bp.route('/monthly_report')
@cached(timeout=1800, key_prefix="monthly_report")
def monthly_report_page():
    """Monthly report page with caching"""
    import pandas as pd
    from app.utils.database import db_manager
    
    month = int(request.args.get('month', pd.Timestamp.now().month))
    year = int(request.args.get('year', pd.Timestamp.now().year))
    
    # Load data from database
    reports_df = db_manager.read_table('report')
    
    return render_template('monthly-report.html', 
                         reports=reports_df.to_dict('records'),
                         month=month,
                         year=year)


@main_bp.route('/refresh_cache', methods=['POST'])
def refresh_cache():
    """Refresh data from S3 to database"""
    from app.utils.s3_client import S3Manager
    from app.utils.database import db_manager
    from app.config import Config
    
    try:
        # Initialize S3
        s3_manager = S3Manager(
            bucket_name=Config.S3_BUCKET_NAME,
            aws_access_key=Config.AWS_ACCESS_KEY_ID,
            aws_secret_key=Config.AWS_SECRET_ACCESS_KEY,
            region=Config.AWS_DEFAULT_REGION
        )
        
        # List of CSV files to sync
        csv_files = [
            'report.csv',
            'frequencies.csv',
            'customer_locations.csv',
            'combined_firmware_reports.csv',
            'combined_vhealth_reports.csv',
            'combined_snapshot_reports.csv'
        ]
        
        for csv_file in csv_files:
            logger.info(f"Syncing {csv_file}")
            df = s3_manager.read_csv(csv_file)
            
            if not df.empty:
                table_name = csv_file.replace('.csv', '')
                db_manager.truncate_table(table_name)
                db_manager.write_table(df, table_name)
        
        return jsonify({'status': 'success', 'message': 'Cache refreshed'}), 200
        
    except Exception as e:
        logger.error(f"Error refreshing cache: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
