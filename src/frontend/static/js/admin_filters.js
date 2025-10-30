document.addEventListener('DOMContentLoaded', function() {
    const toggleBtn = document.createElement('button');
    const filterDiv = document.getElementById('changelist-filter');

    if (!filterDiv) return;

    // Always start with filters hidden (default is always hidden)
    const isHidden = true;

    // Get translated strings from global object, fallback to English if not available
    const i18n = window.adminFiltersI18n || {
        showFilters: 'Show Filters',
        hideFilters: 'Hide Filters'
    };

    toggleBtn.className = 'historylink';
    toggleBtn.textContent = isHidden ? i18n.showFilters : i18n.hideFilters;
    toggleBtn.type = 'button';

    // Apply initial state - default is hidden
    if (isHidden) {
        filterDiv.classList.add('hidden');
        document.body.classList.add('hidden-filters');
    }

    filterDiv.parentNode.insertBefore(toggleBtn, filterDiv);

    toggleBtn.addEventListener('click', function() {
        const currentlyHidden = filterDiv.classList.contains('hidden');

        if (currentlyHidden) {
            filterDiv.classList.remove('hidden');
            document.body.classList.remove('hidden-filters');
            toggleBtn.textContent = i18n.hideFilters;
            localStorage.setItem('admin-filters-hidden', 'false');
        } else {
            filterDiv.classList.add('hidden');
            document.body.classList.add('hidden-filters');
            toggleBtn.textContent = i18n.showFilters;
            localStorage.setItem('admin-filters-hidden', 'true');
        }
    });
});
