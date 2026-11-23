// Navigation functionality

const navButtons = document.querySelectorAll(".nav-button");
const pages = document.querySelectorAll(".page-content");

navButtons.forEach(button => {

    button.addEventListener("click", () => {

        const selectedPage = button.dataset.page;

        // Remove active navigation state
        navButtons.forEach(btn => btn.classList.remove("active"));

        // Activate selected navigation button
        button.classList.add("active");

        // Hide all pages
        pages.forEach(page => page.classList.remove("active"));

        // Display selected page
        document.getElementById(selectedPage).classList.add("active");

    });

});


// Hamburger Menu

const menuButton = document.getElementById("menuButton");
const menuDropdown = document.getElementById("menuDropdown");

menuButton.addEventListener("click", () => {

    menuDropdown.classList.toggle("show");

});


// Initial Dashboard Data

const dashboardData = {
    totalPlayers: 0,
    clanLevel: 0,
    clanPower: 0,
    averageLevel: 0
};


// Update Dashboard

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

updateDashboard();