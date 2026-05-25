function scrapeCodeforcesData(root) {
    try {
        const sourceCode = root.querySelector('#program-source-text')?.innerText || "";
        const tableRow = root.querySelector('.datatable tr:nth-child(2)');
        if (!tableRow) return null;

        const cells = tableRow.querySelectorAll('td');
        const submissionId = cells[0]?.innerText.trim();
        const username = cells[1]?.querySelector('.rated-user')?.innerText.trim();
        const rawLang = cells[3]?.innerText.trim().toLowerCase();
        let lang = "other";
        if (rawLang.includes("c++") || rawLang.includes("g++")) lang = "cpp";
        else if (rawLang.includes("python") || rawLang.includes("pypy")) lang = "python";
        else if (rawLang.includes("java")) lang = "java";

        const verdictText = cells[4]?.innerText.trim();
        let points = 0;
        if (verdictText.includes("Полное решение") || verdictText.includes("Accepted")) {
            points = 100;
        } else if (verdictText.includes("балл") || verdictText.includes("points")) {
            const match = verdictText.match(/\d+/);
            points = match ? parseInt(match[0]) : 0;
        } else {
            points = 0;
        }

        return {
            submissionId,
            username,
            lang,
            points,
            sourceCode,
            timestamp: new Date().toISOString()
        };
    } catch (err) {
        return null;
    }
}

function scrapeCodeforcesProblem(root) {
    try {
        const problemHolder = root.querySelector('.problemindexholder');
        if (!problemHolder) return null;

        const header = problemHolder.querySelector('.header');
        const title = header?.querySelector('.title')?.innerText.trim() || "";

        function getProperty(selector) {
            const el = header?.querySelector(selector);
            if (!el) return "";
            const propertyTitle = el.querySelector('.property-title');
            if (propertyTitle) {
                return el.innerText.replace(propertyTitle.innerText, '').trim();
            }
            return el.innerText.trim();
        }

        const timeLimit = getProperty('.time-limit');
        const memoryLimit = getProperty('.memory-limit');

        function cleanSection(selector) {
            const el = problemHolder.querySelector(selector);
            if (!el) return "";
            const clone = el.cloneNode(true);
            clone.querySelector('.section-title')?.remove();
            return clone.innerText.trim();
        }

        const inputFormat = cleanSection('.input-specification');
        const outputFormat = cleanSection('.output-specification');

        const problemStatement = problemHolder.querySelector('.problem-statement');
        let description = "";
        if (problemStatement) {
            const tempDiv = problemStatement.cloneNode(true);
            tempDiv.querySelector('.header')?.remove();
            tempDiv.querySelector('.input-specification')?.remove();
            tempDiv.querySelector('.output-specification')?.remove();
            tempDiv.querySelector('.sample-tests')?.remove();
            tempDiv.querySelector('.note')?.remove();

            description = tempDiv.innerText.trim();
        }

        return {
            name: title,
            timeLimit: timeLimit,
            memoryLimit: memoryLimit,
            inputFormat: inputFormat,
            outputFormat: outputFormat,
            description: description,
            timestamp: new Date().toISOString()
        };
    } catch (err) {
        return null;
    }
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "scrapeCodeforces") {
        fetch(window.location.href)
            .then(response => response.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const data = scrapeCodeforcesData(doc);
                sendResponse(data);
            })
            .catch(err => {
                console.error("Fetch failed:", err);
                sendResponse(null);
            });
        return true;
    }

    if (request.action === "scrapeProblem") {
        fetch(window.location.href)
            .then(response => response.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const data = scrapeCodeforcesProblem(doc);
                sendResponse(data);
            })
            .catch(err => {
                console.error("Fetch failed:", err);
                sendResponse(null);
            });
        return true;
    }
});