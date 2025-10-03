document.getElementById('generateForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = new FormData(this);
    const statusDiv = document.getElementById('statusMessage');
    const spinnerDiv = document.getElementById('spinner');
    const imageGrid = document.getElementById('imageGrid');
    const numImages = parseInt(formData.get('num_images')) || 1;

    // Remove height and width from form data since they're no longer in the UI
    formData.delete('height');
    formData.delete('width');

    // Show spinner and hide previous status
    spinnerDiv.classList.add('active');
    statusDiv.classList.remove('active', 'success', 'error');

    // Get current prompt and aspect ratio for skeleton cards
    const currentPrompt = formData.get('prompt') || 'Generating image...';
    const aspectRatio = formData.get('aspect_ratio') || '4:3';
    const skeletonHeight = getSkeletonHeight(aspectRatio);

    // Add skeleton cards group
    const imageContainer = document.getElementById('imageContainer');

    // Create or find a skeleton prompt group
    let skeletonGroup = document.getElementById('skeleton-group');
    if (!skeletonGroup) {
        skeletonGroup = document.createElement('div');
        skeletonGroup.className = 'prompt-group';
        skeletonGroup.id = 'skeleton-group';

        const promptText = document.createElement('div');
        promptText.className = 'prompt-text';
        promptText.textContent = currentPrompt;
        skeletonGroup.appendChild(promptText);

        const skeletonGrid = document.createElement('div');
        skeletonGrid.className = 'image-grid';
        skeletonGrid.id = 'skeleton-grid';
        skeletonGroup.appendChild(skeletonGrid);

        // Insert at the beginning of container
        imageContainer.insertBefore(skeletonGroup, imageContainer.firstChild);
    } else {
        // Update prompt text if it exists
        const promptText = skeletonGroup.querySelector('.prompt-text');
        if (promptText) {
            promptText.textContent = currentPrompt;
        }
    }

    const skeletonGrid = document.getElementById('skeleton-grid');

    // Add multiple skeleton cards based on number of images requested
    currentSkeletonIds = []; // Clear previous skeleton IDs
    for (let i = 0; i < numImages; i++) {
        const skeletonId = 'skeleton-' + Date.now() + '-' + i;
        currentSkeletonIds.push(skeletonId);

        const skeletonCard = document.createElement('div');
        skeletonCard.className = 'skeleton-card';
        skeletonCard.id = skeletonId;

        const skeletonImage = document.createElement('div');
        skeletonImage.className = 'skeleton-image';
        skeletonImage.style.height = skeletonHeight;
        skeletonImage.textContent = 'Generating...';

        skeletonCard.appendChild(skeletonImage);

        // Insert skeleton at the beginning of the skeleton grid
        skeletonGrid.insertBefore(skeletonCard, skeletonGrid.firstChild);
    }

    // Create multiple tasks for the requested images, grouped by batch
    try {
        const response = await fetch('/generate', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.status === 'success') {
            statusDiv.textContent = `Batch created successfully! Batch ID: ${result.batch_id}`;
            statusDiv.className = 'status active success';

            // Track how many tasks have completed
            let completedTasks = 0;
            let hasError = false;

            // Poll for each task status
            result.task_ids.forEach((taskId, index) => {
                pollTaskStatus(taskId, () => {
                    completedTasks++;
                    if (completedTasks === result.task_ids.length && !hasError) {
                        statusDiv.textContent = `Batch ${result.batch_id} completed successfully! Generated ${numImages} images.`;
                        statusDiv.className = 'status active success';
                    }
                });
            });
        } else {
            statusDiv.textContent = `Error: ${result.message}`;
            statusDiv.className = 'status active error';
        }
    } catch (error) {
        statusDiv.textContent = `Error: ${error.message}`;
        statusDiv.className = 'status active error';
    }

    // Hide spinner when all tasks are initiated
    spinnerDiv.classList.remove('active');
});

function removeSkeletonCard(skeletonId) {
    const skeletonElement = document.getElementById(skeletonId);
    if (skeletonElement) {
        skeletonElement.remove();
    }

    // Check if skeleton group is empty and remove it
    const skeletonGroup = document.getElementById('skeleton-group');
    if (skeletonGroup) {
        const skeletonGrid = document.getElementById('skeleton-grid');
        if (skeletonGrid && skeletonGrid.children.length === 0) {
            skeletonGroup.remove();
        }
    }
}

function pollTaskStatus(taskId, onComplete) {
    const statusDiv = document.getElementById('statusMessage');

    const checkStatus = async () => {
        try {
            const response = await fetch(`/task_status/${taskId}`);
            const result = await response.json();

            if (result.completed) {
                if (result.status === 'succeeded') {
                    // Refresh the images
                    loadImages();

                    // Call the completion callback if provided
                    if (onComplete) {
                        onComplete();
                    }
                } else {
                    statusDiv.textContent = 'Task failed: ' + (result.error || 'Unknown error');
                    statusDiv.className = 'status active error';

                    // Remove skeleton card on failure
                    // We'll remove a skeleton card, but need to track which one
                    if (typeof onComplete === 'function') {
                        onComplete();
                    }
                }
                return;
            } else {
                // Continue polling
                setTimeout(checkStatus, 5000);
            }
        } catch (error) {
            statusDiv.textContent = 'Error checking task status: ' + error.message;
            statusDiv.className = 'status active error';

            // Call completion callback on error
            if (typeof onComplete === 'function') {
                onComplete();
            }
        }
    };

    checkStatus();
}

// Global variable to store skeleton IDs
let currentSkeletonIds = [];

function getSkeletonHeight(aspectRatio) {
    // Calculate height based on aspect ratio to maintain proper proportions
    // Assuming grid column width of around 300px on desktop
    const baseWidth = 300;

    switch(aspectRatio) {
        case '1:1':
            return baseWidth + 'px';
        case '4:3':
            return (baseWidth * 3/4) + 'px';
        case '16:9':
            return (baseWidth * 9/16) + 'px';
        case '9:16':
            return (baseWidth * 16/9) + 'px';
        case '3:2':
            return (baseWidth * 2/3) + 'px';
        default:
            return (baseWidth * 3/4) + 'px'; // Default to 4:3
    }
}

async function loadImages() {
    try {
        const response = await fetch('/images');
        const result = await response.json();

        const imageContainer = document.getElementById('imageContainer');

        // Remove any existing skeleton cards before loading new images
        currentSkeletonIds.forEach(id => {
            removeSkeletonCard(id);
        });
        currentSkeletonIds = [];

        // Remove skeleton group if it exists
        const skeletonGroup = document.getElementById('skeleton-group');
        if (skeletonGroup) {
            skeletonGroup.remove();
        }

        imageContainer.innerHTML = '';

        if (!result.batches || result.batches.length === 0) {
            imageContainer.innerHTML = '<p>No images found in the output folder.</p>';
            return;
        }

        // Create batch groups
        result.batches.forEach(batch => {
            const batchGroup = document.createElement('div');
            batchGroup.className = 'prompt-group';

            const promptText = document.createElement('div');
            promptText.className = 'prompt-text';
            promptText.textContent = batch.prompt;
            batchGroup.appendChild(promptText);

            // Add batch metadata
            const batchMeta = document.createElement('div');
            batchMeta.className = 'task-meta';
            batchMeta.innerHTML = `
                <span class="task-id">Batch ID: ${batch.id}</span>
                <span class="task-date">${new Date(batch.created_at).toLocaleString()}</span>
                <span class="task-size">${batch.aspect_ratio} • ${batch.size} • ${batch.images.length} images</span>
            `;
            batchGroup.appendChild(batchMeta);

            const imageGrid = document.createElement('div');
            imageGrid.className = 'image-grid';

            batch.images.forEach(filename => {
                const imageCard = document.createElement('div');
                imageCard.className = 'image-card';

                imageCard.innerHTML = `
                    <img src="/output/${filename}" alt="${filename}">
                `;

                imageGrid.appendChild(imageCard);
            });

            batchGroup.appendChild(imageGrid);
            imageContainer.appendChild(batchGroup);
        });
    } catch (error) {
        console.error('Error loading images:', error);
    }
}

// Load images when page loads
loadImages();