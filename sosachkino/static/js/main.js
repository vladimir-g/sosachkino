var filterThreads = function (query) {
    var query = query.toLowerCase();
    var checks = document.querySelectorAll('#thread-filter div.form-check');
    for (var i = 0; i < checks.length; i++) {
        if (checks[i].dataset.search.indexOf(query) === -1) {
            checks[i].style.display = 'none';
        } else {
            checks[i].style.display = 'block';
        }
    }
};

document.getElementById('thread-input').addEventListener('input', function (e) {
    filterThreads(e.target.value.toLowerCase());
});

document.getElementById('reset-thread').addEventListener('click', function (e) {
    e.preventDefault();
    document.getElementById('thread-input').value = '';
    filterThreads('');
});
