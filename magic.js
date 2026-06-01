const https = require("https");
const fs = require("fs");

// ============================================================
// CONFIG: Set your GitHub raw URL for AnimationSniper.json here
// ============================================================
const GITHUB_SOURCES = {
    "AnimationSniper.json":
        "https://raw.githubusercontent.com/PinkWards/emote-sniper/main/AnimationSniper.json"
    // Add more files here if needed, e.g.:
    // "EmoteSniper.json": "https://raw.githubusercontent.com/..."
};

const APIs = [
    {
        name: "Basic API",
        baseUrl:
            "https://catalog.roproxy.com/v1/search/items/details?Category=12&Subcategory=39&Limit=30",
        outputFile: "EmoteSniper.json"
    },
    {
        name: "Latest API",
        baseUrl:
            "https://catalog.roproxy.com/v1/search/items/details?Category=12&Subcategory=39&Limit=30&salesTypeFilter=1&SortType=3",
        outputFile: "EmoteSniper.json"
    },
    {
        name: "Animation API",
        baseUrl:
            "https://catalog.roproxy.com/v1/search/items/details?Category=12&Subcategory=38&salesTypeFilter=1&Limit=30",
        outputFile: "AnimationSniper.json"
    }
];

function log(message) {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] ${message}`);
}

// ============================================================
// VALIDATION: Ensures an item has a valid id and name
// ============================================================
function isValidItem(item) {
    if (!item || typeof item !== "object") return false;
    if (item.id === undefined || item.id === null) return false;
    if (typeof item.id !== "number" || isNaN(item.id)) return false;
    if (!item.name || typeof item.name !== "string" || item.name.trim() === "") return false;
    return true;
}

// ============================================================
// Validate and clean an item — strips invalid fields
// ============================================================
function cleanItem(item) {
    const cleaned = {
        id: item.id,
        name: item.name.trim()
    };

    // Preserve bundledItems if present and valid
    if (item.bundledItems && typeof item.bundledItems === "object" && !Array.isArray(item.bundledItems)) {
        const validBundled = {};
        for (const [key, values] of Object.entries(item.bundledItems)) {
            if (Array.isArray(values) && values.every(v => typeof v === "number")) {
                validBundled[key] = values;
            }
        }
        if (Object.keys(validBundled).length > 0) {
            cleaned.bundledItems = validBundled;
        }
    }

    return cleaned;
}

function loadExistingData(filename) {
    try {
        if (fs.existsSync(filename)) {
            const data = JSON.parse(fs.readFileSync(filename, "utf8"));
            const rawItems = data.data || [];

            // Validate every item — only keep valid ones
            const existingItems = [];
            const existingIds = new Set();

            for (const item of rawItems) {
                if (isValidItem(item)) {
                    const cleaned = cleanItem(item);
                    if (!existingIds.has(cleaned.id)) {
                        existingItems.push(cleaned);
                        existingIds.add(cleaned.id);
                    }
                } else {
                    log(`[VALIDATION] Skipped invalid local item in ${filename}: ${JSON.stringify(item)}`);
                }
            }

            log(`[LOCAL] Loaded ${existingItems.length} valid items from ${filename}`);
            return { items: existingItems, ids: existingIds };
        }
    } catch (error) {
        log(`Error reading ${filename}, starting fresh: ${error.message}`);
    }
    return { items: [], ids: new Set() };
}

// ============================================================
// Fetch baseline data from GitHub — these items are NEVER removed
// ============================================================
async function fetchGitHubData(filename) {
    const url = GITHUB_SOURCES[filename];
    if (!url) {
        log(`[GITHUB] No GitHub source configured for ${filename}, skipping`);
        return { items: [], ids: new Set() };
    }

    try {
        log(`[GITHUB] Fetching ${filename} from GitHub...`);
        const data = await new Promise((resolve, reject) => {
            const timeout = setTimeout(() => reject(new Error("GitHub request timeout")), 30000);

            https.get(url, (res) => {
                clearTimeout(timeout);
                let body = "";

                if (res.statusCode !== 200) {
                    reject(new Error(`GitHub HTTP ${res.statusCode}`));
                    return;
                }

                res.on("data", (chunk) => (body += chunk));
                res.on("end", () => {
                    try {
                        resolve(JSON.parse(body));
                    } catch (e) {
                        reject(new Error("GitHub JSON parse error"));
                    }
                });
            }).on("error", (err) => {
                clearTimeout(timeout);
                reject(err);
            });
        });

        const rawItems = data.data || [];
        const items = [];
        const ids = new Set();

        for (const item of rawItems) {
            if (isValidItem(item)) {
                const cleaned = cleanItem(item);
                if (!ids.has(cleaned.id)) {
                    items.push(cleaned);
                    ids.add(cleaned.id);
                }
            } else {
                log(`[GITHUB VALIDATION] Skipped invalid item in ${filename}: ${JSON.stringify(item)}`);
            }
        }

        log(`[GITHUB] Loaded ${items.length} valid items from GitHub for ${filename}`);
        return { items, ids };
    } catch (error) {
        log(`[GITHUB] Failed to fetch ${filename} from GitHub: ${error.message}`);
        return { items: [], ids: new Set() };
    }
}

async function fetchData(baseUrl, cursor = "", maxRetries = 3) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            const data = await new Promise((resolve, reject) => {
                const url = `${baseUrl}${cursor ? `&Cursor=${cursor}` : ""}`;
                const timeout = setTimeout(() => {
                    reject(new Error("Request timeout"));
                }, 30000);

                https
                    .get(url, (res) => {
                        clearTimeout(timeout);
                        let data = "";

                        if (res.statusCode !== 200) {
                            reject(new Error(`HTTP Error: ${res.statusCode}`));
                            return;
                        }

                        res.on("data", (chunk) => {
                            data += chunk;
                        });

                        res.on("end", () => {
                            try {
                                const jsonData = JSON.parse(data);
                                resolve(jsonData);
                            } catch (error) {
                                reject(new Error("JSON parsing error"));
                            }
                        });
                    })
                    .on("error", (error) => {
                        clearTimeout(timeout);
                        reject(error);
                    });
            });

            return data;
        } catch (error) {
            if (attempt === maxRetries) {
                throw error;
            }
            await new Promise((resolve) => setTimeout(resolve, 2000 * attempt));
        }
    }
}

async function fetchFromAPI(apiInfo, existingData) {
    const apiItems = [];
    let nextPageCursor = null;
    let pageCount = 0;
    let newItemsCount = 0;
    let duplicateCount = 0;

    try {
        do {
            pageCount++;
            log(`${apiInfo.name} - Page ${pageCount}`);

            const response = await fetchData(apiInfo.baseUrl, nextPageCursor);

            if (response.data && Array.isArray(response.data)) {
                response.data.forEach((item) => {
                    if (existingData.ids.has(item.id)) {
                        duplicateCount++;
                    } else {
                        const itemData = {
                            id: item.id,
                            name: item.name
                        };

                        if (item.bundledItems && Array.isArray(item.bundledItems)) {
                            const bundledAssets = {};
                            let animCounter = 1;

                            item.bundledItems.forEach((bundledItem) => {
                                if (bundledItem.type === "UserOutfit") return;

                                const typeKey = animCounter++.toString();

                                if (bundledItem.id) {
                                    if (!bundledAssets[typeKey]) {
                                        bundledAssets[typeKey] = [];
                                    }
                                    bundledAssets[typeKey].push(bundledItem.id);
                                }
                            });

                            if (Object.keys(bundledAssets).length > 0) {
                                itemData.bundledItems = bundledAssets;
                            }
                        }

                        // Validate before adding
                        if (isValidItem(itemData)) {
                            apiItems.push(itemData);
                            existingData.ids.add(item.id);
                            newItemsCount++;
                        } else {
                            log(`[API VALIDATION] Skipped invalid API item: ${JSON.stringify(itemData)}`);
                        }
                    }
                });
            }

            nextPageCursor = response.nextPageCursor;
            await new Promise((resolve) => setTimeout(resolve, 1000));
        } while (nextPageCursor && nextPageCursor.trim() !== "");
    } catch (error) {
        log(`Error in ${apiInfo.name}: ${error.message}`);
    }

    return {
        items: apiItems,
        newItems: newItemsCount,
        duplicates: duplicateCount
    };
}

function saveData(items, filename) {
    const output = {
        keyword: null,
        totalItems: items.length,
        lastUpdate: new Date().toISOString(),
        data: items
    };

    try {
        fs.writeFileSync(filename, JSON.stringify(output, null, 2), "utf8");
        return true;
    } catch (error) {
        log(`Save error for ${filename}: ${error.message}`);
        return false;
    }
}

async function processAPIsByFile() {
    const startTime = Date.now();
    log("Starting combined update...");

    const apisByFile = {};
    APIs.forEach((api) => {
        if (!apisByFile[api.outputFile]) {
            apisByFile[api.outputFile] = [];
        }
        apisByFile[api.outputFile].push(api);
    });

    const results = {};

    for (const [filename, apis] of Object.entries(apisByFile)) {
        log(`Processing ${filename}...`);

        // Step 1: Fetch GitHub baseline data (these items are PERMANENT)
        const githubData = await fetchGitHubData(filename);

        // Step 2: Load local file data
        const localData = loadExistingData(filename);

        // Step 3: Merge — GitHub items take priority, then local items
        const mergedItems = [];
        const mergedIds = new Set();

        // Add GitHub items first (highest priority — never removed)
        for (const item of githubData.items) {
            if (!mergedIds.has(item.id)) {
                mergedItems.push(item);
                mergedIds.add(item.id);
            }
        }

        // Add local items not already in GitHub
        for (const item of localData.items) {
            if (!mergedIds.has(item.id)) {
                mergedItems.push(item);
                mergedIds.add(item.id);
            }
        }

        log(`[MERGE] ${filename}: ${githubData.items.length} from GitHub + ${localData.items.length} from local = ${mergedItems.length} merged`);

        // Step 4: Build existingData for API dedup check
        const existingData = { items: mergedItems, ids: mergedIds };

        // Step 5: Fetch from APIs — only adds NEW items
        let totalNewItems = 0;
        let totalDuplicates = 0;

        for (const api of apis) {
            const result = await fetchFromAPI(api, existingData);
            mergedItems.push(...result.items);
            totalNewItems += result.newItems;
            totalDuplicates += result.duplicates;

            log(`${api.name} - New: ${result.newItems}, Duplicates: ${result.duplicates}`);
        }

        // Step 6: Save — ALL items are preserved (GitHub + local + new API)
        const saveSuccess = saveData(mergedItems, filename);

        results[filename] = {
            success: saveSuccess,
            totalItems: mergedItems.length,
            githubItems: githubData.items.length,
            localItems: localData.items.length,
            newItems: totalNewItems,
            duplicates: totalDuplicates
        };

        log(
            `${filename} - Total: ${mergedItems.length} (GitHub: ${githubData.items.length}, Local: ${localData.items.length}, New API: ${totalNewItems})`
        );
    }

    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
    log(`All updates complete - Duration: ${duration}s`);

    return { results, duration };
}

async function main() {
    log("Starting Enhanced EmoteSniper with Animation support...");

    try {
        const { results, duration } = await processAPIsByFile();

        let allSuccess = true;
        for (const [filename, result] of Object.entries(results)) {
            if (!result.success) {
                allSuccess = false;
                log(`Failed to save ${filename}`);
            } else {
                log(
                    `✓ ${filename}: ${result.totalItems} items (GitHub: ${result.githubItems}, Local: ${result.localItems}, New: ${result.newItems})`
                );
            }
        }

        if (allSuccess) {
            log("Enhanced EmoteSniper completed successfully");
            process.exit(0);
        } else {
            log("Enhanced EmoteSniper completed with some errors");
            process.exit(1);
        }
    } catch (error) {
        log(`Enhanced EmoteSniper error: ${error.message}`);
        process.exit(1);
    }
}

process.on("unhandledRejection", (reason) => {
    log(`Unhandled error: ${reason}`);
    process.exit(1);
});

process.on("uncaughtException", (error) => {
    log(`Uncaught exception: ${error.message}`);
    process.exit(1);
});

main();
