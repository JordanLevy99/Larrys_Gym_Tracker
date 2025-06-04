document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tabs
    const triggerTabList = document.querySelectorAll('#configTabs button');
    triggerTabList.forEach(triggerEl => {
        new bootstrap.Tab(triggerEl);
        triggerEl.addEventListener('click', event => {
            event.preventDefault();
            new bootstrap.Tab(triggerEl).show();
        });
    });
    
    // User management
    const userContainer = document.getElementById('userContainer');
    const userTemplate = document.getElementById('userTemplate');
    
    if (document.getElementById('addUserBtn')) {
        document.getElementById('addUserBtn').addEventListener('click', function() {
            const clone = document.importNode(userTemplate.content, true);
            userContainer.appendChild(clone);
            setupRemoveButtons();
        });
    }
    
    // Birthday songs management
    const birthdaySongContainer = document.getElementById('birthdaySongContainer');
    const birthdaySongTemplate = document.getElementById('birthdaySongTemplate');
    
    if (document.getElementById('addBirthdaySongBtn')) {
        document.getElementById('addBirthdaySongBtn').addEventListener('click', function() {
            const clone = document.importNode(birthdaySongTemplate.content, true);
            birthdaySongContainer.appendChild(clone);
            setupRemoveButtons();
        });
    }
    
    // Winner songs management
    const winnerSongContainer = document.getElementById('winnerSongContainer');
    const winnerSongTemplate = document.getElementById('winnerSongTemplate');
    
    if (document.getElementById('addWinnerSongBtn')) {
        document.getElementById('addWinnerSongBtn').addEventListener('click', function() {
            const clone = document.importNode(winnerSongTemplate.content, true);
            winnerSongContainer.appendChild(clone);
            setupRemoveButtons();
        });
    }
    
    // Set up remove buttons for existing entries
    setupRemoveButtons();
    
    function setupRemoveButtons() {
        document.querySelectorAll('.remove-entry').forEach(button => {
            button.addEventListener('click', function() {
                const entry = this.closest('.user-entry, .birthday-song-entry, .winner-song-entry');
                if (entry) {
                    entry.remove();
                }
            });
        });
    }
    
    // Form validation
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                
                // Find the first invalid field
                const invalidInputs = form.querySelectorAll(':invalid');
                if (invalidInputs.length > 0) {
                    // Find the tab containing the invalid field
                    const firstInvalidInput = invalidInputs[0];
                    const tabPane = firstInvalidInput.closest('.tab-pane');
                    
                    if (tabPane) {
                        // Get the id of the tab pane
                        const tabId = tabPane.id;
                        
                        // Activate the corresponding tab
                        const tab = document.querySelector(`button[data-bs-target="#${tabId}"]`);
                        if (tab) {
                            new bootstrap.Tab(tab).show();
                        }
                        
                        // Focus the invalid input
                        firstInvalidInput.focus();
                    }
                }
            }
            
            form.classList.add('was-validated');
        }, false);
    }
    
    // Extension toggle validation
    document.querySelectorAll('input[name="enabled_extensions"]').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            validateExtensionDependencies();
        });
    });
    
    function validateExtensionDependencies() {
        // Map of extensions to their required API keys
        const dependencies = {
            'sports_betting': ['api_odds'],
            'news_recommender': ['api_news', 'api_openai'],
            'exercise_of_the_day': ['api_openai'],
            'realtime_transcription': ['api_openai'],
            'stock_trading': ['api_finnhub'],
            'year_in_review': ['api_openai']
        };
        
        // Check which extensions are enabled
        document.querySelectorAll('input[name="enabled_extensions"]:checked').forEach(checkbox => {
            const extensionValue = checkbox.value;
            
            // If this extension has dependencies
            if (dependencies[extensionValue]) {
                dependencies[extensionValue].forEach(apiKey => {
                    const apiInput = document.getElementById(apiKey);
                    if (apiInput && !apiInput.value) {
                        // Add warning to the API key input
                        if (!apiInput.nextElementSibling || !apiInput.nextElementSibling.classList.contains('extension-warning')) {
                            const warning = document.createElement('div');
                            warning.className = 'alert alert-warning mt-2 extension-warning';
                            warning.textContent = `Required for the ${extensionValue.replace('_', ' ')} extension`;
                            apiInput.parentNode.insertBefore(warning, apiInput.nextElementSibling);
                        }
                    }
                });
            }
        });
        
        // Remove warnings for disabled extensions
        document.querySelectorAll('input[name="enabled_extensions"]:not(:checked)').forEach(checkbox => {
            const extensionValue = checkbox.value;
            
            if (dependencies[extensionValue]) {
                dependencies[extensionValue].forEach(apiKey => {
                    const apiInput = document.getElementById(apiKey);
                    if (apiInput) {
                        const warnings = apiInput.parentNode.querySelectorAll('.extension-warning');
                        warnings.forEach(warning => {
                            if (warning.textContent.includes(extensionValue.replace('_', ' '))) {
                                warning.remove();
                            }
                        });
                    }
                });
            }
        });
    }
    
    // Initial validation
    validateExtensionDependencies();
});