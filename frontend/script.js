document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('agent-form');
    const loadingDiv = document.getElementById('loading');
    const resultsContainer = document.getElementById('results-container');
    const resultsPre = document.getElementById('results');

    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        // Hide previous results and show loading
        resultsContainer.classList.add('hidden');
        loadingDiv.classList.remove('hidden');

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        try {
            const response = await fetch('/api/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'An unknown error occurred.');
            }

            const result = await response.json();

            // Display results
            resultsPre.textContent = JSON.stringify(result, null, 2);
            resultsContainer.classList.remove('hidden');

        } catch (error) {
            resultsPre.textContent = `Error: ${error.message}`;
            resultsContainer.classList.remove('hidden');
        } finally {
            // Hide loading
            loadingDiv.classList.add('hidden');
        }
    });
});
