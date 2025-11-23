"""
Main blueprint - All routes from original version, adapted for Cloud Run
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, Response, send_file
from app.utils.cache import cached
from app.utils.database import db_manager
from app.utils.s3_client import S3Manager
from app.config import Config
import pandas as pd
import json
import logging
from datetime import datetime
from io import StringIO

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

# Template constants
TEMPLATE_ALERTS_REPORT = 'alerts-report.html'
TEMPLATE_MONTHLY_REPORTS = 'monthly-report.html'
TEMPLATE_ANTIVIRUS_ASSET_REPORT = 'antivirus-asset-report.html'
TEMPLATE_BASE = 'base-template.html'
TEMPLATE_CERTIFICATE_EXPIRY_REPORT = 'certificate-expiry-report.html'
TEMPLATE_FIRMWARE_REPORTS = 'firmware-report.html'
TEMPLATE_HOME = 'home.html'
TEMPLATE_LOADING_PAGE = 'loading-page.html'
TEMPLATE_LOGIN_PAGE = 'login-page.html'
TEMPLATE_MANAGE_EXCLUSIONS = 'manage-exclusions.html'
TEMPLATE_NETWORK_UTILIZATION_REPORT = 'network-utilization-report.html'
TEMPLATE_PASSWORD_EXPIRATION_REPORT = 'password-expiration-report.html'
TEMPLATE_SNAPSHOT_REPORTS = 'snapshot-report.html'
TEMPLATE_STATISTICS_REPORT = 'statistics-report.html'
TEMPLATE_VDISK_REPORT = 'vdisk-report.html'
TEMPLATE_VMWARE_VERSIONS_REPORT = 'vmware-versions-report.html'
TEMPLATE_VHEALTH_REPORTS = 'vhealth-report.html'
TEMPLATE_VHOSTS_REPORT = 'vhosts-report.html'
TEMPLATE_VINFO_REPORT = 'vinfo-report.html'
TEMPLATE_ENV_VERSIONS_REPORT = 'env-versions.html'

# Redirect constants
REDIRECT_MONTHLY_REPORT = 'main.monthly_report_page'
REDIRECT_SNAPSHOT_REPORT = 'main.snapshot_report_page'
REDIRECT_VHEALTH_REPORT = 'main.vhealth_report_page'
REDIRECT_FIRMWARE_REPORT = 'main.firmware_report_page'
REDIRECT_VINFO_REPORT = 'main.vinfo_report_page'
REDIRECT_VDISK_REPORT = 'main.vdisk_report_page'
REDIRECT_VHOSTS_REPORT = 'main.vhosts_report_page'
REDIRECT_NETWORK_UTILIZATION_REPORT = 'main.network_utilization_report_page'
REDIRECT_CERTIFICATE_EXPIRY_REPORT = 'main.certificate_expiry_report_page'
REDIRECT_PASSWORD_EXPIRATION_REPORT = 'main.password_expiration_report_page'
REDIRECT_ANTIVIRUS_ASSET_REPORT = 'main.antivirus_asset_report_page'
REDIRECT_STATISTICS_REPORT = 'main.statistics_report_page'
REDIRECT_ENV_VERSIONS_REPORT = 'main.env_versions_report_page'


def get_s3_manager():
    """Get S3 manager instance"""
    return S3Manager(
        bucket_name=Config.S3_BUCKET_NAME,
        aws_access_key=Config.AWS_ACCESS_KEY_ID,
        aws_secret_key=Config.AWS_SECRET_ACCESS_KEY,
        region=Config.AWS_DEFAULT_REGION
    )


@main_bp.route('/')
def index():
    """Home page"""
    return render_template(TEMPLATE_HOME)


@main_bp.route('/snapshot_report')
def snapshot_report_page():
    """Snapshot report page - reads directly from S3"""
    try:
        s3_manager = get_s3_manager()
        snapshot_reports_df = s3_manager.read_csv('combined_snapshot_reports.csv')
        if snapshot_reports_df.empty:
            return render_template(TEMPLATE_SNAPSHOT_REPORTS, table_data=[])
        table_data = snapshot_reports_df.to_dict(orient='records')
        return render_template(TEMPLATE_SNAPSHOT_REPORTS, table_data=table_data)
    except Exception as e:
        logger.error(f"Error in snapshot_report_page: {e}", exc_info=True)
        return render_template(TEMPLATE_SNAPSHOT_REPORTS, table_data=[])


@main_bp.route('/vhealth_report')
def vhealth_report_page():
    """vHealth report page - reads directly from S3"""
    try:
        s3_manager = get_s3_manager()
        combined_vhealth_df = s3_manager.read_csv('combined_vhealth_reports.csv')
        if combined_vhealth_df.empty:
            return render_template(TEMPLATE_VHEALTH_REPORTS, table_data='[]')
        table_data = combined_vhealth_df.to_dict(orient='records')
        table_data_json = json.dumps(table_data)
        return render_template(TEMPLATE_VHEALTH_REPORTS, table_data=table_data_json)
    except Exception as e:
        logger.error(f"Error in vhealth_report_page: {e}", exc_info=True)
        return render_template(TEMPLATE_VHEALTH_REPORTS, table_data='[]')


@main_bp.route('/firmware_report')
def firmware_report_page():
    """Firmware report page - reads directly from S3"""
    try:
        s3_manager = get_s3_manager()
        combined_firmware_df = s3_manager.read_csv('combined_firmware_reports.csv')
        customer_locations_df = s3_manager.read_csv('customer_locations.csv')
        
        if combined_firmware_df.empty or customer_locations_df.empty:
            return render_template(TEMPLATE_FIRMWARE_REPORTS, table_data=[], customers=[], locations=[])
        
        # Find location column names (case-insensitive)
        firmware_loc_col = None
        for col in ['Location', 'location', 'LOCATION']:
            if col in combined_firmware_df.columns:
                firmware_loc_col = col
                break
        
        customer_loc_col = None
        for col in ['location', 'Location', 'LOCATION']:
            if col in customer_locations_df.columns:
                customer_loc_col = col
                break
        
        if not firmware_loc_col or not customer_loc_col:
            logger.error(f"Location columns not found. Firmware: {combined_firmware_df.columns.tolist()}, Customer: {customer_locations_df.columns.tolist()}")
            return render_template(TEMPLATE_FIRMWARE_REPORTS, table_data=[], customers=[], locations=[])
        
        combined_firmware_df = combined_firmware_df.merge(
            customer_locations_df, left_on=firmware_loc_col, right_on=customer_loc_col, how='left'
        )
        
        # Find customer column
        customer_col = None
        for col in ['Customer', 'customer', 'CUSTOMER']:
            if col in customer_locations_df.columns:
                customer_col = col
                break
        
        if customer_col and 'Customer' not in combined_firmware_df.columns:
            combined_firmware_df['Customer'] = combined_firmware_df[customer_loc_col].map(
                customer_locations_df.set_index(customer_loc_col)[customer_col]
            )
        
        table_data = combined_firmware_df.to_dict(orient='records')
        customers = sorted(customer_locations_df[customer_col].unique()) if customer_col else []
        locations = sorted(customer_locations_df[customer_loc_col].unique())
        
        return render_template(TEMPLATE_FIRMWARE_REPORTS, table_data=table_data, customers=customers, locations=locations)
    except Exception as e:
        logger.error(f"Error in firmware_report_page: {e}", exc_info=True)
        return render_template(TEMPLATE_FIRMWARE_REPORTS, table_data=[], customers=[], locations=[])


@main_bp.route('/vinfo_report')
def vinfo_report_page():
    """vInfo report page"""
    rvtools_vinfo_df = db_manager.read_table('rvtools_vinfo')
    
    if 'Location' not in rvtools_vinfo_df.columns:
        raise KeyError("'Location' column is missing from rvtools_vinfo_df")
    
    table_data = rvtools_vinfo_df.to_dict(orient='records')
    customers = sorted(rvtools_vinfo_df['Customer'].unique())
    locations = sorted(rvtools_vinfo_df['Location'].unique())
    
    return render_template(TEMPLATE_VINFO_REPORT, table_data=table_data, customers=customers, locations=locations)


@main_bp.route('/vdisk_report')
def vdisk_report_page():
    """vDisk report page - reads directly from S3"""
    try:
        s3_manager = get_s3_manager()
        combined_vdisk_reports_df = s3_manager.read_csv('combined_vdisk_reports.csv')
        if combined_vdisk_reports_df.empty:
            return render_template(TEMPLATE_VDISK_REPORT, table_data=[])
        table_data = combined_vdisk_reports_df.to_dict(orient='records')
        return render_template(TEMPLATE_VDISK_REPORT, table_data=table_data)
    except Exception as e:
        logger.error(f"Error in vdisk_report_page: {e}", exc_info=True)
        return render_template(TEMPLATE_VDISK_REPORT, table_data=[])


@main_bp.route('/vhosts_report')
def vhosts_report_page():
    """vHosts report page - reads directly from S3"""
    try:
        s3_manager = get_s3_manager()
        combined_vhosts_reports_df = s3_manager.read_csv('combined_vhosts_reports.csv')
        if combined_vhosts_reports_df.empty:
            return render_template(TEMPLATE_VHOSTS_REPORT, table_data=[])
        table_data = combined_vhosts_reports_df.to_dict(orient='records')
        return render_template(TEMPLATE_VHOSTS_REPORT, table_data=table_data)
    except Exception as e:
        logger.error(f"Error in vhosts_report_page: {e}", exc_info=True)
        return render_template(TEMPLATE_VHOSTS_REPORT, table_data=[])


@main_bp.route('/statistics_report')
def statistics_report_page():
    """Statistics report page - reads directly from S3"""
    try:
        s3_manager = get_s3_manager()
        vrops_alerts_df = s3_manager.read_csv('vrops_alerts_historical.csv')
        
        if vrops_alerts_df.empty:
            return render_template(TEMPLATE_STATISTICS_REPORT, table_data=[], locations=[])
        
        # Check if required columns exist, use alternatives if needed
        date_col = 'date' if 'date' in vrops_alerts_df.columns else 'Date' if 'Date' in vrops_alerts_df.columns else None
        location_col = 'location' if 'location' in vrops_alerts_df.columns else 'Location' if 'Location' in vrops_alerts_df.columns else None
        customer_col = 'customer' if 'customer' in vrops_alerts_df.columns else 'Customer' if 'Customer' in vrops_alerts_df.columns else None
        
        if not date_col or not location_col:
            logger.error(f"Missing required columns. Available: {vrops_alerts_df.columns.tolist()}")
            return render_template(TEMPLATE_STATISTICS_REPORT, table_data=[], locations=[])
        
        vrops_alerts_df['date'] = pd.to_datetime(vrops_alerts_df[date_col], errors='coerce')
        for col in ['critical', 'immediate', 'warning', 'total']:
            if col in vrops_alerts_df.columns:
                vrops_alerts_df[col] = vrops_alerts_df[col].fillna(0).astype(int)
            else:
                vrops_alerts_df[col] = 0
        
        vrops_alerts_df = vrops_alerts_df.sort_values(by=[location_col, 'date'])
        vrops_alerts_df['critical_diff'] = vrops_alerts_df.groupby(location_col)['critical'].diff()
        latest_data = vrops_alerts_df.sort_values('date', ascending=False).drop_duplicates(location_col)
        
        table_data = []
        for _, row in latest_data.iterrows():
            critical_diff = row['critical_diff']
            color = '#f8d7da' if critical_diff > 0 else '#d4edda' if critical_diff < 0 else ''
            table_data.append({
                'customer': row.get(customer_col, 'Unknown') if customer_col else 'Unknown',
                'date': row['date'].strftime('%Y-%m-%d') if pd.notna(row['date']) else 'Missing',
                'location': row[location_col],
                'critical': int(row['critical']),
                'immediate': int(row['immediate']),
                'warning': int(row['warning']),
                'total': int(row['total']),
                'color': color
            })
        
        locations = vrops_alerts_df[location_col].unique() if location_col else []
        return render_template(TEMPLATE_STATISTICS_REPORT, table_data=table_data, locations=locations)
    except Exception as e:
        logger.error(f"Error in statistics_report_page: {e}", exc_info=True)
        return render_template(TEMPLATE_STATISTICS_REPORT, table_data=[], locations=[])


@main_bp.route('/network_utilization_report')
def network_utilization_report_page():
    """Network utilization report page - reads directly from S3"""
    try:
        s3_manager = get_s3_manager()
        combined_network_utilization_df = s3_manager.read_csv('combined_network_utilization_report.csv')
        
        # Load exclusions from S3
        excluded_networks_df = pd.DataFrame(columns=['Network', 'Location'])
        try:
            s3_manager = get_s3_manager()
            excluded_networks_df = s3_manager.read_csv('excluded_networks.csv')
            if excluded_networks_df.empty or 'Network' not in excluded_networks_df.columns or 'Location' not in excluded_networks_df.columns:
                excluded_networks_df = pd.DataFrame(columns=['Network', 'Location'])
        except Exception as e:
            logger.warning(f"Could not load exclusions from S3: {e}")
        
        # Find column names
        network_col = None
        location_col = None
        for col in ['Network', 'network', 'NETWORK']:
            if col in combined_network_utilization_df.columns:
                network_col = col
                break
        for col in ['Location', 'location', 'LOCATION']:
            if col in combined_network_utilization_df.columns:
                location_col = col
                break
        
        # Exclude specified networks
        if not excluded_networks_df.empty and network_col and location_col:
            exclusions = excluded_networks_df[['Network', 'Location']].apply(tuple, axis=1)
            combined_network_utilization_df = combined_network_utilization_df[
                ~combined_network_utilization_df[[network_col, location_col]].apply(tuple, axis=1).isin(exclusions)
            ]
        
        table_data = combined_network_utilization_df.to_dict(orient='records')
        
        customer_locations_df = s3_manager.read_csv('customer_locations.csv')
        if customer_locations_df.empty:
            return render_template(TEMPLATE_NETWORK_UTILIZATION_REPORT, table_data=table_data, locations=[], customers=[])
        
        # Find location and customer columns
        loc_col = None
        cust_col = None
        for col in ['location', 'Location', 'LOCATION']:
            if col in customer_locations_df.columns:
                loc_col = col
                break
        for col in ['Customer', 'customer', 'CUSTOMER']:
            if col in customer_locations_df.columns:
                cust_col = col
                break
        
        locations = sorted(customer_locations_df[loc_col].unique()) if loc_col else []
        customers = sorted(customer_locations_df[cust_col].unique()) if cust_col else []
        
        return render_template(TEMPLATE_NETWORK_UTILIZATION_REPORT, table_data=table_data, locations=locations, customers=customers)
    except Exception as e:
        logger.error(f"Error in network_utilization_report_page: {e}", exc_info=True)
        return render_template(TEMPLATE_NETWORK_UTILIZATION_REPORT, table_data=[], locations=[], customers=[])


@main_bp.route('/certificate_expiry_report')
def certificate_expiry_report_page():
    """Certificate expiry report page - reads directly from S3"""
    try:
        s3_manager = get_s3_manager()
        certificate_expiry_df = s3_manager.read_csv('combined_certificate_expiry_reports.csv')
        table_data = certificate_expiry_df.to_dict(orient='records') if not certificate_expiry_df.empty else []
        
        customer_locations_df = s3_manager.read_csv('customer_locations.csv')
        if customer_locations_df.empty:
            return render_template(TEMPLATE_CERTIFICATE_EXPIRY_REPORT, table_data=table_data, customers=[], locations=[])
        
        # Find columns
        loc_col = None
        cust_col = None
        for col in ['location', 'Location', 'LOCATION']:
            if col in customer_locations_df.columns:
                loc_col = col
                break
        for col in ['Customer', 'customer', 'CUSTOMER']:
            if col in customer_locations_df.columns:
                cust_col = col
                break
        
        customers = sorted(customer_locations_df[cust_col].unique()) if cust_col else []
        locations = sorted(customer_locations_df[loc_col].unique()) if loc_col else []
        return render_template(TEMPLATE_CERTIFICATE_EXPIRY_REPORT, table_data=table_data, customers=customers, locations=locations)
    except Exception as e:
        logger.error(f"Error in certificate_expiry_report_page: {e}", exc_info=True)
        return render_template(TEMPLATE_CERTIFICATE_EXPIRY_REPORT, table_data=[], customers=[], locations=[])


@main_bp.route('/password_expiration_report')
def password_expiration_report_page():
    """Password expiration report page - reads directly from S3"""
    try:
        s3_manager = get_s3_manager()
        password_expiration_df = s3_manager.read_csv('combined_password_expiration_reports.csv')
        table_data = password_expiration_df.to_dict(orient='records') if not password_expiration_df.empty else []
        
        customer_locations_df = s3_manager.read_csv('customer_locations.csv')
        if customer_locations_df.empty:
            return render_template(TEMPLATE_PASSWORD_EXPIRATION_REPORT, table_data=table_data, customers=[], locations=[])
        
        # Find columns
        loc_col = None
        cust_col = None
        for col in ['location', 'Location', 'LOCATION']:
            if col in customer_locations_df.columns:
                loc_col = col
                break
        for col in ['Customer', 'customer', 'CUSTOMER']:
            if col in customer_locations_df.columns:
                cust_col = col
                break
        
        customers = sorted(customer_locations_df[cust_col].unique()) if cust_col else []
        locations = sorted(customer_locations_df[loc_col].unique()) if loc_col else []
        return render_template(TEMPLATE_PASSWORD_EXPIRATION_REPORT, table_data=table_data, customers=customers, locations=locations)
    except Exception as e:
        logger.error(f"Error in password_expiration_report_page: {e}", exc_info=True)
        return render_template(TEMPLATE_PASSWORD_EXPIRATION_REPORT, table_data=[], customers=[], locations=[])


@main_bp.route('/antivirus_asset_report')
def antivirus_asset_report_page():
    """Antivirus asset report page - reads directly from S3"""
    try:
        s3_manager = get_s3_manager()
        combined_antivirus_asset_report_df = s3_manager.read_csv('combined_antivirus_asset_reports.csv')
        table_data = combined_antivirus_asset_report_df.to_dict(orient='records') if not combined_antivirus_asset_report_df.empty else []
        
        customer_locations_df = s3_manager.read_csv('customer_locations.csv')
        if customer_locations_df.empty:
            return render_template(TEMPLATE_ANTIVIRUS_ASSET_REPORT, table_data=table_data, customers=[], locations=[])
        
        # Find columns
        loc_col = None
        cust_col = None
        for col in ['location', 'Location', 'LOCATION']:
            if col in customer_locations_df.columns:
                loc_col = col
                break
        for col in ['Customer', 'customer', 'CUSTOMER']:
            if col in customer_locations_df.columns:
                cust_col = col
                break
        
        customers = sorted(customer_locations_df[cust_col].unique()) if cust_col else []
        locations = sorted(customer_locations_df[loc_col].unique()) if loc_col else []
        return render_template(TEMPLATE_ANTIVIRUS_ASSET_REPORT, table_data=table_data, customers=customers, locations=locations)
    except Exception as e:
        logger.error(f"Error in antivirus_asset_report_page: {e}", exc_info=True)
        return render_template(TEMPLATE_ANTIVIRUS_ASSET_REPORT, table_data=[], customers=[], locations=[])


@main_bp.route('/env_versions_report')
def env_versions_report_page():
    """Environment versions report page - reads directly from S3"""
    try:
        s3_manager = get_s3_manager()
        combined_non_vcf_inventory_df = s3_manager.read_csv('combined_non_vcf_inventory.csv')
        combined_vcf_inventory_df = s3_manager.read_csv('combined_vcf_inventory.csv')
        
        if combined_non_vcf_inventory_df.empty and combined_vcf_inventory_df.empty:
            return render_template(TEMPLATE_ENV_VERSIONS_REPORT, table_data=[])
        
        combined_both_inventory_df = pd.concat([combined_non_vcf_inventory_df, combined_vcf_inventory_df], ignore_index=True)
        
        # Find date column
        date_col = None
        for col in ['Report Date', 'report_date', 'REPORT_DATE', 'Date', 'date']:
            if col in combined_both_inventory_df.columns:
                date_col = col
                break
        
        if date_col:
            combined_both_inventory_df['Report Date'] = pd.to_datetime(combined_both_inventory_df[date_col], errors='coerce')
            if combined_both_inventory_df['Report Date'].dt.time.any():
                combined_both_inventory_df['Report Date'] = combined_both_inventory_df['Report Date'].dt.date
        
        # Find required columns for deduplication
        dedup_cols = []
        for col in ['Customer', 'Location', 'Report Date', 'VM', 'Name']:
            if col in combined_both_inventory_df.columns:
                dedup_cols.append(col)
        
        if dedup_cols:
            combined_both_inventory_df = combined_both_inventory_df.drop_duplicates(subset=dedup_cols)
        
        table_data = combined_both_inventory_df.to_dict(orient='records')
        return render_template(TEMPLATE_ENV_VERSIONS_REPORT, table_data=table_data)
    except Exception as e:
        logger.error(f"Error in env_versions_report_page: {e}", exc_info=True)
        return render_template(TEMPLATE_ENV_VERSIONS_REPORT, table_data=[])


@main_bp.route('/alerts_report')
def alerts_report_page():
    """Alerts report page - reads directly from S3"""
    try:
        location = request.args.get('location')
        s3_manager = get_s3_manager()
        vrops_list_of_alerts_df = s3_manager.read_csv('combined_vrops_list_of_alerts.csv')
        
        if vrops_list_of_alerts_df.empty:
            return render_template(TEMPLATE_ALERTS_REPORT, alerts_data=[])
        
        # Find location column
        location_col = None
        for col in ['Location', 'location', 'LOCATION']:
            if col in vrops_list_of_alerts_df.columns:
                location_col = col
                break
        
        if location and location_col:
            filtered_alerts = vrops_list_of_alerts_df[vrops_list_of_alerts_df[location_col] == location]
        else:
            filtered_alerts = vrops_list_of_alerts_df
        
        alerts_data = filtered_alerts.to_dict(orient='records')
        return render_template(TEMPLATE_ALERTS_REPORT, alerts_data=alerts_data)
    except Exception as e:
        logger.error(f"Error in alerts_report_page: {e}", exc_info=True)
        return render_template(TEMPLATE_ALERTS_REPORT, alerts_data=[])


@main_bp.route('/monthly_report')
@cached(timeout=1800, key_prefix="monthly_report")
def monthly_report_page():
    """Monthly report page - reads directly from S3"""
    month = int(request.args.get('month', pd.Timestamp.now().month))
    year = int(request.args.get('year', pd.Timestamp.now().year))
    selected_customer = request.args.get('customer', 'All Customers')
    selected_location = request.args.get('location', 'All Locations')
    selected_report = request.args.get('report', 'All Reports')
    exclude_missing = request.args.get('exclude_missing', 'false').lower() == 'true'
    
    # Load data directly from S3 (stateless)
    s3_manager = get_s3_manager()
    reports_df = s3_manager.read_csv('report.csv')
    frequencies_df = s3_manager.read_csv('frequencies.csv')
    customer_location_df = s3_manager.read_csv('customer_locations.csv')
    
    filtered_df = reports_df.copy()
    if selected_customer != 'All Customers':
        filtered_df = filtered_df[filtered_df['customer'] == selected_customer]
    if selected_location != 'All Locations':
        filtered_df = filtered_df[filtered_df['location'] == selected_location]
    if selected_report != 'All Reports':
        filtered_df = filtered_df[filtered_df['report name'] == selected_report]
    
    if exclude_missing:
        filtered_df = filtered_df[~filtered_df.apply(lambda row: row.str.contains('Missing').any(), axis=1)]
    
    customers = reports_df['customer'].unique()
    locations = customer_location_df['location'].unique()
    reports = reports_df['report name'].unique()
    
    # TODO: Implement create_table_data function
    # For now, return basic template
    selected_month_name = pd.to_datetime(f'{year}-{month:02}-01').strftime('%B')
    frequencies_data = frequencies_df.to_dict(orient='records')
    
    return render_template(
        TEMPLATE_MONTHLY_REPORTS,
        reports=filtered_df.to_dict('records'),
        customers=customers,
        locations=locations,
        report_names=reports,
        selected_customer=selected_customer,
        selected_location=selected_location,
        selected_report=selected_report,
        selected_month=month,
        selected_year=year,
        selected_month_name=selected_month_name,
        exclude_missing=exclude_missing,
        frequencies_data=frequencies_data
    )


@main_bp.route('/refresh_cache', methods=['POST', 'GET'])
def refresh_cache():
    """Refresh cache - for Cloud Run, data is always read from S3, so this is a no-op"""
    # In Cloud Run, we read directly from S3, so there's nothing to refresh
    # This endpoint exists for compatibility with the original version
    if request.method == 'GET':
        next_page = request.args.get('next', 'main.index')
        return redirect(url_for(next_page))
    
    return jsonify({'status': 'success', 'message': 'Data is always fresh from S3'}), 200


# Additional routes for scraping and data APIs
import requests
from bs4 import BeautifulSoup
import re


def get_locations():
    """Get list of locations from S3"""
    try:
        s3_manager = get_s3_manager()
        customer_locations_df = s3_manager.read_csv('customer_locations.csv')
        if customer_locations_df.empty:
            return []
        
        # Try different column name variations
        location_col = None
        for col in ['location', 'Location', 'LOCATION']:
            if col in customer_locations_df.columns:
                location_col = col
                break
        
        if not location_col:
            logger.error(f"Location column not found. Available: {customer_locations_df.columns.tolist()}")
            return []
        
        return customer_locations_df[location_col].unique().tolist()
    except Exception as e:
        logger.error(f"Error getting locations: {e}", exc_info=True)
        return []


def scrape_vmware_versions(url):
    """Scrape VMware ESXi versions from knowledge base"""
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    tables = soup.find_all('table')
    
    def process_table(table):
        rows = table.find_all('tr')
        data = []
        for row in rows[1:]:
            columns = row.find_all('td')
            if len(columns) > 1:
                version = columns[1].get_text(strip=True)
                build_number = columns[3].get_text(strip=True)
                release_date = columns[2].get_text(strip=True) if len(columns) > 2 else ''
                available_as = columns[4].get_text(strip=True)
                data.append([version, build_number, release_date, available_as])
        
        for i, entry in enumerate(data):
            entry.append(f"N-{i}" if i > 0 else "N")
        return data
    
    combined_data = []
    for table in tables[:2]:
        table_data = process_table(table)
        combined_data.extend(table_data)
    
    df = pd.DataFrame(combined_data, columns=['Version', 'Build Number', 'Release Date', 'Available As', 'Label'])
    return df


@main_bp.route('/vmware_versions_report')
def vmware_versions_report_page():
    """VMware versions report page"""
    try:
        versions_df = scrape_vmware_versions(
            'https://knowledge.broadcom.com/external/article/316595/build-numbers-and-versions-of-vmware-esx.html'
        )
        table_data = versions_df.to_dict(orient='records')
        locations = get_locations()
        return render_template(TEMPLATE_VMWARE_VERSIONS_REPORT, table_data=table_data, locations=locations)
    except Exception as e:
        logger.error(f"Error in vmware_versions_report_page: {e}", exc_info=True)
        return render_template(TEMPLATE_VMWARE_VERSIONS_REPORT, table_data=[], locations=[])


@main_bp.route('/get_vhosts_data')
def get_vhosts_data():
    """Get vHosts data as JSON - reads directly from S3"""
    location = request.args.get('location', 'all')
    s3_manager = get_s3_manager()
    combined_vhosts_reports_df = s3_manager.read_csv('combined_vhosts_reports.csv')
    
    def extract_version_and_build(esx_version):
        match = re.search(r'VMware ESXi (\d+\.\d+)\.\d+ build-(\d+)', str(esx_version))
        if match:
            return match.group(1), match.group(2)
        return None, None
    
    combined_vhosts_reports_df['Version'], combined_vhosts_reports_df['Build'] = zip(
        *combined_vhosts_reports_df['ESX Version'].apply(extract_version_and_build)
    )
    
    if location != 'all':
        combined_vhosts_reports_df = combined_vhosts_reports_df[
            combined_vhosts_reports_df['Location'] == location
        ]
    
    versions_df = scrape_vmware_versions(
        'https://knowledge.broadcom.com/external/article/316595/build-numbers-and-versions-of-vmware-esx.html'
    )
    versions_df['Major_Minor_Version'] = versions_df['Version'].str[:8].str[-3:]
    
    merged_data = pd.merge(
        combined_vhosts_reports_df,
        versions_df[['Major_Minor_Version', 'Build Number', 'Label']],
        left_on=['Version', 'Build'],
        right_on=['Major_Minor_Version', 'Build Number'],
        how='left'
    )
    
    merged_data = merged_data.where(pd.notnull(merged_data), None)
    merged_data['Label'] = merged_data['Label'].fillna('NoLabel').replace('None', 'NoLabel')
    
    pie_chart_data = merged_data.groupby('Label').size().reset_index(name='count')
    pie_chart_data['count'] = pie_chart_data['count'].astype(int)
    
    hosts_table_data = merged_data[
        ['Host', 'Version', 'Build', 'Location', 'Customer', 'Label']
    ].to_dict(orient='records')
    
    scraped_data = versions_df.to_dict(orient='records')
    
    return jsonify({
        'pie_chart_data': pie_chart_data.to_dict(orient='records'),
        'hosts_table_data': hosts_table_data,
        'scraped_data': scraped_data
    })


def scrape_vcenter_versions():
    """Scrape vCenter versions from knowledge base"""
    url = "https://knowledge.broadcom.com/external/article/326316/build-numbers-and-versions-of-vmware-vce.html"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    tables = soup.find_all('table')
    vcenter_data = []
    
    for table in tables[:2]:
        rows = table.find_all('tr')
        for i, row in enumerate(rows[1:]):
            cols = row.find_all('td')
            if len(cols) >= 5:
                release_name = cols[0].text.strip()
                version = cols[1].text.strip()
                date = cols[2].text.strip()
                build_version = cols[4].text.strip()
                label = f"N-{i}" if i > 0 else "N"
                vcenter_data.append({
                    'Release Name': release_name,
                    'Version': version,
                    'Date': date,
                    'Build Version': build_version,
                    'Label': label
                })
    
    return vcenter_data


@main_bp.route('/get_vinfo_data')
def get_vinfo_data():
    """Get vInfo data as JSON - reads directly from S3"""
    location = request.args.get('location', 'all')
    vcenter_data = scrape_vcenter_versions()
    s3_manager = get_s3_manager()
    vinfo_df = s3_manager.read_csv('rvtools_vinfo.csv')
    vcs_machines = vinfo_df[vinfo_df['VM'].str.contains("vcs00", na=False)].copy()
    
    vcs_machines.loc[:, 'Location'] = vinfo_df.loc[
        vinfo_df['VM'].str.contains("vcs00", na=False), 'Location'
    ]
    vcs_machines.loc[:, 'Customer'] = vinfo_df.loc[
        vinfo_df['VM'].str.contains("vcs00", na=False), 'Customer'
    ]
    
    if location != 'all':
        vcs_machines = vcs_machines[vcs_machines['Location'] == location]
    
    vcs_machines['Version'], vcs_machines['Build'] = zip(
        *vcs_machines['VI SDK Server type'].apply(
            lambda x: re.search(r'VMware vCenter Server (\d+\.\d+)\.\d+ build-(\d+)', str(x)).groups()
            if re.search(r'VMware vCenter Server (\d+\.\d+)\.\d+ build-(\d+)', str(x))
            else ('', '')
        )
    )
    
    vcenter_df = pd.DataFrame(vcenter_data)
    vcenter_df['Major_Minor_Version'] = vcenter_df['Version'].apply(
        lambda x: '.'.join(str(x).split('.')[:2])
    )
    
    merged_data = pd.merge(
        vcs_machines,
        vcenter_df,
        left_on=['Version', 'Build'],
        right_on=['Major_Minor_Version', 'Build Version'],
        how='left'
    )
    
    merged_data['Label'] = merged_data['Label'].fillna('NoLabel').replace('None', 'NoLabel')
    vcs_machines_data = merged_data[
        ['VM', 'VI SDK Server type', 'Location', 'Customer', 'Label']
    ].to_dict(orient='records')
    
    pie_chart_data = pd.DataFrame(vcs_machines_data).groupby('Label').size().reset_index(name='count')
    pie_chart_data['count'] = pie_chart_data['count'].astype(int)
    
    return jsonify({
        'vcenter_data': vcenter_data,
        'vcs_machines_data': vcs_machines_data,
        'pie_chart_data': pie_chart_data.to_dict(orient='records')
    })
