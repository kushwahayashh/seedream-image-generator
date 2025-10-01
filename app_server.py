from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask import send_from_directory
import requests
import json
import time
import os
from urllib.parse import urlparse
import threading

app = Flask(__name__)

# Global variable to store task status
task_results = {}

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
        return filepath

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred while downloading image: {http_err}")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"Request error occurred while downloading image: {req_err}")
        return None
    except Exception as err:
        print(f"An error occurred while downloading image: {err}")
        return None

def process_task(task_id, prompt):
    """Run the task processing in a background thread"""
    global task_results

    task_results[task_id] = {"status": "processing", "prompt": prompt}

    # Poll for task completion
    while True:
        task_status = get_task(task_id)

        if task_status and "result" in task_status:
            status = task_status["result"]["status"]
            task_results[task_id]["status"] = status

            if status == "succeeded":
                output_urls = task_status["result"].get("output", [])
                if output_urls:
                    for url in output_urls:
                        download_image(url)

                task_results[task_id]["completed"] = True
                task_results[task_id]["output_urls"] = output_urls
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

    task_result = create_task(prompt, aspect_ratio, width, height, size)

    if task_result and "result" in task_result:
        task_id = task_result["result"]["task_id"]

        # Start background task processing
        thread = threading.Thread(target=process_task, args=(task_id, prompt))
        thread.start()

        return jsonify({"status": "success", "task_id": task_id})
    else:
        return jsonify({"status": "error", "message": "Failed to create task"})

@app.route('/task_status/<task_id>')
def task_status(task_id):
    if task_id in task_results:
        return jsonify(task_results[task_id])
    else:
        return jsonify({"status": "not_found"})

@app.route('/images')
def get_images():
    output_dir = "output"
    image_files = []

    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                image_files.append(filename)

    return jsonify({"images": image_files})

@app.route('/output/<filename>')
def output_file(filename):
    return send_from_directory('output', filename)

if __name__ == '__main__':
    os.makedirs("output", exist_ok=True)  # Ensure output directory exists
    app.run(debug=True, host='0.0.0.0', port=5000)