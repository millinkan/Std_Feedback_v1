/**
 * Optional UI helpers — matches page syncs Bootstrap tabs from ?tab=
 */
document.addEventListener('DOMContentLoaded', function () {
    var params = new URLSearchParams(window.location.search);
    var tabId = params.get('tab');
    if (tabId === 'completed' || tabId === 'upcoming') {
        var trigger = document.querySelector('[data-bs-toggle="tab"][href="#' + tabId + '"]');
        if (trigger && typeof bootstrap !== 'undefined') new bootstrap.Tab(trigger).show();
    }
});
