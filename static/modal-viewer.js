// Modal Image Viewer Script
class ModalImageViewer {
  constructor() {
    this.modal = null;
    this.overlay = null;
    this.image = null;
    this.closeBtn = null;
    this.navBtns = { prev: null, next: null };
    this.imageCounter = null;
    this.currentImage = null;
    this.currentGroup = [];
    this.currentIndex = 0;
    
    this.init();
  }

  init() {
    this.createModal();
    this.bindEvents();
  }

  createModal() {
    // Create modal elements
    this.overlay = document.createElement('div');
    this.overlay.className = 'modal-overlay';
    
    this.modal = document.createElement('div');
    this.modal.className = 'modal-content';
    
    this.image = document.createElement('img');
    this.image.className = 'modal-image';
    
    this.closeBtn = document.createElement('button');
    this.closeBtn.className = 'close-btn';
    this.closeBtn.innerHTML = '&times;';
    this.closeBtn.setAttribute('aria-label', 'Close modal');
    
    const navContainer = document.createElement('div');
    navContainer.className = 'modal-nav';
    
    this.navBtns.prev = document.createElement('button');
    this.navBtns.prev.className = 'nav-btn';
    this.navBtns.prev.innerHTML = '&#10094;';
    this.navBtns.prev.setAttribute('aria-label', 'Previous image');
    
    this.navBtns.next = document.createElement('button');
    this.navBtns.next.className = 'nav-btn';
    this.navBtns.next.innerHTML = '&#10095;';
    this.navBtns.next.setAttribute('aria-label', 'Next image');
    
    this.imageCounter = document.createElement('div');
    this.imageCounter.className = 'image-counter';
    
    // Build modal structure
    navContainer.appendChild(this.navBtns.prev);
    navContainer.appendChild(this.navBtns.next);
    
    this.modal.appendChild(this.image);
    this.modal.appendChild(navContainer);
    this.overlay.appendChild(this.modal);
    this.overlay.appendChild(this.closeBtn);
    this.overlay.appendChild(this.imageCounter);
    
    // Add to document body
    document.body.appendChild(this.overlay);
  }

  bindEvents() {
    // Close modal when close button is clicked
    this.closeBtn.addEventListener('click', () => this.close());
    
    // Close modal when overlay is clicked (but not the modal content)
    this.overlay.addEventListener('click', (e) => {
      // If the clicked element is the overlay itself (not a child element), close the modal
      if (e.target === this.overlay) {
        this.close();
      }
    });
    
    // Navigation
    this.navBtns.prev.addEventListener('click', (e) => {
      e.stopPropagation(); // Prevent event bubbling to overlay
      this.showPrevImage();
    });
    this.navBtns.next.addEventListener('click', (e) => {
      e.stopPropagation(); // Prevent event bubbling to overlay
      this.showNextImage();
    });
    

    
    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
      if (!this.overlay.classList.contains('active')) return;
      
      switch(e.key) {
        case 'Escape':
          this.close();
          break;
        case 'ArrowLeft':
          this.showPrevImage();
          break;
        case 'ArrowRight':
          this.showNextImage();
          break;
      }
    });
  }

  async open(imageElement) {
    // Find all images in the same group (same parent container)
    this.currentGroup = Array.from(imageElement.closest('.image-grid').querySelectorAll('img'));
    this.currentIndex = this.currentGroup.indexOf(imageElement);
    
    this.currentImage = imageElement;
    this.image.src = imageElement.src;
    this.updateCounter();
    this.updateNavButtons();
    
    // Calculate scrollbar width and add padding to prevent layout shift
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    
    // Apply padding before showing modal to ensure smooth transition
    if (scrollbarWidth > 0) {
      document.body.style.paddingRight = `${scrollbarWidth}px`;
    }
    
    // Show modal with animation
    this.overlay.classList.add('active');
    document.body.style.overflow = 'hidden'; // Prevent background scrolling
  }

  close() {
    this.overlay.classList.remove('active');
    document.body.style.overflow = ''; // Restore scrolling
    
    // Remove padding after a brief delay to match the animation timing
    setTimeout(() => {
      document.body.style.paddingRight = ''; // Remove added padding
    }, 300); // Match the CSS transition duration
  }

  showNextImage() {
    if (this.currentIndex < this.currentGroup.length - 1) {
      this.currentIndex++;
      this.currentImage = this.currentGroup[this.currentIndex];
      this.image.src = this.currentImage.src;
      this.updateCounter();
      this.updateNavButtons();
    }
  }

  showPrevImage() {
    if (this.currentIndex > 0) {
      this.currentIndex--;
      this.currentImage = this.currentGroup[this.currentIndex];
      this.image.src = this.currentImage.src;
      this.updateCounter();
      this.updateNavButtons();
    }
  }

  updateCounter() {
    this.imageCounter.textContent = `${this.currentIndex + 1} / ${this.currentGroup.length}`;
  }

  updateNavButtons() {
    this.navBtns.prev.disabled = this.currentIndex === 0;
    this.navBtns.next.disabled = this.currentIndex === this.currentGroup.length - 1;
  }
}

// Initialize the modal when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  const modalViewer = new ModalImageViewer();
  
  // Add click event to all images in image cards
  document.addEventListener('click', (e) => {
    if (e.target.tagName === 'IMG' && e.target.closest('.image-card')) {
      modalViewer.open(e.target);
    }
  });
});