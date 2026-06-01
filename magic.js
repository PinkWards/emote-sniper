const https = require("https");
const fs = require("fs");

// Animation asset types that appear inside character bundles
const ANIMATION_ASSET_TYPES = {
    48: "Climb",
    50: "Fall",
    51: "Idle",
    52: "Jump",
    53: "Run",
    54: "Swim",
    55: "Walk",
    61: "Emote",
    78: "Mood"
};

const isAnimationAssetType = (assetType) =>
    ANIMATION_ASSET_TYPES.hasOwnProperty(assetType);

const APIs = [
    {
        name: "Basic API",
        baseUrl:
            "https://catalog.roproxy.com/v1/search/items/details?Category=12&Subcategory=39&Limit=30",
        outputFile: "EmoteSniper.json",
        mode: "default"
    },
    {
        name: "Latest API",
        baseUrl:
            "https://catalog.roproxy.com/v1/search/items/details?Category=12&Subcategory=39&Limit=30&salesTypeFilter=1&SortType=3",
        outputFile: "EmoteSniper.json",
        mode: "default"
    },
    {
        name: "Animation API",
        baseUrl:
            "https://catalog.roproxy.com/v1/search/items/details?Category=12&Subcategory=38&salesTypeFilter=1&Limit=30",
        outputFile: "AnimationSniper.json",
        mode: "default"
    },
    {
        name: "Character Bundle Animation API",
        baseUrl:
            "https://catalog.roproxy.com/v1/search/items/details?Category=1&CreatorName=Roblox&Limit=30",
        outputFile: "AnimationSniper.json",
        mode: "bundleAnimations"
    }
];

function log(message) {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] ${message}`);
}

function loadExistingData(filename) {
    try {
        if (fs.existsSync(filename)) {
            const fileData = JSON.parse(fs.readFileSync(filename, "utf8"));
            const existingItems = fileData.data || [];
            const existingIds = new Set(
                existingItems.map((item) => item.id)
            );
            return { items: existingItems, ids: existingIds };
        }
    } catch (error) {
        log(`Error reading ${filename}, starting fresh`);
    }
    return { items: [], ids: new Set() };
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
                        let rawData = "";

                        if (res.statusCode !== 200) {
                            reject(new Error(`HTTP Error: ${res.statusCode}`));
                            return;
                        }

                        res.on("data", (chunk) => {
                            rawData += chunk;
                        });

                        res.on("end", () => {
                            try {
                                const jsonData = JSON.parse(rawData);
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
            await new Promise((resolve) =>
                setTimeout(resolve, 2000 * attempt)
            );
        }
    }
}

function extractBundleAnimations(item, existingData, apiItems) {
    let newItems = 0;
    let duplicates = 0;

    if (
        item.itemType !== "Bundle" ||
        !item.bundledItems ||
        !Array.isArray(item.bundledItems)
    ) {
        return { newItems, duplicates };
    }

    const bundleAnims = item.bundledItems.filter(
        (bi) => bi.type === "Asset" && isAnimationAssetType(bi.assetType)
    );

    bundleAnims.forEach((anim) => {
        if (existingData.ids.has(anim.id)) {
            duplicates++;
            return;
        }

        apiItems.push({
            id: anim.id,
            name: anim.name,
            animationType: ANIMATION_ASSET_TYPES[anim.assetType],
            assetType: anim.assetType,
            bundleId: item.id,
            bundleName: item.name,
            source: "bundle"
        });

        existingData.ids.add(anim.id);
        newItems++;
    });

    return { newItems, duplicates };
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
                for (const item of response.data) {
                    if (apiInfo.mode === "bundleAnimations") {
                        const result = extractBundleAnimations(
                            item,
                            existingData,
                            apiItems
                        );
                        newItemsCount += result.newItems;
                        duplicateCount += result.duplicates;
                    } else {
                        if (existingData.ids.has(item.id)) {
                            duplicateCount++;
                            continue;
                        }

                        const itemData = {
                            id: item.id,
                            name: item.name
                        };

                        // Capture any bundled animations for regular items too
                        if (
                            item.bundledItems &&
                            Array.isArray(item.bundledItems)
                        ) {
                            const bundledAnims = {};
                            item.bundledItems.forEach((bundledItem) => {
                                if (
                                    bundledItem.type === "Asset" &&
                                    isAnimationAssetType(bundledItem.assetType)
                                ) {
                                    const typeName =
                                        ANIMATION_ASSET_TYPES[bundledItem.assetType];
                                    if (!bundledAnims[typeName]) {
                                        bundledAnims[typeName] = [];
                                    }
                                    bundledAnims[typeName].push({
                                        id: bundledItem.id,
                                        name: bundledItem.name
                                    });
                                }
                            });

                            if (Object.keys(bundledAnims).length > 0) {
                                itemData.bundledAnimations = bundledAnims;
                            }
                        }

                        apiItems.push(itemData);
                        existingData.ids.add(item.id);
                        newItemsCount++;
                    }
                }
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

        const existingData = loadExistingData(filename);
        const allItems = [...existingData.items];
        let totalNewItems = 0;
        let totalDuplicates = 0;

        for (const api of apis) {
            const result = await fetchFromAPI(api, existingData);
            allItems.push(...result.items);
            totalNewItems += result.newItems;
            totalDuplicates += result.duplicates;
            log(
                `${api.name} - New: ${result.newItems}, Duplicates: ${result.duplicates}`
            );
        }

        const saveSuccess = saveData(allItems, filename);
        results[filename] = {
            success: saveSuccess,
            totalItems: allItems.length,
            newItems: totalNewItems,
            duplicates: totalDuplicates
        };

        log(
            `${filename} - Total: ${allItems.length}, New: ${totalNewItems}`
        );
    }

    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
    log(`All updates complete - Duration: ${duration}s`);

    return { results, duration };
}

async function main() {
    log("Starting Enhanced EmoteSniper with Bundle Animation support...");

    try {
        const { results, duration } = await processAPIsByFile();
        let allSuccess = true;

        for (const [filename, result] of Object.entries(results)) {
            if (!result.success) {
                allSuccess = false;
                log(`Failed to save ${filename}`);
            } else {
                log(
                    `✓ ${filename}: ${result.totalItems} items (${result.newItems} new)`
                );
            }
        }

        if (allSuccess) {
            log("Enhanced sniper completed successfully");
            process.exit(0);
        } else {
            log("Enhanced sniper completed with some errors");
            process.exit(1);
        }
    } catch (error) {
        log(`Enhanced sniper error: ${error.message}`);
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
