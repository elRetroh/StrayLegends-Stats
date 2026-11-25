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

const dashboardData = {
    totalMembers: 4,
    totalATK: 880000,
    avgATK: 220000,
    totalRelicCores: 39
};


// Update Dashboard

function updateDashboard() {

    document.getElementById("totalMembers").textContent =
        dashboardData.totalMembers;

    document.getElementById("totalATK").textContent =
        dashboardData.totalATK.toLocaleString();

    document.getElementById("avgATK").textContent =
        dashboardData.avgATK.toLocaleString();

    document.getElementById("totalRelicCores").textContent =
        dashboardData.totalRelicCores;

}


// Sample Player Data

const players = [

    {
        name: "Player 1",
        totalAtk: 250000,
        relicCore: 12,
        transmuteCore: 8,
        relicChip: 15,
        awakeningCore: 6
    },

    {
        name: "Player 2",
        totalAtk: 225000,
        relicCore: 10,
        transmuteCore: 7,
        relicChip: 12,
        awakeningCore: 5
    },

    {
        name: "Player 3",
        totalAtk: 210000,
        relicCore: 9,
        transmuteCore: 6,
        relicChip: 11,
        awakeningCore: 4
    },

    {
        name: "Player 4",
        totalAtk: 195000,
        relicCore: 8,
        transmuteCore: 5,
        relicChip: 9,
        awakeningCore: 3
    }

];


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
            <td>${player.relicChip}</td>
            <td>${player.awakeningCore}</td>
        `;

        tableBody.appendChild(row);

    });

}

//This loads the cx player data from the Json file
async function loadCXPlayers() {

    const tableBody = document.getElementById("cxPlayerTableBody");

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

        // Retrieve the player data
        const response = await fetch("data/lme/current.json");

        if (!response.ok) {
            throw new Error("Could not load LME player data.");
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
            scoreCell.textContent = player.lme_score.toLocaleString();

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

updateDashboard();
renderPlayerTable();
loadCXPlayers();
loadLMEPlayers();