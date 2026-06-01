const https = require("https");
const fs = require("fs");

// ============================================================
// CONFIG: Set your GitHub raw URL for AnimationSniper.json here
// ============================================================
const GITHUB_SOURCES = {
    "AnimationSniper.json":
        "https://raw.githubusercontent.com/PinkWards/emote-sniper/main/AnimationSniper.json"
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

// ============================================================
// Known animation type names for extraction from bundled items
// ============================================================
const ANIM_TYPES = ["Climb", "Fall", "Walk", "Swim", "SwimIdle", "Idle", "Run", "Jump"];

function log(message) {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] ${message}`);
}

// ============================================================
// Extract animation type from a name string
// ============================================================
function extractAnimType(name) {
    if (!name || typeof name !== "string") return null;
    const lower = name.toLowerCase();
    for (const t of ANIM_TYPES) {
        if (lower.includes(t.toLowerCase())) {
            return t;
        }
    }
    return null;
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
// Validate a single animation entry {id, name}
// ============================================================
function isValidAnimEntry(entry) {
    if (!entry || typeof entry !== "object") return false;
    if (entry.id === undefined || entry.id === null) return false;
    if (typeof entry.id !== "number" || isNaN(entry.id)) return false;
    if (!entry.name || typeof entry.name !== "string" || entry.name.trim() === "") return false;
    return true;
}

// ============================================================
// Validate and clean bundledAnimations
// ============================================================
function cleanBundledAnimations(bundledAnimations) {
    if (!bundledAnimations || typeof bundledAnimations !== "object" || Array.isArray(bundledAnimations)) {
        return null;
    }

    const cleaned = {};
    let hasValid = false;

    for (const [typeKey, entries] of Object.entries(bundledAnimations)) {
        if (!Array.isArray(entries)) continue;

        const validEntries = entries
            .filter(e => isValidAnimEntry(e))
            .map(e => ({
                id: e.id,
                name: e.name.trim()
            }));

        if (validEntries.length > 0) {
            cleaned[typeKey] = validEntries;
            hasValid = true;
        }
    }

    return hasValid ? cleaned : null;
}

// ============================================================
// Validate and clean an entire item
// ============================================================
function cleanItem(item) {
    const cleaned = {
        id: item.id,
        name: item.name.trim()
    };

    const anims = cleanBundledAnimations(item.bundledAnimations);
    if (anims) {
        cleaned.bundledAnimations = anims;
    }

    return cleaned;
}

function loadExistingData(filename) {
    try {
        if (fs.existsSync(filename)) {
            const data = JSON.parse(fs.readFileSync(filename, "utf8"));
            const rawItems = data.data || [];

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

// ============================================================
// Convert API bundledItems to bundledAnimations format
// ============================================================
function convertBundledItemsToAnimations(bundledItems, parentName) {
    if (!bundledItems || !Array.isArray(bundledItems)) return null;

    const animations = {};

    for (const bundledItem of bundledItems) {
        if (bundledItem.type === "UserOutfit") continue;
        if (!bundledItem.id) continue;

        const animName = bundledItem.name || parentName || "";
        const animType = extractAnimType(animName);

        if (animType) {
            if (!animations[animType]) {
                animations[animType] = [];
            }
            animations[animType].push({
                id: bundledItem.id,
                name: animName.trim()
            });
        } else {
            const genericKey = `Animation_${Object.keys(animations).length + 1}`;
            if (!animations[genericKey]) {
                animations[genericKey] = [];
            }
            animations[genericKey].push({
                id: bundledItem.id,
                name: animName.trim()
            });
        }
    }

    return Object.keys(animations).length > 0 ? animations : null;
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
                            const animations = convertBundledItemsToAnimations(
                                item.bundledItems,
                                item.name
                            );
                            if (animations) {
                                itemData.bundledAnimations = animations;
                            }
                        }

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

        const githubData = await fetchGitHubData(filename);
        const localData = loadExistingData(filename);

        const mergedItems = [];
        const mergedIds = new Set();

        for (const item of githubData.items) {
            if (!mergedIds.has(item.id)) {
                mergedItems.push(item);
                mergedIds.add(item.id);
            }
        }

        for (const item of localData.items) {
            if (!mergedIds.has(item.id)) {
                mergedItems.push(item);
                mergedIds.add(item.id);
            }
        }

        log(`[MERGE] ${filename}: ${githubData.items.length} from GitHub + ${localData.items.length} from local = ${mergedItems.length} merged`);

        const existingData = { items: mergedItems, ids: mergedIds };

        let totalNewItems = 0;
        let totalDuplicates = 0;

        for (const api of apis) {
            const result = await fetchFromAPI(api, existingData);
            mergedItems.push(...result.items);
            totalNewItems += result.newItems;
            totalDuplicates += result.duplicates;

            log(`${api.name} - New: ${result.newItems}, Duplicates: ${result.duplicates}`);
        }

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
