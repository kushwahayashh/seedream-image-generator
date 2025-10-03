// DOM Elements
const els = {
  form: document.getElementById('generateForm'),
  status: document.getElementById('statusMessage'),
  spinner: document.getElementById('spinner'),
  container: document.getElementById('imageContainer')
};

// State
let skeletonIds = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  els.form.addEventListener('submit', handleSubmit);
  loadImages();
});

// Handle form submission
async function handleSubmit(e) {
  e.preventDefault();
  
  const fd = new FormData(els.form);
  const numImages = parseInt(fd.get('num_images')) || 1;
  
  // Clean form data
  fd.delete('height');
  fd.delete('width');
  
  // Show loading state
  showLoading();
  
  // Get prompt details for skeleton cards
  const prompt = fd.get('prompt') || 'Generating image...';
  const aspectRatio = fd.get('aspect_ratio') || '4:3';
  
  // Create skeleton cards
  createSkeletonCards(prompt, aspectRatio, numImages);
  
  try {
    const response = await fetch('/generate', {
      method: 'POST',
      body: fd
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
  els.spinner.classList.add('active');
  els.status.classList.remove('active', 'success', 'error');
}

// Hide loading state
function hideLoading() {
  els.spinner.classList.remove('active');
}

// Show status message
function showMessage(text, type) {
  els.status.textContent = text;
  els.status.className = `status active ${type}`;
}

// Show success message
function showSuccess(message) {
  showMessage(message, 'success');
}

// Show error message
function showError(message) {
  showMessage(message, 'error');
}

// Create skeleton cards for loading state
function createSkeletonCards(prompt, aspectRatio, numImages) {
  // Remove existing skeleton group
  removeSkeletonGroup();
  
  // Create new skeleton group
  const group = document.createElement('div');
  group.className = 'prompt-group';
  group.id = 'skeleton-group';
  
  // Add prompt text
  const promptEl = document.createElement('div');
  promptEl.className = 'prompt-text';
  promptEl.textContent = prompt;
  group.appendChild(promptEl);
  
  // Create skeleton grid
  const grid = document.createElement('div');
  grid.className = 'image-grid';
  grid.id = 'skeleton-grid';
  
  // Add skeleton cards
  skeletonIds = [];
  const height = calcSkeletonHeight(aspectRatio);
  
  for (let i = 0; i < numImages; i++) {
    const id = `skeleton-${Date.now()}-${i}`;
    skeletonIds.push(id);
    grid.appendChild(createSkeletonCard(id, height));
  }
  
  group.appendChild(grid);
  els.container.insertBefore(group, els.container.firstChild);
}

// Create individual skeleton card
function createSkeletonCard(id, height) {
  const card = document.createElement('div');
  card.className = 'skeleton-card';
  card.id = id;
  
  const skeletonImg = document.createElement('div');
  skeletonImg.className = 'skeleton-image';
  skeletonImg.style.height = height;
  skeletonImg.textContent = 'Generating...';
  
  card.appendChild(skeletonImg);
  return card;
}

// Remove skeleton group
function removeSkeletonGroup() {
  const skeletonGroup = document.getElementById('skeleton-group');
  if (skeletonGroup) skeletonGroup.remove();
  skeletonIds = [];
}

// Poll multiple tasks
function pollTasks(taskIds, batchId, numImages) {
  let completed = 0;
  
  taskIds.forEach(taskId => {
    pollTaskStatus(taskId, () => {
      completed++;
      if (completed === taskIds.length) {
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
function calcSkeletonHeight(aspectRatio) {
  const ratios = {
    '1:1': 1,
    '4:3': 0.75,
    '16:9': 0.5625,
    '9:16': 1.7778,
    '3:2': 0.6667
  };
  
  const multiplier = ratios[aspectRatio] || 0.75;
  return `${300 * multiplier}px`;
}

// Load and display images
async function loadImages() {
  try {
    const response = await fetch('/images');
    const result = await response.json();
    
    // Clear existing content
    els.container.innerHTML = '';
    skeletonIds = [];
    
    if (!result.batches?.length) {
      els.container.innerHTML = '<p>No images found in the output folder.</p>';
      return;
    }
    
    // Render batches
    result.batches.forEach(batch => {
      els.container.appendChild(createBatchGroup(batch));
    });
  } catch (error) {
    console.error('Error loading images:', error);
  }
}

// Create batch group element
function createBatchGroup(batch) {
  const group = document.createElement('div');
  group.className = 'prompt-group';
  
  // Add prompt text
  const promptEl = document.createElement('div');
  promptEl.className = 'prompt-text';
  promptEl.textContent = batch.prompt;
  group.appendChild(promptEl);
  
  // Add batch metadata
  const meta = document.createElement('div');
  meta.className = 'task-meta';
  meta.innerHTML = `
    <span class="task-id">Batch ID: ${batch.id}</span>
    <span class="task-date">${new Date(batch.created_at).toLocaleString()}</span>
    <span class="task-size">${batch.aspect_ratio} • ${batch.size} • ${batch.images.length} images</span>
  `;
  group.appendChild(meta);
  
  // Add image grid
  const grid = document.createElement('div');
  grid.className = 'image-grid';
  
  batch.images.forEach(file => grid.appendChild(createImageCard(file)));
  
  group.appendChild(grid);
  return group;
}

// Create image card element
function createImageCard(filename) {
  const card = document.createElement('div');
  card.className = 'image-card';
  
  const img = document.createElement('img');
  img.src = `/output/${filename}`;
  img.alt = filename;
  
  card.appendChild(img);
  return card;
}

