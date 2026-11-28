// Navigation

const navButtons = document.querySelectorAll(".nav-button");
const pages = document.querySelectorAll(".page-content");

navButtons.forEach(button => {
    button.addEventListener("click", () => {

        const selectedPage = button.dataset.page;

        navButtons.forEach(btn => btn.classList.remove("active"));
        button.classList.add("active");

        pages.forEach(page => page.classList.remove("active"));
        document.getElementById(selectedPage).classList.add("active");

    });
});


// Hamburger Menu

const menuButton = document.getElementById("menuButton");
const menuDropdown = document.getElementById("menuDropdown");

menuButton.addEventListener("click", () => {
    menuDropdown.classList.toggle("show");
});


// Dashboard Data




// Update Dashboard

// Update Dashboard using real player data

function updateDashboard() {

    // Count the players
    const totalMembers = players.length;

    // Calculate combined ATK
    const totalATK = players.reduce(
        (total, player) => total + (player.totalAtk || 0),
        0
    );

    // Calculate average ATK
    const avgATK = totalMembers > 0
        ? Math.round(totalATK / totalMembers)
        : 0;

    // Calculate combined Relic Cores
    const totalRelicCores = players.reduce(
        (total, player) => total + (player.relicCore || 0),
        0
    );

    // Update the dashboard cards
    document.getElementById("totalMembers").textContent =
        totalMembers;

    document.getElementById("totalATK").textContent =
        totalATK.toLocaleString();

    document.getElementById("avgATK").textContent =
        avgATK.toLocaleString();

    document.getElementById("totalRelicCores").textContent =
        totalRelicCores.toLocaleString();

}


async function loadStatsPlayers() {
    try {
        const response = await fetch("data/player/current.json");

        if (!response.ok) {
            throw new Error(`Could not load player data: ${response.status}`);
        }

        const decodedPlayers = await response.json();

        players = decodedPlayers.map(player => ({
            name: player.name,
            totalAtk: player.atk,
            relicCore: player.relic_total,
            transmuteCore: player.transmute_total,
            resoChip: player.reso?.reso_chips ?? 0,
            awakeningCore: player.awakening?.awakening_cores_low ?? 0,
            awakeningCoreHigh: player.awakening?.awakening_cores_high ?? 0
        }));

        updateDashboard();
        renderPlayerTable();
    } catch (error) {
        console.error("Error loading Stats players:", error);
    }
}


// Player Table

let currentSort = "totalAtk";
let sortDescending = true;

function renderPlayerTable() {

    const tableBody = document.getElementById("playerTableBody");

    const search = document.getElementById("playerSearch")
        .value.toLowerCase();

    const filteredPlayers = players
        .filter(player => player.name.toLowerCase().includes(search))
        .sort((a, b) => {

            const valueA = a[currentSort];
            const valueB = b[currentSort];

            if (typeof valueA === "string") {
                return sortDescending
                    ? valueB.localeCompare(valueA)
                    : valueA.localeCompare(valueB);
            }

            return sortDescending
                ? valueB - valueA
                : valueA - valueB;

        });

    tableBody.innerHTML = "";

    filteredPlayers.forEach(player => {

        const row = document.createElement("tr");

        row.innerHTML = `
            <td class="player-name">${player.name}</td>
            <td>${player.totalAtk.toLocaleString()}</td>
            <td>${player.relicCore}</td>
            <td>${player.transmuteCore}</td>
            <td>${player.resoChip}</td>
            <td>${player.awakeningCore}–${player.awakeningCoreHigh}</td>
        `;

        tableBody.appendChild(row);

    });

}

//This loads the cx player data from the Json file
async function loadCXPlayers() {

    const tableBody = document.getElementById("cx-table-body");

    try {

        // Retrieve the player data
        const response = await fetch("data/cx/current.json");

        if (!response.ok) {
            throw new Error("Could not load CX player data.");
        }

        // Convert the response into JavaScript data
        const players = await response.json();

        // Clear the loading message
        tableBody.innerHTML = "";

        // Create a row for each player
        players.forEach(player => {

            const row = document.createElement("tr");

            const rankCell = document.createElement("td");
            rankCell.textContent = player.rank;

            const nameCell = document.createElement("td");
            nameCell.textContent = player.name;

            const scoreCell = document.createElement("td");
            scoreCell.textContent = player.cx_score.toLocaleString();

            row.appendChild(rankCell);
            row.appendChild(nameCell);
            row.appendChild(scoreCell);

            tableBody.appendChild(row);

        });

    } catch (error) {

        console.error("CX Leaderboard Error:", error);

        tableBody.innerHTML = `
            <tr>
                <td colspan="3">Unable to load player data.</td>
            </tr>
        `;

    }

}

//This loads the lme player data from the Json file
async function loadLMEPlayers() {

    const tableBody = document.getElementById("lme-table-body");

    try {

        // Load the current leaderboard
        const response = await fetch("data/lme/current.json");

        if (!response.ok) {
            throw new Error("Could not load LME player data.");
        }

        const players = await response.json();

        // Load the last updated timestamp
        const timestampResponse = await fetch("data/lme/last_updated.json");

        if (timestampResponse.ok) {
            const timestampData = await timestampResponse.json();

            const updatedDate = new Date(timestampData.last_updated);

            document.getElementById("lme-last-updated").textContent =
                "Last updated: " +
                updatedDate.toLocaleString([], {
                    dateStyle: "medium",
                    timeStyle: "short"
                });
        }

        // Load the list of weekly snapshots
        let historyFiles = [];

        try {
            const historyResponse = await fetch("data/lme/history/index.json");

            if (historyResponse.ok) {
                historyFiles = await historyResponse.json();
            }
        } catch (error) {
            console.warn("Could not load LME history index:", error);
        }

        // Find the Wednesday date for the current week
        const today = new Date();
        const currentWednesday = new Date(today);
        const daysUntilWednesday = (3 - today.getDay() + 7) % 7;

        currentWednesday.setDate(today.getDate() + daysUntilWednesday);

        const currentWednesdayDate = [
            currentWednesday.getFullYear(),
            String(currentWednesday.getMonth() + 1).padStart(2, "0"),
            String(currentWednesday.getDate()).padStart(2, "0")
        ].join("-");

        // If this week's Wednesday snapshot exists, exclude it from comparison
        if (historyFiles.length > 0 &&
            historyFiles[0].startsWith(currentWednesdayDate)) {
            historyFiles = historyFiles.slice(1);
        }

        // Use only the three most recent previous weekly snapshots
        const previousSnapshotFiles = historyFiles.slice(0, 3);

        // Load the previous weekly leaderboards
        const previousSnapshots = await Promise.all(
            previousSnapshotFiles.map(async fileName => {
                const historyResponse = await fetch(
                    `data/lme/history/${fileName}`
                );

                if (!historyResponse.ok) {
                    throw new Error(`Could not load history file: ${fileName}`);
                }

                return historyResponse.json();
            })
        );

        // Build a map of each player's highest score in previous snapshots
        const previousHighScores = new Map();

        previousSnapshots.forEach(snapshot => {
            snapshot.forEach(player => {
                const existingHigh = previousHighScores.get(player.player_id);

                if (existingHigh === undefined ||
                    player.lme_score > existingHigh) {
                    previousHighScores.set(player.player_id, player.lme_score);
                }
            });
        });

        // Clear the loading message
        tableBody.innerHTML = "";

        // Create a row for each player
        players.forEach(player => {

            const row = document.createElement("tr");

            const rankCell = document.createElement("td");
            rankCell.textContent = player.rank;

            const nameCell = document.createElement("td");
            nameCell.textContent = player.name;

            const scoreCell = document.createElement("td");

            const currentScore = player.lme_score;
            const previousHigh = previousHighScores.get(player.player_id);

            scoreCell.textContent = currentScore.toLocaleString();

            if (previousHigh !== undefined) {

                const growth = currentScore - previousHigh;

                const growthSpan = document.createElement("span");
                growthSpan.textContent = ` (${growth > 0 ? "+" : ""}${growth.toLocaleString()})`;

                if (growth > 0) {
                    growthSpan.className = "growth-positive";
                } else if (growth < 0) {
                    growthSpan.className = "growth-negative";
                } else {
                    growthSpan.className = "growth-neutral";
                }

                scoreCell.appendChild(growthSpan);

            } else {
                scoreCell.appendChild(document.createTextNode(" (—)"));
            }

            row.appendChild(rankCell);
            row.appendChild(nameCell);
            row.appendChild(scoreCell);

            tableBody.appendChild(row);

        });

    } catch (error) {

        console.error("LME Leaderboard Error:", error);

        tableBody.innerHTML = `
            <tr>
                <td colspan="3">Unable to load player data.</td>
            </tr>
        `;

    }

}


// Column Sorting

document.querySelectorAll(".player-table th").forEach(header => {

    header.addEventListener("click", () => {

        const selectedSort = header.dataset.sort;

        if (currentSort === selectedSort) {
            sortDescending = !sortDescending;
        } else {
            currentSort = selectedSort;
            sortDescending = selectedSort !== "name";
        }

        renderPlayerTable();

    });

});


// Search

document.getElementById("playerSearch")
    .addEventListener("input", renderPlayerTable);


// Initialize

loadStatsPlayers();
loadCXPlayers();
loadLMEPlayers();