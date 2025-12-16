import os
import csv
import json
import time
import io
from flask import Flask, request, render_template, jsonify, Response
from openai import AzureOpenAI

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT = os.environ.get('AZURE_OPENAI_ENDPOINT')
AZURE_OPENAI_API_KEY = os.environ.get('AZURE_OPENAI_API_KEY')
AZURE_OPENAI_DEPLOYMENT = os.environ.get('AZURE_OPENAI_DEPLOYMENT')
AZURE_OPENAI_API_VERSION = os.environ.get('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')

def get_azure_client():
    """Initialize Azure OpenAI client"""
    if not all([AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT]):
        raise ValueError("Missing Azure OpenAI configuration. Please set environment variables.")
    
    return AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION
    )

def parse_csv(csv_content):
    """Parse CSV content into list of dictionaries"""
    reader = csv.DictReader(io.StringIO(csv_content))
    # Normalize headers to lowercase
    rows = []
    for row in reader:
        normalized = {k.lower().strip(): v.strip() for k, v in row.items()}
        rows.append(normalized)
    return rows

def parse_percentage(value):
    """Parse percentage from various formats"""
    if not value or value == '':
        return 0
    value = str(value).strip()
    if '%' in value:
        return float(value.replace('%', '')) / 100
    num = float(value)
    return num / 100 if num > 1 else num

def parse_currency(value):
    """Parse currency from various formats"""
    if not value or value == '':
        return 0
    return float(str(value).replace('$', '').replace(',', ''))

def normalize_name(name):
    """Normalize name for comparison"""
    if not name:
        return ''
    return str(name).lower().strip()

def build_rules_lookup(rules_data):
    """Build lookup dictionary from rules sheet"""
    lookup = {}
    for rule in rules_data:
        name = normalize_name(
            rule.get('attorney name') or 
            rule.get('attorney_name') or 
            rule.get('name', '')
        )
        lookup[name] = {
            'user_percentage': parse_percentage(
                rule.get('user percentage') or 
                rule.get('user_percentage', '0')
            ),
            'origination_percentage': parse_percentage(
                rule.get('own origination other work percentage') or 
                rule.get('own_origination_other_work_percentage') or
                rule.get('origination_percentage', '0')
            )
        }
    return lookup

def process_with_ai(client, case_batch, rules_lookup, batch_num, total_batches):
    """Use Azure OpenAI to validate and process calculations"""
    
    # Prepare the data for AI analysis
    cases_summary = []
    for case in case_batch:
        matter = case.get('matter', '')
        date = case.get('date', '')
        total = parse_currency(case.get('total collected') or case.get('total_collected', '0'))
        user = case.get('user', '')
        originator = case.get('originator', '')
        
        user_norm = normalize_name(user)
        originator_norm = normalize_name(originator)
        
        user_rule = rules_lookup.get(user_norm, {'user_percentage': 0, 'origination_percentage': 0})
        originator_rule = rules_lookup.get(originator_norm, {'user_percentage': 0, 'origination_percentage': 0})
        
        cases_summary.append({
            'matter': matter,
            'date': date,
            'total_collected': total,
            'user': user,
            'originator': originator,
            'user_percentage': user_rule['user_percentage'],
            'originator_own_origination_pct': originator_rule['origination_percentage'],
            'same_person': user_norm == originator_norm
        })
    
    # Create prompt for AI
    system_prompt = """You are a precise financial calculator agent. Your task is to calculate attorney commissions following these EXACT rules:

AGENT 1 - USER CALCULATION:
- User Pay = Total Collected × User Percentage

AGENT 2 - ORIGINATOR CALCULATION:
- If user and originator are the SAME person: Leave originator_percentage and originator_pay as empty strings ""
- If user and originator are DIFFERENT: 
  - originator_percentage = originator's "own origination other work percentage"
  - originator_pay = User Pay × originator_percentage
  - CRITICAL: Multiply against USER PAY, not total collected!

Return ONLY valid JSON array with calculated results. Each object must have:
- matter, date, user, originator, total_collected, user_percentage, user_pay
- originator_percentage (empty string if same person)
- originator_pay (empty string if same person)

Format percentages as decimals (0.30 not 30%). Format money as numbers (no $ or commas)."""

    user_prompt = f"""Process batch {batch_num} of {total_batches}. Calculate commissions for these cases:

{json.dumps(cases_summary, indent=2)}

Take your time to calculate each row carefully and accurately. Return the results as a JSON array."""

    try:
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,  # Deterministic for calculations
            max_tokens=4000
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Extract JSON from response
        if '```json' in result_text:
            result_text = result_text.split('```json')[1].split('```')[0]
        elif '```' in result_text:
            result_text = result_text.split('```')[1].split('```')[0]
        
        return json.loads(result_text)
    
    except Exception as e:
        # Fallback to manual calculation if AI fails
        print(f"AI processing failed, using fallback: {e}")
        return calculate_fallback(cases_summary)

def calculate_fallback(cases_summary):
    """Fallback calculation without AI"""
    results = []
    for case in cases_summary:
        user_pay = case['total_collected'] * case['user_percentage']
        
        if case['same_person']:
            originator_pct = ''
            originator_pay = ''
        else:
            originator_pct = case['originator_own_origination_pct']
            originator_pay = user_pay * originator_pct
        
        results.append({
            'matter': case['matter'],
            'date': case['date'],
            'user': case['user'],
            'originator': case['originator'],
            'total_collected': case['total_collected'],
            'user_percentage': case['user_percentage'],
            'user_pay': user_pay,
            'originator_percentage': originator_pct,
            'originator_pay': originator_pay
        })
    return results

def format_output_csv(results):
    """Format results as CSV string"""
    headers = ['matter', 'date', 'user', 'originator', 'total collected', 'user percentage', 'user pay', 'originator percentage', 'originator pay']
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    
    for row in results:
        user_pct = row.get('user_percentage', 0)
        if isinstance(user_pct, (int, float)):
            user_pct = f"{user_pct * 100:.1f}%"
        
        orig_pct = row.get('originator_percentage', '')
        if isinstance(orig_pct, (int, float)) and orig_pct != '':
            orig_pct = f"{orig_pct * 100:.1f}%"
        
        user_pay = row.get('user_pay', 0)
        if isinstance(user_pay, (int, float)):
            user_pay = f"{user_pay:.2f}"
        
        orig_pay = row.get('originator_pay', '')
        if isinstance(orig_pay, (int, float)) and orig_pay != '':
            orig_pay = f"{orig_pay:.2f}"
        
        total = row.get('total_collected', 0)
        if isinstance(total, (int, float)):
            total = f"{total:.2f}"
        
        writer.writerow([
            row.get('matter', ''),
            row.get('date', ''),
            row.get('user', ''),
            row.get('originator', ''),
            total,
            user_pct,
            user_pay,
            orig_pct,
            orig_pay
        ])
    
    return output.getvalue()

@app.route('/')
def index():
    """Main upload page"""
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    """Process uploaded CSV files"""
    try:
        # Get uploaded files
        if 'case_data' not in request.files or 'rules_sheet' not in request.files:
            return jsonify({'error': 'Please upload both CSV files'}), 400
        
        case_file = request.files['case_data']
        rules_file = request.files['rules_sheet']
        
        if case_file.filename == '' or rules_file.filename == '':
            return jsonify({'error': 'Please select both files'}), 400
        
        # Read and parse CSVs
        case_data_content = case_file.read().decode('utf-8-sig')  # Handle BOM
        rules_content = rules_file.read().decode('utf-8-sig')
        
        case_data = parse_csv(case_data_content)
        rules_data = parse_csv(rules_content)
        
        if not case_data:
            return jsonify({'error': 'Case data CSV is empty or invalid'}), 400
        if not rules_data:
            return jsonify({'error': 'Rules sheet CSV is empty or invalid'}), 400
        
        # Build rules lookup
        rules_lookup = build_rules_lookup(rules_data)
        
        # Initialize Azure OpenAI client
        try:
            client = get_azure_client()
        except ValueError as e:
            return jsonify({'error': str(e)}), 500
        
        # Process in batches for large datasets
        BATCH_SIZE = 20  # Process 20 rows at a time for accuracy
        all_results = []
        total_batches = (len(case_data) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for i in range(0, len(case_data), BATCH_SIZE):
            batch = case_data[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            
            # Add delay between batches for rate limiting
            if i > 0:
                time.sleep(1)
            
            batch_results = process_with_ai(client, batch, rules_lookup, batch_num, total_batches)
            all_results.extend(batch_results)
        
        # Format output
        csv_output = format_output_csv(all_results)
        
        return jsonify({
            'success': True,
            'csv_output': csv_output,
            'processed_rows': len(all_results),
            'results': all_results
        })
    
    except Exception as e:
        return jsonify({'error': f'Processing error: {str(e)}'}), 500

@app.route('/download', methods=['POST'])
def download():
    """Download processed CSV"""
    try:
        data = request.get_json()
        csv_content = data.get('csv_output', '')
        
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=commission_results.csv'}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    config_status = {
        'endpoint_set': bool(AZURE_OPENAI_ENDPOINT),
        'api_key_set': bool(AZURE_OPENAI_API_KEY),
        'deployment_set': bool(AZURE_OPENAI_DEPLOYMENT)
    }
    return jsonify({
        'status': 'healthy',
        'azure_config': config_status
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
