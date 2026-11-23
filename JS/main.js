// Initial dashboard data
const dashboardData = {
    totalPlayers: 0,
    clanLevel: 0,
    clanPower: 0,
    averageLevel: 0
};

// Update dashboard statistics
function updateDashboard() {

    document.getElementById("totalPlayers").textContent =
        dashboardData.totalPlayers;

    document.getElementById("clanLevel").textContent =
        dashboardData.clanLevel;

    document.getElementById("clanPower").textContent =
        dashboardData.clanPower;

    document.getElementById("averageLevel").textContent =
        dashboardData.averageLevel;

}

// Initialize dashboard
updateDashboard();