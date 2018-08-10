/* Utilities */

var byId = function (id) { return document.getElementById(id); };

var setSetting = function (key, value) {
    try {
        window.localStorage.setItem(key, String(value));
    } catch (e) {
    }
};

var getSetting = function (key, default_) {
    try {
        var value = window.localStorage.getItem(key);
        if (value === null)
            return default_;
        return value;
    } catch (e) {
        return default_;
    }
};

/* Settings */

// Load settings on page load
var useJsPlayer = getSetting('js-player') === 'true';

// Init settings dialog
var settingsBtn = byId('settings-btn');
var settingsDialog = byId('settings-dialog');
var settingsOverlay = byId('settings-overlay');

var hideSettings = function () {
    settingsDialog.style.display = 'none';
    settingsOverlay.style.display = 'none';
};

settingsBtn.addEventListener('click', function (e) {
    e.preventDefault();
    settingsDialog.style.display = 'block';
    settingsOverlay.style.display = 'block';
});

// Closing settings dialog
settingsDialog.addEventListener('click', function (e) {
    if (e.target !== this)
        return;
    hideSettings();
});
var close = document.getElementsByClassName("settings-close");
for (var i = 0; i < close.length; i++) {
    close[i].addEventListener('click', hideSettings);
}

if (useJsPlayer) {
    byId('use-js-player').checked = true;
}

// Saving settings
byId('save-settings').addEventListener('click', function (e) {
    useJsPlayer = byId('use-js-player').checked;
    setSetting('js-player', useJsPlayer);
    hideSettings();
    updateControls();
});

/* Filter */

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

var threadInput = byId('thread-input');
threadInput.addEventListener('input', function (e) {
    filterThreads(e.target.value.toLowerCase());
});

var resetBtn = byId('reset-thread');
resetBtn.addEventListener('click', function (e) {
    e.preventDefault();
    threadInput.value = '';
    filterThreads('');
});

/* Video player */

var lightBox = byId('lightbox');
var videos = document.getElementsByClassName('video');
var currentIndex = null;

// Play video in lightbox
var playVideo = function (index) {
    console.log(index);
    if (index < 0 || index > videos.length - 1)
        return;
    var source = videos[index];
    var src = source.src;
    var video = byId('video-item');
    if (!video) {
        video = document.createElement('video');
        video.id = 'video-item';
        video.controls = true;
        lightBox.appendChild(video);
    } else {
        video.pause();
    }
    video.src = src;
    byId('video-counter').textContent =
        "".concat(index + 1, '/', videos.length);
    byId('video-name').textContent = source.dataset.name;
    lightBox.style.display = 'block';
    video.play();
    currentIndex = index;
    var prevDisp = (index < 1) ? 'none' : 'block';
    var nextDisp = (index > videos.length - 2) ? 'none' : 'block';
    byId('prev').style.display = prevDisp;
    byId('next').style.display = nextDisp;
};

// Enable or disable controls depending on js player
var updateControls = function () {
    for (var i = 0, j = videos.length; i < j; i++) {
        videos[i].controls = !useJsPlayer;
        videos[i].preload = (useJsPlayer) ? 'none' : 'metadata';
    }
};

// Add click handlers for play (no lightbox) and click
for (var i = 0, j = videos.length; i < j; i++) {
    videos[i].addEventListener('play', function (e) {
        if (useJsPlayer) {
            return;
        }
        for (var k = 0; k < j; k++) {
            if (videos[k] !== this &&
                !videos[k].paused) {
                videos[k].pause();
            }
        }
    });
    (function (i) {
        videos[i].addEventListener('click', function (e) {
            if (!useJsPlayer) {
                return;
            }
            e.preventDefault();
            playVideo(i);
        });
    })(i);
};

updateControls();

/* Lightbox */

// Closing lightbox
var lightBoxClose = function () {
    lightBox.style.display = 'none';
    lightBox.removeChild(byId('video-item'));
}

lightBox.addEventListener('click', lightBoxClose);
var closeBox = lightBox.getElementsByClassName("close");
for (var i = 0; i < closeBox.length; i++) {
    closeBox[i].addEventListener('click', lightBoxClose);
}

byId('prev').addEventListener('click', function (e) {
    e.preventDefault();
    e.stopPropagation();
    if (currentIndex < 1)
        return;
    playVideo(currentIndex - 1);
});

byId('next').addEventListener('click', function (e) {
    console.log('n');
    e.preventDefault();
    e.stopPropagation();
    if (currentIndex > videos.length - 1)
        return;
    playVideo(currentIndex + 1);
});
