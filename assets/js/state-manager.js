/**
 * Centralized UI State Manager
 * Ensures consistent state across all frontend components
 */

class UIStateManager {
  constructor() {
    this.state = {
      isLoading: false,
      currentPage: 'home',
      errorMessage: null,
      successMessage: null,
      lastUpdate: null,
      proxiesLoaded: false,
      statisticsLoaded: false,
      dataUpdatedAt: null
    };

    this.listeners = new Map();
    this.initializeEventListeners();
  }

  /**
   * Subscribe to state changes
   * @param {string} key - State key to listen for
   * @param {Function} callback - Called when state[key] changes
   */
  subscribe(key, callback) {
    if (!this.listeners.has(key)) {
      this.listeners.set(key, []);
    }
    this.listeners.get(key).push(callback);
  }

  /**
   * Update state and notify listeners
   */
  setState(updates) {
    let changed = false;

    for (const [key, value] of Object.entries(updates)) {
      if (this.state[key] !== value) {
        this.state[key] = value;
        changed = true;

        // Notify listeners for this key
        if (this.listeners.has(key)) {
          this.listeners.get(key).forEach(callback => {
            try {
              callback(value);
            } catch (error) {
              console.error(`Listener error for ${key}:`, error);
            }
          });
        }
      }
    }

    // Global state change event
    if (changed) {
      window.dispatchEvent(new CustomEvent('stateChanged', { detail: this.state }));
    }
  }

  /**
   * Show loading state
   */
  setLoading(value, message = 'Loading...') {
    this.setState({
      isLoading: value,
      successMessage: null,
      errorMessage: null
    });

    if (value) {
      this.updateLoadingUI(message);
    } else {
      this.hideLoadingUI();
    }
  }

  /**
   * Show error message
   */
  setError(message, details = null) {
    console.error('UI Error:', message, details);

    this.setState({
      isLoading: false,
      errorMessage: message,
      successMessage: null
    });

    this.showErrorNotification(message);
  }

  /**
   * Show success message
   */
  setSuccess(message) {
    this.setState({
      isLoading: false,
      successMessage: message,
      errorMessage: null
    });

    this.showSuccessNotification(message);

    // Auto-hide after 5 seconds
    setTimeout(() => {
      this.setState({ successMessage: null });
      this.hideSuccessNotification();
    }, 5000);
  }

  /**
   * Update UI elements based on loading state
   */
  updateLoadingUI(message) {
    // Hide main content
    const mainContent = document.querySelector('main');
    if (mainContent) {
      mainContent.style.opacity = '0.5';
      mainContent.style.pointerEvents = 'none';
    }

    // Show or create loading overlay
    let loadingOverlay = document.getElementById('loading-overlay');
    if (!loadingOverlay) {
      loadingOverlay = document.createElement('div');
      loadingOverlay.id = 'loading-overlay';
      loadingOverlay.className = 'loading-overlay';
      document.body.appendChild(loadingOverlay);
    }

    loadingOverlay.innerHTML = `
      <div class="loading-spinner">
        <div class="spinner"></div>
        <p>${message}</p>
      </div>
    `;
    loadingOverlay.style.display = 'flex';
  }

  /**
   * Hide loading UI
   */
  hideLoadingUI() {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
      loadingOverlay.style.display = 'none';
    }

    const mainContent = document.querySelector('main');
    if (mainContent) {
      mainContent.style.opacity = '1';
      mainContent.style.pointerEvents = 'auto';
    }
  }

  /**
   * Show error notification
   */
  showErrorNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'notification notification-error';
    notification.innerHTML = `
      <div class="notification-content">
        <i data-feather="alert-circle" class="notification-icon"></i>
        <div class="notification-text">
          <h4>Error</h4>
          <p>${message}</p>
        </div>
        <button class="notification-close" onclick="this.parentElement.parentElement.remove()">
          <i data-feather="x"></i>
        </button>
      </div>
    `;

    document.body.appendChild(notification);

    // Initialize feather icons
    if (window.feather) {
      window.feather.replace();
    }

    // Auto-hide after 8 seconds
    setTimeout(() => {
      if (notification.parentElement) {
        notification.remove();
      }
    }, 8000);
  }

  /**
   * Show success notification
   */
  showSuccessNotification(message) {
    const notification = document.createElement('div');
    notification.id = 'success-notification';
    notification.className = 'notification notification-success';
    notification.innerHTML = `
      <div class="notification-content">
        <i data-feather="check-circle" class="notification-icon"></i>
        <div class="notification-text">
          <p>${message}</p>
        </div>
        <button class="notification-close" onclick="this.parentElement.parentElement.remove()">
          <i data-feather="x"></i>
        </button>
      </div>
    `;

    document.body.appendChild(notification);

    if (window.feather) {
      window.feather.replace();
    }
  }

  /**
   * Hide success notification
   */
  hideSuccessNotification() {
    const notification = document.getElementById('success-notification');
    if (notification) {
      notification.remove();
    }
  }

  /**
   * Set current page
   */
  setCurrentPage(page) {
    this.setState({ currentPage: page });
  }

  /**
   * Initialize global event listeners
   */
  initializeEventListeners() {
    // Listen for data updates from cache manager
    window.addEventListener('dataUpdated', (event) => {
      this.setState({ lastUpdate: event.detail.generated_at });
    });
  }
}

// Create global instance
window.stateManager = new UIStateManager();

console.log('✅ UIStateManager initialized');