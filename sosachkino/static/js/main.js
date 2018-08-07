// Filter threads by text in input
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

var threadInput = document.getElementById('thread-input');
threadInput.addEventListener('input', function (e) {
    filterThreads(e.target.value.toLowerCase());
});

var resetBtn = document.getElementById('reset-thread');
resetBtn.addEventListener('click', function (e) {
    e.preventDefault();
    threadInput.value = '';
    filterThreads('');
});

// Stop all videos except played
var videos = document.getElementsByClassName('video');
for (var i = 0, j = videos.length; i < j; i++) {
    videos[i].addEventListener('play', function (e) {
        for (var k = 0; k < j; k++) {
            if (videos[k] !== this &&
                videos[k].played.length &&
                !videos[k].paused) {
                videos[k].pause();
            }
        }
    });
};
