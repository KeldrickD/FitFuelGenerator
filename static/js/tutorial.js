// Tutorial steps configuration
const tutorialSteps = [
  {
    element: '.navbar-brand',
    title: 'Welcome to FitFuel!',
    content: 'Your all-in-one platform for managing client workouts and nutrition plans.',
    placement: 'bottom'
  },
  {
    element: '[data-feature="dashboard"]',
    title: 'Dashboard Overview',
    content: 'Get a quick overview of all your clients and their progress.',
    placement: 'right'
  },
  {
    element: '[data-feature="create-plan"]',
    title: 'Create New Plans',
    content: 'Create personalized workout and nutrition plans for your clients.',
    placement: 'left'
  },
  {
    element: '[data-feature="clients"]',
    title: 'Client Management',
    content: 'View and manage all your clients in one place.',
    placement: 'bottom'
  },
  {
    element: '[data-feature="meal-planner"]',
    title: 'Meal Planning',
    content: 'Create and customize meal plans for your clients.',
    placement: 'left'
  },
  {
    element: '[data-feature="achievements"]',
    title: 'Achievement System',
    content: 'Track client progress and celebrate their milestones.',
    placement: 'bottom'
  }
];

class TutorialOverlay {
  constructor() {
    this.currentStep = 0;
    this.overlay = null;
    this.tooltipElement = null;
  }

  start() {
    if (localStorage.getItem('tutorialCompleted')) {
      return;
    }

    this.createOverlay();
    this.showStep(0);

    // Add skip button event listener
    document.getElementById('skipTutorial').addEventListener('click', () => {
      this.complete();
    });
  }

  createOverlay() {
    // Create main overlay
    this.overlay = document.createElement('div');
    this.overlay.className = 'tutorial-overlay';
    
    // Create tooltip element
    this.tooltipElement = document.createElement('div');
    this.tooltipElement.className = 'tutorial-tooltip';
    this.tooltipElement.innerHTML = `
      <div class="tutorial-content">
        <h4 class="tutorial-title"></h4>
        <p class="tutorial-text"></p>
        <div class="tutorial-controls">
          <button class="btn btn-sm btn-secondary" id="skipTutorial">Skip Tutorial</button>
          <div class="tutorial-navigation">
            <button class="btn btn-sm btn-primary tutorial-prev" style="display: none;">Previous</button>
            <button class="btn btn-sm btn-primary tutorial-next">Next</button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(this.overlay);
    document.body.appendChild(this.tooltipElement);

    // Add navigation event listeners
    this.tooltipElement.querySelector('.tutorial-prev').addEventListener('click', () => {
      this.showStep(this.currentStep - 1);
    });
    this.tooltipElement.querySelector('.tutorial-next').addEventListener('click', () => {
      this.showStep(this.currentStep + 1);
    });
  }

  showStep(stepIndex) {
    if (stepIndex < 0 || stepIndex >= tutorialSteps.length) {
      this.complete();
      return;
    }

    const step = tutorialSteps[stepIndex];
    const targetElement = document.querySelector(step.element);
    
    if (!targetElement) {
      console.warn(`Tutorial target element not found: ${step.element}`);
      this.showStep(stepIndex + 1);
      return;
    }

    // Update current step
    this.currentStep = stepIndex;

    // Position tooltip
    const elementRect = targetElement.getBoundingClientRect();
    const tooltipRect = this.tooltipElement.getBoundingClientRect();
    
    let top, left;
    switch(step.placement) {
      case 'bottom':
        top = elementRect.bottom + 10;
        left = elementRect.left + (elementRect.width / 2) - (tooltipRect.width / 2);
        break;
      case 'right':
        top = elementRect.top + (elementRect.height / 2) - (tooltipRect.height / 2);
        left = elementRect.right + 10;
        break;
      case 'left':
        top = elementRect.top + (elementRect.height / 2) - (tooltipRect.height / 2);
        left = elementRect.left - tooltipRect.width - 10;
        break;
      default:
        top = elementRect.top - tooltipRect.height - 10;
        left = elementRect.left + (elementRect.width / 2) - (tooltipRect.width / 2);
    }

    // Update tooltip content and position
    this.tooltipElement.querySelector('.tutorial-title').textContent = step.title;
    this.tooltipElement.querySelector('.tutorial-text').textContent = step.content;
    this.tooltipElement.style.top = `${top}px`;
    this.tooltipElement.style.left = `${left}px`;

    // Update navigation buttons
    this.tooltipElement.querySelector('.tutorial-prev').style.display = 
      stepIndex > 0 ? 'inline-block' : 'none';
    this.tooltipElement.querySelector('.tutorial-next').textContent = 
      stepIndex === tutorialSteps.length - 1 ? 'Finish' : 'Next';

    // Highlight current element
    targetElement.classList.add('tutorial-highlight');
  }

  complete() {
    localStorage.setItem('tutorialCompleted', 'true');
    this.overlay.remove();
    this.tooltipElement.remove();
    document.querySelectorAll('.tutorial-highlight').forEach(el => {
      el.classList.remove('tutorial-highlight');
    });
  }
}

// Initialize tutorial when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  const tutorial = new TutorialOverlay();
  
  // Start tutorial for new users
  if (!localStorage.getItem('tutorialCompleted')) {
    tutorial.start();
  }

  // Add manual trigger (for testing or user-initiated tutorial)
  window.startTutorial = () => {
    localStorage.removeItem('tutorialCompleted');
    tutorial.start();
  };
});
