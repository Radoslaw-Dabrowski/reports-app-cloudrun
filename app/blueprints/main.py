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
    """Snapshot report page"""
    snapshot_reports_df = db_manager.read_table('combined_snapshot_reports')
    table_data = snapshot_reports_df.to_dict(orient='records')
    return render_template(TEMPLATE_SNAPSHOT_REPORTS, table_data=table_data)


@main_bp.route('/vhealth_report')
def vhealth_report_page():
    """vHealth report page"""
    combined_vhealth_df = db_manager.read_table('combined_vhealth_reports')
    table_data = combined_vhealth_df.to_dict(orient='records')
    table_data_json = json.dumps(table_data)
    return render_template(TEMPLATE_VHEALTH_REPORTS, table_data=table_data_json)


@main_bp.route('/firmware_report')
def firmware_report_page():
    """Firmware report page"""
    combined_firmware_df = db_manager.read_table('combined_firmware_reports')
    customer_locations_df = db_manager.read_table('customer_locations')
    
    if 'Location' not in combined_firmware_df.columns:
        raise KeyError("'Location' column is missing from combined_firmware_reports")
    
    if 'location' not in customer_locations_df.columns:
        raise KeyError("'location' column is missing from customer_locations_df")
    
    combined_firmware_df = combined_firmware_df.merge(
        customer_locations_df, left_on='Location', right_on='location', how='left'
    )
    
    if 'Customer' not in combined_firmware_df.columns and 'Customer' in customer_locations_df.columns:
        combined_firmware_df['Customer'] = combined_firmware_df['location'].map(
            customer_locations_df.set_index('location')['Customer']
        )
    
    table_data = combined_firmware_df.to_dict(orient='records')
    customers = sorted(customer_locations_df['Customer'].unique())
    locations = sorted(customer_locations_df['location'].unique())
    
    return render_template(TEMPLATE_FIRMWARE_REPORTS, table_data=table_data, customers=customers, locations=locations)


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
    """vDisk report page"""
    combined_vdisk_reports_df = db_manager.read_table('combined_vdisk_reports')
    table_data = combined_vdisk_reports_df.to_dict(orient='records')
    return render_template(TEMPLATE_VDISK_REPORT, table_data=table_data)


@main_bp.route('/vhosts_report')
def vhosts_report_page():
    """vHosts report page"""
    combined_vhosts_reports_df = db_manager.read_table('combined_vhosts_reports')
    table_data = combined_vhosts_reports_df.to_dict(orient='records')
    return render_template(TEMPLATE_VHOSTS_REPORT, table_data=table_data)


@main_bp.route('/statistics_report')
def statistics_report_page():
    """Statistics report page"""
    vrops_alerts_df = db_manager.read_table('vrops_alerts_historical')
    vrops_alerts_df['date'] = pd.to_datetime(vrops_alerts_df['date'], errors='coerce')
    for col in ['critical', 'immediate', 'warning', 'total']:
        if col in vrops_alerts_df.columns:
            vrops_alerts_df[col] = vrops_alerts_df[col].fillna(0).astype(int)
        else:
            vrops_alerts_df[col] = 0
    
    vrops_alerts_df = vrops_alerts_df.sort_values(by=['location', 'date'])
    vrops_alerts_df['critical_diff'] = vrops_alerts_df.groupby('location')['critical'].diff()
    latest_data = vrops_alerts_df.sort_values('date', ascending=False).drop_duplicates('location')
    
    table_data = []
    for _, row in latest_data.iterrows():
        critical_diff = row['critical_diff']
        color = '#f8d7da' if critical_diff > 0 else '#d4edda' if critical_diff < 0 else ''
        table_data.append({
            'customer': row['customer'],
            'date': row['date'].strftime('%Y-%m-%d') if pd.notna(row['date']) else 'Missing',
            'location': row['location'],
            'critical': int(row['critical']),
            'immediate': int(row['immediate']),
            'warning': int(row['warning']),
            'total': int(row['total']),
            'color': color
        })
    
    return render_template(TEMPLATE_STATISTICS_REPORT, table_data=table_data, locations=vrops_alerts_df['location'].unique())


@main_bp.route('/network_utilization_report')
def network_utilization_report_page():
    """Network utilization report page"""
    combined_network_utilization_df = db_manager.read_table('combined_network_utilization_report')
    
    # Load exclusions from S3
    s3_manager = get_s3_manager()
    excluded_networks_df = s3_manager.read_csv('excluded_networks.csv')
    if excluded_networks_df.empty or 'Network' not in excluded_networks_df.columns or 'Location' not in excluded_networks_df.columns:
        excluded_networks_df = pd.DataFrame(columns=['Network', 'Location'])
    
    # Exclude specified networks
    if not excluded_networks_df.empty:
        exclusions = excluded_networks_df[['Network', 'Location']].apply(tuple, axis=1)
        combined_network_utilization_df = combined_network_utilization_df[
            ~combined_network_utilization_df[['Network', 'Location']].apply(tuple, axis=1).isin(exclusions)
        ]
    
    table_data = combined_network_utilization_df.to_dict(orient='records')
    customer_locations_df = db_manager.read_table('customer_locations')
    locations = sorted(customer_locations_df['location'].unique())
    customers = sorted(customer_locations_df['Customer'].unique())
    
    return render_template(TEMPLATE_NETWORK_UTILIZATION_REPORT, table_data=table_data, locations=locations, customers=customers)


@main_bp.route('/certificate_expiry_report')
def certificate_expiry_report_page():
    """Certificate expiry report page"""
    certificate_expiry_df = db_manager.read_table('combined_certificate_expiry_reports')
    table_data = certificate_expiry_df.to_dict(orient='records')
    customer_locations_df = db_manager.read_table('customer_locations')
    customers = sorted(customer_locations_df['Customer'].unique())
    locations = sorted(customer_locations_df['location'].unique())
    return render_template(TEMPLATE_CERTIFICATE_EXPIRY_REPORT, table_data=table_data, customers=customers, locations=locations)


@main_bp.route('/password_expiration_report')
def password_expiration_report_page():
    """Password expiration report page"""
    password_expiration_df = db_manager.read_table('combined_password_expiration_reports')
    table_data = password_expiration_df.to_dict(orient='records')
    customer_locations_df = db_manager.read_table('customer_locations')
    customers = sorted(customer_locations_df['Customer'].unique())
    locations = sorted(customer_locations_df['location'].unique())
    return render_template(TEMPLATE_PASSWORD_EXPIRATION_REPORT, table_data=table_data, customers=customers, locations=locations)


@main_bp.route('/antivirus_asset_report')
def antivirus_asset_report_page():
    """Antivirus asset report page"""
    combined_antivirus_asset_report_df = db_manager.read_table('combined_antivirus_asset_reports')
    table_data = combined_antivirus_asset_report_df.to_dict(orient='records')
    customer_locations_df = db_manager.read_table('customer_locations')
    customers = sorted(customer_locations_df['Customer'].unique())
    locations = sorted(customer_locations_df['location'].unique())
    return render_template(TEMPLATE_ANTIVIRUS_ASSET_REPORT, table_data=table_data, customers=customers, locations=locations)


@main_bp.route('/env_versions_report')
def env_versions_report_page():
    """Environment versions report page"""
    combined_non_vcf_inventory_df = db_manager.read_table('combined_non_vcf_inventory')
    combined_vcf_inventory_df = db_manager.read_table('combined_vcf_inventory')
    combined_both_inventory_df = pd.concat([combined_non_vcf_inventory_df, combined_vcf_inventory_df])
    
    combined_both_inventory_df['Report Date'] = pd.to_datetime(combined_both_inventory_df['Report Date'], errors='coerce')
    if combined_both_inventory_df['Report Date'].dt.time.any():
        combined_both_inventory_df['Report Date'] = combined_both_inventory_df['Report Date'].dt.date
    
    combined_both_inventory_df = combined_both_inventory_df.drop_duplicates(
        subset=['Customer', 'Location', 'Report Date', 'VM', 'Name']
    )
    table_data = combined_both_inventory_df.to_dict(orient='records')
    return render_template(TEMPLATE_ENV_VERSIONS_REPORT, table_data=table_data)


@main_bp.route('/alerts_report')
def alerts_report_page():
    """Alerts report page"""
    location = request.args.get('location')
    vrops_list_of_alerts_df = db_manager.read_table('combined_vrops_list_of_alerts')
    
    if location:
        filtered_alerts = vrops_list_of_alerts_df[vrops_list_of_alerts_df['Location'] == location]
    else:
        filtered_alerts = vrops_list_of_alerts_df
    
    alerts_data = filtered_alerts.to_dict(orient='records')
    return render_template(TEMPLATE_ALERTS_REPORT, alerts_data=alerts_data)


@main_bp.route('/monthly_report')
@cached(timeout=1800, key_prefix="monthly_report")
def monthly_report_page():
    """Monthly report page with caching"""
    month = int(request.args.get('month', pd.Timestamp.now().month))
    year = int(request.args.get('year', pd.Timestamp.now().year))
    selected_customer = request.args.get('customer', 'All Customers')
    selected_location = request.args.get('location', 'All Locations')
    selected_report = request.args.get('report', 'All Reports')
    exclude_missing = request.args.get('exclude_missing', 'false').lower() == 'true'
    
    # Load data from database (stateless - load on each request)
    reports_df = db_manager.read_table('report')
    frequencies_df = db_manager.read_table('frequencies')
    customer_location_df = db_manager.read_table('customer_locations')
    
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
    """Refresh data from S3 to database"""
    try:
        s3_manager = get_s3_manager()
        
        # List of CSV files to sync
        csv_files = [
            'report.csv',
            'frequencies.csv',
            'customer_locations.csv',
            'combined_firmware_reports.csv',
            'combined_vhealth_reports.csv',
            'combined_snapshot_reports.csv',
            'combined_network_utilization_report.csv',
            'combined_certificate_expiry_reports.csv',
            'combined_password_expiration_reports.csv',
            'combined_antivirus_asset_reports.csv',
            'combined_vdisk_reports.csv',
            'combined_vhosts_reports.csv',
            'rvtools_vinfo.csv',
            'vrops_alerts_historical.csv',
            'combined_vrops_list_of_alerts.csv',
            'combined_non_vcf_inventory.csv',
            'combined_vcf_inventory.csv',
            'excluded_networks.csv'
        ]
        
        for csv_file in csv_files:
            logger.info(f"Syncing {csv_file}")
            df = s3_manager.read_csv(csv_file)
            
            if not df.empty:
                table_name = csv_file.replace('.csv', '')
                if db_manager.table_exists(table_name):
                    db_manager.truncate_table(table_name)
                db_manager.write_table(df, table_name)
        
        if request.method == 'GET':
            next_page = request.args.get('next', 'main.index')
            return redirect(url_for(next_page))
        
        return jsonify({'status': 'success', 'message': 'Cache refreshed'}), 200
        
    except Exception as e:
        logger.error(f"Error refreshing cache: {e}")
        if request.method == 'GET':
            return redirect(url_for('main.index'))
        return jsonify({'status': 'error', 'message': str(e)}), 500


# Additional routes for scraping and data APIs
import requests
from bs4 import BeautifulSoup
import re


def get_locations():
    """Get list of locations from database"""
    customer_locations_df = db_manager.read_table('customer_locations')
    return customer_locations_df['location'].unique().tolist()


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
    versions_df = scrape_vmware_versions(
        'https://knowledge.broadcom.com/external/article/316595/build-numbers-and-versions-of-vmware-esx.html'
    )
    table_data = versions_df.to_dict(orient='records')
    locations = get_locations()
    return render_template(TEMPLATE_VMWARE_VERSIONS_REPORT, table_data=table_data, locations=locations)


@main_bp.route('/get_vhosts_data')
def get_vhosts_data():
    """Get vHosts data as JSON"""
    location = request.args.get('location', 'all')
    combined_vhosts_reports_df = db_manager.read_table('combined_vhosts_reports')
    
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
    """Get vInfo data as JSON"""
    location = request.args.get('location', 'all')
    vcenter_data = scrape_vcenter_versions()
    vinfo_df = db_manager.read_table('rvtools_vinfo')
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
