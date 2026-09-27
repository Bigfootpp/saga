const languages = ['en', 'fr', 'es', 'de', 'it', 'pt', 'pt-BR', 'ja', 'ru', 'hi', 'nl', 'hu', 'pl', 'mul'];

document.addEventListener('DOMContentLoaded', function () {
    initLanguageListeners();
    loadData();
});

function getLanguageCheckboxes() {
    return Array.from(document.querySelectorAll('#languageCheckBoxes input[type="checkbox"]'));
}

function normalizeLang(value) {
    return value === 'multi' ? 'mul' : value;
}

function initLanguageListeners() {
    getLanguageCheckboxes().forEach(function (el) {
        el.addEventListener('change', updateLanguagesSummary);
    });
    languages.forEach(function (lang) {
        const el = document.getElementById(lang);
        if (el && !el.dataset.bound) {
            el.dataset.bound = '1';
            el.addEventListener('change', updateLanguagesSummary);
        }
    });
    const legacyEl = document.getElementById('multi');
    if (legacyEl && !legacyEl.dataset.bound) {
        legacyEl.dataset.bound = '1';
        legacyEl.addEventListener('change', updateLanguagesSummary);
    }
}

function updateLanguagesSummary() {
    const summaryEl = document.getElementById('languages-summary');
    if (!summaryEl) return;

    const selected = getLanguageCheckboxes()
        .filter(function (el) { return el.checked; })
        .map(function (el) { return normalizeLang(el.value || el.id); });

    if (selected.length === 0) {
        summaryEl.textContent = 'Select Languages...';
    } else if (selected.length <= 3) {
        summaryEl.textContent = selected.join(', ');
    } else {
        summaryEl.textContent = selected.length + ' languages selected';
    }
}

function loadData() {
    const currentUrl = window.location.href;
    let data = currentUrl.match(/\/([^\/]+)\/configure$/);
    if (data && data[1].startsWith("ey")) {
        try {
            let decoded = atob(data[1]);
            decoded = JSON.parse(decoded);

            const preferredDubs = decoded.preferredDubs || decoded.preferred_dubs || [];
            const dubMaxResult = decoded.dubMaxResult ?? decoded.dub_max_results ?? decoded.dubMaxResult ?? 5;
            const otherMaxResult = decoded.otherMaxResult ?? decoded.other_max_results ?? decoded.otherMaxResult ?? 10;

            preferredDubs.forEach(function (lang) {
                lang = normalizeLang(lang);
                const el = document.getElementById(lang)
                    || document.querySelector('#languageCheckBoxes input[value="' + lang + '"]');
                if (el) el.checked = true;
            });
            if (preferredDubs.map(normalizeLang).includes('mul')) {
                const legacyEl = document.getElementById('multi');
                if (legacyEl) legacyEl.checked = true;
            }

            if (decoded.getAllLanguages) {
                languages.forEach(function (lang) {
                    const el = document.getElementById(lang);
                    if (el) el.checked = true;
                });
            }

            const dubEl = document.getElementById('dub-max-result');
            if (dubEl) dubEl.value = String(dubMaxResult);

            const otherEl = document.getElementById('other-max-result');
            if (otherEl) otherEl.value = String(otherMaxResult);

            updateLanguagesSummary();
        } catch (e) {
            console.error('Failed to parse config from URL', e);
        }
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

function getLink(method) {
    const addonHost = new URL(window.location.href).protocol.replace(':', '') + "://" + new URL(window.location.href).host;

    const selectedLanguages = [];
    getLanguageCheckboxes().forEach(function (el) {
        if (el.checked) selectedLanguages.push(normalizeLang(el.value || el.id));
    });

    const preferredDubs = selectedLanguages;

    const dubMaxRaw = document.getElementById('dub-max-result')?.value;
    const otherMaxRaw = document.getElementById('other-max-result')?.value;

    const dubMaxResult = parseInt(dubMaxRaw, 10);
    const otherMaxResult = parseInt(otherMaxRaw, 10);

    if (isNaN(dubMaxResult) || dubMaxResult < 0 || dubMaxResult > 50) {
        alert('Dub Max Results must be a number between 0 and 50');
        return false;
    }
    if (isNaN(otherMaxResult) || otherMaxResult < 0 || otherMaxResult > 50) {
        alert('Other Max Results must be a number between 0 and 50');
        return false;
    }

    if (preferredDubs.length === 0) {
        const confirmEmpty = confirm('No preferred dub language selected. Continue with empty list?');
        if (!confirmEmpty) return false;
    }

    let data = {
        preferredDubs: preferredDubs,
        dubMaxResult: dubMaxResult,
        otherMaxResult: otherMaxResult
    };

    let stremio_link = window.location.host + "/" + btoa(JSON.stringify(data)) + "/manifest.json";

    if (method === 'link') {
        window.open("stremio://" + stremio_link, "_blank");
    } else if (method === 'copy') {
        const link = window.location.protocol + '//' + stremio_link;

        if (!navigator.clipboard) {
            alert('Your browser does not support clipboard');
            console.log(link);
            return;
        }

        navigator.clipboard.writeText(link).then(function () {
            alert('Link copied to clipboard');
        }, function () {
            alert('Error copying link to clipboard');
        });
    }
}
