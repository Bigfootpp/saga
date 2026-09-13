const languages = ['en', 'fr', 'es', 'de', 'it', 'pt', 'pt-BR', 'ja', 'ru', 'hi', 'nl', 'hu', 'pl', 'multi'];

document.addEventListener('DOMContentLoaded', function () {
    initLanguageListeners();
    loadData();
});

function initLanguageListeners() {
    languages.forEach(function (lang) {
        const el = document.getElementById(lang);
        if (el) {
            el.addEventListener('change', updateLanguagesSummary);
        }
    });
}

function updateLanguagesSummary() {
    const summaryEl = document.getElementById('languages-summary');
    if (!summaryEl) return;

    const selected = languages.filter(function (lang) {
        const el = document.getElementById(lang);
        return el && el.checked;
    });

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

            // preferredDubs can be under alias preferredDubs or snake_case preferred_dubs
            const preferredDubs = decoded.preferredDubs || decoded.preferred_dubs || [];
            const dubMaxResult = decoded.dubMaxResult ?? decoded.dub_max_results ?? decoded.dubMaxResult ?? 5;
            const otherMaxResult = decoded.otherMaxResult ?? decoded.other_max_results ?? decoded.otherMaxResult ?? 10;

            // Populate languages
            // If preferredDubs is empty and getAll was implied, keep unchecked
            preferredDubs.forEach(function (lang) {
                const el = document.getElementById(lang);
                if (el) el.checked = true;
            });

            // Handle legacy getAllLanguages flag (no longer selectable in UI)
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
    languages.forEach(function (language) {
        const el = document.getElementById(language);
        if (el && el.checked) selectedLanguages.push(language);
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

    // preferredDubs is required by UserPreferences but we allow empty (means no preference)
    // Warn if empty and user didn't explicitly want empty
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
