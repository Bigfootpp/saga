const languages = ['en', 'fr', 'es', 'de', 'it', 'pt', 'ru', 'in', 'nl', 'hu', 'la', 'multi'];

document.addEventListener('DOMContentLoaded', function () {
    updateProviderFields();
});

function setElementDisplay(elementId, displayStatus) {
    const element = document.getElementById(elementId);
    if (!element) {
        return;
    }
    element.style.display = displayStatus;
}

function updateProviderFields(isChangeEvent = false) {
    const tmdbEl = document.getElementById('tmdb');
    if (tmdbEl?.checked) {
        setElementDisplay('tmdb-fields', 'block');
    } else {
        setElementDisplay('tmdb-fields', 'none');
    }

    const getAllLangsEl = document.getElementById('get-all-languages');
    if (!getAllLangsEl?.checked) {
        setElementDisplay('languages-fields', 'block');
    } else {
        setElementDisplay('languages-fields', 'none');
    }
}

function loadData() {
    const currentUrl = window.location.href;
    let data = currentUrl.match(/\/([^\/]+)\/configure$/);
    if (data && data[1].startsWith("ey")) {
        data = atob(data[1]);
        data = JSON.parse(data);
        if (document.getElementById('jackett-fields')) {
            document.getElementById('jackett-host').value = data.jackettHost;
            document.getElementById('jackett-api').value = data.jackettApiKey;
        }
        document.getElementById('tmdb-api').value = data.tmdbApi;
        document.getElementById('tmdb').checked = data.metadataProvider === 'tmdb';
        document.getElementById('cinemeta').checked = data.metadataProvider === 'cinemeta';

        languages.forEach(language => {
            const el = document.getElementById(language);
            if (el && data.languages.includes(language)) el.checked = true;
        });

        const getAllLangsEl = document.getElementById('get-all-languages');
        if (getAllLangsEl) getAllLangsEl.checked = data.getAllLanguages;
    }
}

let showLanguageCheckBoxes = true;

function showCheckboxes() {
    let checkboxes = document.getElementById("languageCheckBoxes");
    if (!checkboxes) return;

    if (showLanguageCheckBoxes) {
        checkboxes.style.display = "block";
        showLanguageCheckBoxes = false;
    } else {
        checkboxes.style.display = "none";
        showLanguageCheckBoxes = true;
    }
}

loadData();

function getLink(method) {
    const addonHost = new URL(window.location.href).protocol.replace(':', '') + "://" + new URL(window.location.href).host;
    const jackettHost = document.getElementById('jackett-host')?.value;
    const jackettApi = document.getElementById('jackett-api')?.value;
    const tmdbApi = document.getElementById('tmdb-api')?.value;
    const metadataProvider = document.getElementById('tmdb')?.checked ? 'tmdb' : 'cinemeta';

    const selectedLanguages = [];
    languages.forEach(language => {
        const el = document.getElementById(language);
        if (el?.checked) selectedLanguages.push(language);
    });

    const getAllLanguages = document.getElementById('get-all-languages')?.checked || false;

    if (jackettHost === '' || jackettApi === '' || (metadataProvider === 'tmdb' && tmdbApi === '') || selectedLanguages.length === 0) {
        alert('Please fill all required fields');
        return false;
    }

    let data = {
        addonHost,
        jackettHost,
        jackettApiKey: jackettApi,
        tmdbApi,
        languages: selectedLanguages,
        getAllLanguages,
        metadataProvider
    };

    let stremio_link = `${window.location.host}/${btoa(JSON.stringify(data))}/manifest.json`;

    if (method === 'link') {
        window.open(`stremio://${stremio_link}`, "_blank");
    } else if (method === 'copy') {
        const link = window.location.protocol + '//' + stremio_link;

        if (!navigator.clipboard) {
            alert('Your browser does not support clipboard');
            console.log(link);
            return;
        }

        navigator.clipboard.writeText(link).then(() => {
            alert('Link copied to clipboard');
        }, () => {
            alert('Error copying link to clipboard');
        });
    }
}