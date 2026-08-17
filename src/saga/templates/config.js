const sorts = ['quality', 'seedsdesc', 'sizedesc', 'sizeasc', 'qualitythensize'];
const qualityExclusions = ['4k', '1080p', '720p', '480p', 'rips', 'cam', 'unknown'];
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
    const jackettEl = document.getElementById('jackett');
    if (jackettEl?.checked) {
        setElementDisplay('jackett-fields', 'block');
    } else {
        setElementDisplay('jackett-fields', 'none');
    }
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
        const jackettEl = document.getElementById('jackett');
        if (jackettEl) jackettEl.checked = data.jackett;
        document.getElementById('torrenting').checked = data.torrenting;
        document.getElementById('tmdb').checked = data.metadataProvider === 'tmdb';
        document.getElementById('cinemeta').checked = data.metadataProvider === 'cinemeta';

        sorts.forEach(sort => {
            const el = document.getElementById(sort);
            if (el && data.sort === sort) el.checked = true;
        });

        qualityExclusions.forEach(quality => {
            const el = document.getElementById(quality);
            if (el && data.exclusion.includes(quality)) el.checked = true;
        });

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
    const tmdbApi = document.getElementById('tmdb-api').value;
    const exclusionKeywords = document.getElementById('exclusion-keywords')?.value.split(',').map(keyword => keyword.trim()).filter(keyword => keyword !== '') || [];
    let maxSize = document.getElementById('maxSize')?.value || '';
    let resultsPerQuality = document.getElementById('resultsPerQuality')?.value || '';
    let maxResults = document.getElementById('maxResults')?.value || '';
    const jackett = document.getElementById('jackett')?.checked || false;
    const torrenting = document.getElementById('torrenting')?.checked || false;
    const metadataProvider = document.getElementById('tmdb')?.checked ? 'tmdb' : 'cinemeta';
    const selectedQualityExclusion = [];

    qualityExclusions.forEach(quality => {
        const el = document.getElementById(quality);
        if (el?.checked) selectedQualityExclusion.push(quality);
    });

    const selectedLanguages = [];
    languages.forEach(language => {
        const el = document.getElementById(language);
        if (el?.checked) selectedLanguages.push(language);
    });

    const getAllLanguages = document.getElementById('get-all-languages')?.checked || false;

    let filter;
    sorts.forEach(sort => {
        const el = document.getElementById(sort);
        if (el?.checked) filter = sort;
    });

    if (maxSize === '' || isNaN(maxSize)) maxSize = 0;
    if (maxResults === '' || isNaN(maxResults)) maxResults = 5;
    if (resultsPerQuality === '' || isNaN(resultsPerQuality)) resultsPerQuality = 1;

    let data = {
        addonHost,
        jackettHost,
        'jackettApiKey': jackettApi,
        maxSize,
        exclusionKeywords,
        'languages': selectedLanguages,
        getAllLanguages,
        'sort': filter,
        resultsPerQuality,
        maxResults,
        'exclusion': selectedQualityExclusion,
        tmdbApi,
        jackett,
        torrenting,
        metadataProvider
    };

    if ((jackett && (jackettHost === '' || jackettApi === '')) || (metadataProvider === 'tmdb' && tmdbApi === '') || selectedLanguages.length === 0) {
        alert('Please fill all required fields');
        return false;
    }
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