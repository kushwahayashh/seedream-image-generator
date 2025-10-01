import requests
import json
import time
import os
from urllib.parse import urlparse

def create_task():
    url = "https://api.vmodel.ai/api/tasks/v1/create"

    headers = {
        "Authorization": "Bearer YEUj6JlofSweD4AvBAneU1olgTnG9rO0IQjoJlfuC_vr-rVqLCxlZWp7-SUPkVFI88BbXARjOZzkDviiIjjZXQ==",
        "Content-Type": "application/json"
    }

    payload = {
        "version": "4100f7460c76359272a6409565b78334d32feb29d1fb15702007bf587062059c",
        "input": {
            "prompt": "a panda riding a skateboard on the moon, digital art",
            "image_input": [],
            "size": "2K",
            "aspect_ratio": "4:3",
            "width": 2048,
            "height": 2048,
            "sequential_image_generation": "disabled",
            "disable_safety_checker": False
        }
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()

        result = response.json()
        print("Task created successfully:")
        print(json.dumps(result, indent=2))

        return result

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        print(f"Response content: {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"Request error occurred: {req_err}")
    except Exception as err:
        print(f"An error occurred: {err}")

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
        print(f"Response content: {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"Request error occurred: {req_err}")
    except Exception as err:
        print(f"An error occurred: {err}")

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

        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'wb') as f:
            f.write(response.content)

        print(f"Image downloaded successfully: {filepath}")
        return filepath

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred while downloading image: {http_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Request error occurred while downloading image: {req_err}")
    except Exception as err:
        print(f"An error occurred while downloading image: {err}")

def main():
    print("Creating task...")
    task_result = create_task()

    if task_result and "result" in task_result:
        task_id = task_result["result"]["task_id"]
        print(f"Task ID: {task_id}")

        # Poll for task completion
        print("Waiting for task to complete...")
        while True:
            task_status = get_task(task_id)

            if task_status and "result" in task_status:
                status = task_status["result"]["status"]
                print(f"Task status: {status}")

                if status == "succeeded":
                    output_urls = task_status["result"].get("output", [])
                    if output_urls:
                        print(f"Task completed successfully. Downloading image...")
                        for url in output_urls:
                            download_image(url)
                    else:
                        print("Task completed but no output URLs found.")
                    break
                elif status == "failed":
                    print(f"Task failed: {task_status['result'].get('error', 'Unknown error')}")
                    break
                elif status == "canceled":
                    print("Task was canceled.")
                    break
                else:
                    print("Task still processing... waiting 5 seconds before checking again.")
                    time.sleep(5)
            else:
                print("Error retrieving task status.")
                break
    else:
        print("Failed to create task.")

if __name__ == "__main__":
    main()