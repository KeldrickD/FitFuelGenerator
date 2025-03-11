// Tutorial steps configuration
const tutorialSteps = [
  {
    element: '[data-tutorial="brand"]',
    title: 'Welcome to FitFuel!',
    content: 'Your all-in-one platform for managing client workouts and nutrition plans.',
    placement: 'bottom'
  },
  {
    element: '[data-tutorial="dashboard"]',
    title: 'Dashboard Overview',
    content: 'Get a quick overview of all your clients and their progress.',
    placement: 'right'
  },
  {
    element: '[data-tutorial="create-plan"]',
    title: 'Create New Plans',
    content: 'Create personalized workout and nutrition plans for your clients.',
    placement: 'left'
  },
  {
    element: '[data-tutorial="clients"]',
    title: 'Client Management',
    content: 'View and manage all your clients in one place.',
    placement: 'bottom'
  },
  {
    element: '[data-tutorial="meal-planner"]',
    title: 'Meal Planning',
    content: 'Create and customize meal plans for your clients.',
    placement: 'left'
  }
];

class TutorialOverlay {
  constructor() {
    this.currentStep = 0;
    this.overlay = document.getElementById('tutorialOverlay');
    this.tooltipElement = document.getElementById('tutorialTooltip');
    this.init();
  }

  init() {
    try {
      // Add navigation event listeners
      document.getElementById('skipTutorial').addEventListener('click', () => this.complete());
      document.getElementById('prevStep').addEventListener('click', () => this.showStep(this.currentStep - 1));
      document.getElementById('nextStep').addEventListener('click', () => this.showStep(this.currentStep + 1));
    } catch (error) {
      console.error('Error initializing tutorial:', error);
    }
  }

  start() {
    try {
      if (localStorage.getItem('tutorialCompleted')) {
        return;
      }

      this.overlay.classList.remove('d-none');
      this.tooltipElement.classList.remove('d-none');
      this.showStep(0);
    } catch (error) {
      console.error('Error starting tutorial:', error);
      this.handleError();
    }
  }

  showStep(stepIndex) {
    try {
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

      // Remove previous highlights
      document.querySelectorAll('.tutorial-highlight').forEach(el => {
        el.classList.remove('tutorial-highlight');
      });

      // Update current step
      this.currentStep = stepIndex;

      // Add highlight to current element
      targetElement.classList.add('tutorial-highlight');

      // Position tooltip
      this.positionTooltip(targetElement, step.placement);

      // Update content
      this.tooltipElement.querySelector('.tutorial-title').textContent = step.title;
      this.tooltipElement.querySelector('.tutorial-description').textContent = step.content;

      // Update navigation buttons
      document.getElementById('prevStep').disabled = stepIndex === 0;
      document.getElementById('nextStep').textContent = 
        stepIndex === tutorialSteps.length - 1 ? 'Finish' : 'Next';

    } catch (error) {
      console.error('Error showing tutorial step:', error);
      this.handleError();
    }
  }

  positionTooltip(targetElement, placement) {
    try {
      const elementRect = targetElement.getBoundingClientRect();
      const tooltipRect = this.tooltipElement.getBoundingClientRect();

      let top, left;
      const margin = 12; // Space between target and tooltip

      switch(placement) {
        case 'bottom':
          top = elementRect.bottom + margin;
          left = elementRect.left + (elementRect.width / 2) - (tooltipRect.width / 2);
          break;
        case 'right':
          top = elementRect.top + (elementRect.height / 2) - (tooltipRect.height / 2);
          left = elementRect.right + margin;
          break;
        case 'left':
          top = elementRect.top + (elementRect.height / 2) - (tooltipRect.height / 2);
          left = elementRect.left - tooltipRect.width - margin;
          break;
        default: // top
          top = elementRect.top - tooltipRect.height - margin;
          left = elementRect.left + (elementRect.width / 2) - (tooltipRect.width / 2);
      }

      // Ensure tooltip stays within viewport
      left = Math.max(margin, Math.min(left, window.innerWidth - tooltipRect.width - margin));
      top = Math.max(margin, Math.min(top, window.innerHeight - tooltipRect.height - margin));

      this.tooltipElement.style.top = `${top}px`;
      this.tooltipElement.style.left = `${left}px`;
    } catch (error) {
      console.error('Error positioning tooltip:', error);
    }
  }

  complete() {
    try {
      localStorage.setItem('tutorialCompleted', 'true');
      this.overlay.classList.add('d-none');
      this.tooltipElement.classList.add('d-none');
      document.querySelectorAll('.tutorial-highlight').forEach(el => {
        el.classList.remove('tutorial-highlight');
      });
    } catch (error) {
      console.error('Error completing tutorial:', error);
    }
  }

  handleError() {
    try {
      // Clean up any visual elements
      this.overlay?.classList.add('d-none');
      this.tooltipElement?.classList.add('d-none');
      document.querySelectorAll('.tutorial-highlight').forEach(el => {
        el.classList.remove('tutorial-highlight');
      });
    } catch (error) {
      console.error('Error handling tutorial error:', error);
    }
  }
}

// Global initialization function
window.initTutorial = function() {
  try {
    const tutorial = new TutorialOverlay();
    tutorial.start();
  } catch (error) {
    console.error('Error initializing tutorial:', error);
  }
};