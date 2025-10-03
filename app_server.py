from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask import send_from_directory
import requests
import json
import time
import os
from urllib.parse import urlparse
import threading
from datetime import datetime
import uuid

app = Flask(__name__)

# Global variable to store task status
task_results = {}

# JSON metadata file
METADATA_FILE = "image_metadata.json"

def load_image_metadata():
    """Load image metadata from JSON file"""
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading metadata: {e}")
            return {"tasks": [], "last_updated": None}
    return {"tasks": [], "last_updated": None}

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

def add_image_metadata(batch_id, filename, prompt, aspect_ratio="4:3", size="2K"):
    """Add new image metadata to JSON file under a batch ID"""
    metadata = load_image_metadata()

    # Check if this batch_id already exists
    existing_batch_index = None
    for i, batch in enumerate(metadata.get("batches", [])):
        if batch["id"] == batch_id:
            existing_batch_index = i
            break

    if existing_batch_index is not None:
        # Add image to existing batch
        metadata["batches"][existing_batch_index]["images"].append(filename)
        # Update the created_at to the latest time
        metadata["batches"][existing_batch_index]["created_at"] = datetime.now().isoformat()
    else:
        # Create new batch
        batch_entry = {
            "id": batch_id,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "size": size,
            "created_at": datetime.now().isoformat(),
            "images": [filename]
        }

        if "batches" not in metadata:
            metadata["batches"] = []
        metadata["batches"].append(batch_entry)

    save_image_metadata(metadata)
    return batch_id

def create_task(prompt, aspect_ratio="4:3", width=2048, height=2048, size="2K"):
    url = "https://api.vmodel.ai/api/tasks/v1/create"

    headers = {
        "Authorization": "Bearer YEUj6JlofSweD4AvBAneU1olgTnG9rO0IQjoJlfuC_vr-rVqLCxlZWp7-SUPkVFI88BbXARjOZzkDviiIjjZXQ==",
        "Content-Type": "application/json"
    }

    payload = {
        "version": "4100f7460c76359272a6409565b78334d32feb29d1fb15702007bf587062059c",
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

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()

        result = response.json()
        return result

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"Request error occurred: {req_err}")
        return None
    except Exception as err:
        print(f"An error occurred: {err}")
        return None

def get_task(task_id):
    url = f"https://api.vmodel.ai/api/tasks/v1/get/{task_id}"

    headers = {
        "Authorization": "Bearer YEUj6JlofSweD4AvBAneU1olgTnG9rO0IQjoJlfuC_vr-rVqLCxlZWp7-SUPkVFI88BbXARjOZzkDviiIjjZXQ=="
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        result = response.json()
        return result

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"Request error occurred: {req_err}")
        return None
    except Exception as err:
        print(f"An error occurred: {err}")
        return None

def download_image(image_url, output_dir="output"):
    """Download image from URL and save to output directory"""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    try:
        response = requests.get(image_url)
        response.raise_for_status()

        # Extract filename from URL
        parsed_url = urlparse(image_url)
        filename = os.path.basename(parsed_url.path)

        # If no filename in URL, use a default name
        if not filename or '.' not in filename:
            filename = "generated_image.png"

        # Create a unique filename if file already exists
        counter = 1
        original_filename = filename
        while os.path.exists(os.path.join(output_dir, filename)):
            name, ext = os.path.splitext(original_filename)
            filename = f"{name}_{counter}{ext}"
            counter += 1

        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'wb') as f:
            f.write(response.content)

        print(f"Image downloaded successfully: {filepath}")
        return filename  # Return just the filename

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred while downloading image: {http_err}")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"Request error occurred while downloading image: {req_err}")
        return None
    except Exception as err:
        print(f"An error occurred while downloading image: {err}")
        return None

def process_task(task_id, prompt, aspect_ratio="4:3", size="2K", batch_id=None):
    """Run the task processing in a background thread"""
    global task_results

    task_results[task_id] = {"status": "processing", "prompt": prompt, "batch_id": batch_id}

    # Poll for task completion
    while True:
        task_status = get_task(task_id)

        if task_status and "result" in task_status:
            status = task_status["result"]["status"]
            task_results[task_id]["status"] = status

            if status == "succeeded":
                output_urls = task_status["result"].get("output", [])
                downloaded_files = []

                if output_urls:
                    for url in output_urls:
                        filename = download_image(url)
                        if filename and batch_id:
                            # Add each image to the batch
                            add_image_metadata(batch_id, filename, prompt, aspect_ratio, size)
                            downloaded_files.append(filename)

                task_results[task_id]["completed"] = True
                task_results[task_id]["output_urls"] = output_urls
                task_results[task_id]["downloaded_files"] = downloaded_files
                break
            elif status == "failed":
                task_results[task_id]["completed"] = True
                task_results[task_id]["error"] = task_status["result"].get("error", "Unknown error")
                break
            elif status == "canceled":
                task_results[task_id]["completed"] = True
                task_results[task_id]["error"] = "Task was canceled"
                break
            else:
                time.sleep(5)  # Wait 5 seconds before checking again
        else:
            task_results[task_id]["completed"] = True
            task_results[task_id]["error"] = "Error retrieving task status"
            break

@app.route('/')
def index():
    # Get all image files from the output folder
    output_dir = "output"
    image_files = []

    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                image_files.append(filename)

    # Get recent task statuses
    recent_tasks = list(task_results.values())[-5:]  # Get last 5 tasks

    return render_template('index.html', image_files=image_files, recent_tasks=recent_tasks)

@app.route('/generate', methods=['POST'])
def generate():
    prompt = request.form.get('prompt', 'a panda riding a skateboard on the moon, digital art')
    aspect_ratio = request.form.get('aspect_ratio', '4:3')
    width = int(request.form.get('width', 2048))
    height = int(request.form.get('height', 2048))
    size = request.form.get('size', '2K')
    num_images = int(request.form.get('num_images', 1))

    # Create a batch ID for this group of images
    batch_id = str(uuid.uuid4())[:8]  # Shorter batch ID
    task_ids = []

    # Create multiple tasks for the requested number of images
    for i in range(num_images):
        task_result = create_task(prompt, aspect_ratio, width, height, size)

        if task_result and "result" in task_result:
            task_id = task_result["result"]["task_id"]
            task_ids.append(task_id)

            # Start background task processing with the batch ID
            thread = threading.Thread(target=process_task, args=(task_id, prompt, aspect_ratio, size, batch_id))
            thread.start()

    if task_ids:
        return jsonify({"status": "success", "batch_id": batch_id, "task_ids": task_ids})
    else:
        return jsonify({"status": "error", "message": "Failed to create any tasks"})

@app.route('/task_status/<task_id>')
def task_status(task_id):
    if task_id in task_results:
        return jsonify(task_results[task_id])
    else:
        return jsonify({"status": "not_found"})

@app.route('/images')
def get_images():
    # Load metadata from JSON file
    metadata = load_image_metadata()

    if not metadata.get("batches"):
        return jsonify({"batches": []})

    # Filter batches to only include those with existing image files
    valid_batches = []
    for batch in metadata.get("batches", []):
        valid_images = []
        for filename in batch.get("images", []):
            # Only include if the image file actually exists
            if os.path.exists(os.path.join("output", filename)):
                valid_images.append(filename)

        # Only add the batch if it has valid images
        if valid_images:
            batch_copy = batch.copy()
            batch_copy["images"] = valid_images
            valid_batches.append(batch_copy)

    # Sort batches by creation time (newest first)
    sorted_batches = sorted(valid_batches, key=lambda x: x["created_at"], reverse=True)

    return jsonify({"batches": sorted_batches})

@app.route('/output/<filename>')
def output_file(filename):
    return send_from_directory('output', filename)

if __name__ == '__main__':
    os.makedirs("output", exist_ok=True)  # Ensure output directory exists
    app.run(debug=True, host='0.0.0.0', port=5000)