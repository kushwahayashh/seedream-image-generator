// DOM Elements
const elements = {
    generateForm: document.getElementById('generateForm'),
    statusMessage: document.getElementById('statusMessage'),
    spinner: document.getElementById('spinner'),
    imageContainer: document.getElementById('imageContainer')
};

// State
let currentSkeletonIds = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    elements.generateForm.addEventListener('submit', handleFormSubmit);
    loadImages();
});

// Handle form submission
async function handleFormSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(elements.generateForm);
    const numImages = parseInt(formData.get('num_images')) || 1;
    
    // Clean form data
    formData.delete('height');
    formData.delete('width');
    
    // Show loading state
    showLoading();
    
    // Get prompt details for skeleton cards
    const prompt = formData.get('prompt') || 'Generating image...';
    const aspectRatio = formData.get('aspect_ratio') || '4:3';
    
    // Create skeleton cards
    createSkeletonCards(prompt, aspectRatio, numImages);
    
    try {
        const response = await fetch('/generate', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showSuccess(`Batch created successfully! Batch ID: ${result.batch_id}`);
            pollTasks(result.task_ids, result.batch_id, numImages);
        } else {
            showError(`Error: ${result.message}`);
        }
    } catch (error) {
        showError(`Error: ${error.message}`);
    } finally {
        hideLoading();
    }
}

// Show loading state
function showLoading() {
    elements.spinner.classList.add('active');
    elements.statusMessage.classList.remove('active', 'success', 'error');
}

// Hide loading state
function hideLoading() {
    elements.spinner.classList.remove('active');
}

// Show success message
function showSuccess(message) {
    elements.statusMessage.textContent = message;
    elements.statusMessage.className = 'status active success';
}

// Show error message
function showError(message) {
    elements.statusMessage.textContent = message;
    elements.statusMessage.className = 'status active error';
}

// Create skeleton cards for loading state
function createSkeletonCards(prompt, aspectRatio, numImages) {
    // Remove existing skeleton group
    removeSkeletonGroup();
    
    // Create new skeleton group
    const skeletonGroup = document.createElement('div');
    skeletonGroup.className = 'prompt-group';
    skeletonGroup.id = 'skeleton-group';
    
    // Add prompt text
    const promptText = document.createElement('div');
    promptText.className = 'prompt-text';
    promptText.textContent = prompt;
    skeletonGroup.appendChild(promptText);
    
    // Create skeleton grid
    const skeletonGrid = document.createElement('div');
    skeletonGrid.className = 'image-grid';
    skeletonGrid.id = 'skeleton-grid';
    
    // Add skeleton cards
    currentSkeletonIds = [];
    const skeletonHeight = getSkeletonHeight(aspectRatio);
    
    for (let i = 0; i < numImages; i++) {
        const skeletonId = `skeleton-${Date.now()}-${i}`;
        currentSkeletonIds.push(skeletonId);
        
        const skeletonCard = createSkeletonCard(skeletonId, skeletonHeight);
        skeletonGrid.appendChild(skeletonCard);
    }
    
    skeletonGroup.appendChild(skeletonGrid);
    elements.imageContainer.insertBefore(skeletonGroup, elements.imageContainer.firstChild);
}

// Create individual skeleton card
function createSkeletonCard(id, height) {
    const card = document.createElement('div');
    card.className = 'skeleton-card';
    card.id = id;
    
    const skeletonImage = document.createElement('div');
    skeletonImage.className = 'skeleton-image';
    skeletonImage.style.height = height;
    skeletonImage.textContent = 'Generating...';
    
    card.appendChild(skeletonImage);
    return card;
}

// Remove skeleton group
function removeSkeletonGroup() {
    const skeletonGroup = document.getElementById('skeleton-group');
    if (skeletonGroup) {
        skeletonGroup.remove();
    }
    currentSkeletonIds = [];
}

// Poll multiple tasks
function pollTasks(taskIds, batchId, numImages) {
    let completedTasks = 0;
    
    taskIds.forEach(taskId => {
        pollTaskStatus(taskId, () => {
            completedTasks++;
            if (completedTasks === taskIds.length) {
                showSuccess(`Batch ${batchId} completed successfully! Generated ${numImages} images.`);
            }
        });
    });
}

// Poll individual task status
function pollTaskStatus(taskId, onComplete) {
    const checkStatus = async () => {
        try {
            const response = await fetch(`/task_status/${taskId}`);
            const result = await response.json();
            
            if (result.completed) {
                if (result.status === 'succeeded') {
                    loadImages();
                } else {
                    showError('Task failed: ' + (result.error || 'Unknown error'));
                }
                
                if (onComplete) onComplete();
                return;
            }
            
            // Continue polling
            setTimeout(checkStatus, 5000);
        } catch (error) {
            showError('Error checking task status: ' + error.message);
            if (onComplete) onComplete();
        }
    };
    
    checkStatus();
}

// Calculate skeleton height based on aspect ratio
function getSkeletonHeight(aspectRatio) {
    const baseWidth = 300;
    const ratios = {
        '1:1': 1,
        '4:3': 3/4,
        '16:9': 9/16,
        '9:16': 16/9,
        '3:2': 2/3
    };
    
    const multiplier = ratios[aspectRatio] || 3/4;
    return `${baseWidth * multiplier}px`;
}

// Load and display images
async function loadImages() {
    try {
        const response = await fetch('/images');
        const result = await response.json();
        
        // Clear existing content
        elements.imageContainer.innerHTML = '';
        currentSkeletonIds = [];
        
        if (!result.batches || result.batches.length === 0) {
            elements.imageContainer.innerHTML = '<p>No images found in the output folder.</p>';
            return;
        }
        
        // Render batches
        result.batches.forEach(batch => {
            elements.imageContainer.appendChild(createBatchGroup(batch));
        });
    } catch (error) {
        console.error('Error loading images:', error);
    }
}

// Create batch group element
function createBatchGroup(batch) {
    const batchGroup = document.createElement('div');
    batchGroup.className = 'prompt-group';
    
    // Add prompt text
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
    
    // Add image grid
    const imageGrid = document.createElement('div');
    imageGrid.className = 'image-grid';
    
    batch.images.forEach(filename => {
        imageGrid.appendChild(createImageCard(filename));
    });
    
    batchGroup.appendChild(imageGrid);
    return batchGroup;
}

// Create image card element
function createImageCard(filename) {
    const imageCard = document.createElement('div');
    imageCard.className = 'image-card';
    
    const img = document.createElement('img');
    img.src = `/output/${filename}`;
    img.alt = filename;
    
    imageCard.appendChild(img);
    return imageCard;
}