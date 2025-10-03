from flask import Flask, render_template, request, jsonify, send_from_directory
import requests
import json
import time
import os
from urllib.parse import urlparse
import threading
from datetime import datetime
import uuid

app = Flask(__name__)

# Configuration
API_BASE_URL = "https://api.vmodel.ai/api/tasks/v1"
API_TOKEN = "Bearer YEUj6JlofSweD4AvBAneU1olgTnG9rO0IQjoJlfuC_vr-rVqLCxlZWp7-SUPkVFI88BbXARjOZzkDviiIjjZXQ=="
MODEL_VERSION = "4100f7460c76359272a6409565b78334d32feb29d1fb15702007bf587062059c"
METADATA_FILE = "image_metadata.json"
OUTPUT_DIR = "output"

# Global state
task_results = {}

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_api_headers():
    """Get common API headers"""
    return {
        "Authorization": API_TOKEN,
        "Content-Type": "application/json"
    }

def load_image_metadata():
    """Load image metadata from JSON file"""
    if not os.path.exists(METADATA_FILE):
        return {"batches": [], "last_updated": None}
    
    try:
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading metadata: {e}")
        return {"batches": [], "last_updated": None}

def save_image_metadata(metadata):
    """Save image metadata to JSON file"""
    try:
        metadata["last_updated"] = datetime.now().isoformat()
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving metadata: {e}")
        return False

def add_image_to_batch(batch_id, filename, prompt, aspect_ratio="4:3", size="2K"):
    """Add image to existing batch or create new batch"""
    metadata = load_image_metadata()
    
    # Find existing batch
    batch = next((b for b in metadata.get("batches", []) if b["id"] == batch_id), None)
    
    if batch:
        # Add to existing batch
        batch["images"].append(filename)
        batch["created_at"] = datetime.now().isoformat()
    else:
        # Create new batch
        new_batch = {
            "id": batch_id,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "size": size,
            "created_at": datetime.now().isoformat(),
            "images": [filename]
        }
        
        if "batches" not in metadata:
            metadata["batches"] = []
        metadata["batches"].append(new_batch)
    
    save_image_metadata(metadata)
    return batch_id

def make_api_request(url, payload=None):
    """Make API request with error handling"""
    try:
        headers = get_api_headers()
        if payload:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
        else:
            response = requests.get(url, headers=headers)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API request error: {e}")
        return None

def create_task(prompt, aspect_ratio="4:3", width=2048, height=2048, size="2K"):
    """Create a new image generation task"""
    url = f"{API_BASE_URL}/create"
    
    payload = {
        "version": MODEL_VERSION,
        "input": {
            "prompt": prompt,
            "image_input": [],
            "size": size,
            "aspect_ratio": aspect_ratio,
            "width": width,
            "height": height,
            "sequential_image_generation": "disabled",
            "disable_safety_checker": False
        }
    }
    
    return make_api_request(url, payload)

def get_task_status(task_id):
    """Get task status from API"""
    url = f"{API_BASE_URL}/get/{task_id}"
    return make_api_request(url)

def download_image(image_url):
    """Download image from URL and save to output directory"""
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        
        # Extract filename from URL
        parsed_url = urlparse(image_url)
        filename = os.path.basename(parsed_url.path)
        
        # Generate unique filename if needed
        if not filename or '.' not in filename:
            filename = "generated_image.png"
        
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        # Handle filename conflicts
        counter = 1
        original_filepath = filepath
        while os.path.exists(filepath):
            name, ext = os.path.splitext(original_filepath)
            filepath = f"{name}_{counter}{ext}"
            counter += 1
        
        # Save image
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        return os.path.basename(filepath)
    
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None

def process_task(task_id, prompt, aspect_ratio="4:3", size="2K", batch_id=None):
    """Process task in background thread"""
    task_results[task_id] = {
        "status": "processing", 
        "prompt": prompt, 
        "batch_id": batch_id,
        "completed": False
    }
    
    while True:
        task_status = get_task_status(task_id)
        
        if not task_status or "result" not in task_status:
            task_results[task_id] = {
                **task_results[task_id],
                "completed": True,
                "error": "Error retrieving task status"
            }
            break
        
        status = task_status["result"]["status"]
        task_results[task_id]["status"] = status
        
        if status == "succeeded":
            output_urls = task_status["result"].get("output", [])
            downloaded_files = []
            
            for url in output_urls:
                filename = download_image(url)
                if filename and batch_id:
                    add_image_to_batch(batch_id, filename, prompt, aspect_ratio, size)
                    downloaded_files.append(filename)
            
            task_results[task_id] = {
                **task_results[task_id],
                "completed": True,
                "output_urls": output_urls,
                "downloaded_files": downloaded_files
            }
            break
        
        elif status in ["failed", "canceled"]:
            task_results[task_id] = {
                **task_results[task_id],
                "completed": True,
                "error": task_status["result"].get("error", f"Task {status}")
            }
            break
        
        # Continue polling
        time.sleep(5)

def get_local_images():
    """Get all image files from output directory"""
    if not os.path.exists(OUTPUT_DIR):
        return []
    
    return [
        filename for filename in os.listdir(OUTPUT_DIR)
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))
    ]

def get_valid_batches():
    """Get batches with existing image files"""
    metadata = load_image_metadata()
    if not metadata.get("batches"):
        return []
    
    valid_batches = []
    for batch in metadata.get("batches", []):
        valid_images = [
            filename for filename in batch.get("images", [])
            if os.path.exists(os.path.join(OUTPUT_DIR, filename))
        ]
        
        if valid_images:
            batch_copy = batch.copy()
            batch_copy["images"] = valid_images
            valid_batches.append(batch_copy)
    
    return sorted(valid_batches, key=lambda x: x["created_at"], reverse=True)

# Routes
@app.route('/')
def index():
    """Main page"""
    image_files = get_local_images()
    recent_tasks = list(task_results.values())[-5:]  # Get last 5 tasks
    return render_template('index.html', image_files=image_files, recent_tasks=recent_tasks)

@app.route('/generate', methods=['POST'])
def generate():
    """Generate images"""
    prompt = request.form.get('prompt', 'a panda riding a skateboard on the moon, digital art')
    aspect_ratio = request.form.get('aspect_ratio', '4:3')
    width = int(request.form.get('width', 2048))
    height = int(request.form.get('height', 2048))
    size = request.form.get('size', '2K')
    num_images = int(request.form.get('num_images', 1))
    
    batch_id = str(uuid.uuid4())[:8]  # Short batch ID
    task_ids = []
    
    # Create and start tasks
    for _ in range(num_images):
        task_result = create_task(prompt, aspect_ratio, width, height, size)
        
        if task_result and "result" in task_result:
            task_id = task_result["result"]["task_id"]
            task_ids.append(task_id)
            
            # Start background processing
            thread = threading.Thread(
                target=process_task, 
                args=(task_id, prompt, aspect_ratio, size, batch_id)
            )
            thread.daemon = True
            thread.start()
    
    if task_ids:
        return jsonify({
            "status": "success", 
            "batch_id": batch_id, 
            "task_ids": task_ids
        })
    
    return jsonify({
        "status": "error", 
        "message": "Failed to create any tasks"
    })

@app.route('/task_status/<task_id>')
def task_status(task_id):
    """Get task status"""
    return jsonify(task_results.get(task_id, {"status": "not_found"}))

@app.route('/images')
def get_images():
    """Get all images grouped by batch"""
    return jsonify({"batches": get_valid_batches()})

@app.route('/output/<filename>')
def output_file(filename):
    """Serve output files"""
    return send_from_directory(OUTPUT_DIR, filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)