(function () {
    "use strict";

    const dataElement = document.getElementById("dashboard-data");
    if (!dataElement || typeof Chart === "undefined") {
        return;
    }

    const data = JSON.parse(dataElement.textContent);

    const colors = {
        green: "#198754",
        red: "#dc3545",
        orange: "#fd7e14",
        grey: "#adb5bd",
        blue: "#0d6efd",
        dark: "#212529",
    };

    Chart.defaults.maintainAspectRatio = false;
    Chart.defaults.plugins.legend.position = "bottom";

    new Chart(document.getElementById("chart-mfa"), {
        type: "doughnut",
        data: {
            labels: data.mfa.labels,
            datasets: [{
                data: data.mfa.values,
                backgroundColor: [colors.green, colors.grey],
            }],
        },
    });

    new Chart(document.getElementById("chart-auth"), {
        type: "bar",
        data: {
            labels: data.auth.labels,
            datasets: [{
                label: "Numri",
                data: data.auth.values,
                backgroundColor: [colors.green, colors.red, colors.orange, colors.dark],
            }],
        },
        options: {
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
        },
    });

    new Chart(document.getElementById("chart-per-day"), {
        type: "line",
        data: {
            labels: data.per_day.labels,
            datasets: [
                {
                    label: "Të suksesshme",
                    data: data.per_day.success,
                    borderColor: colors.green,
                    backgroundColor: colors.green,
                    tension: 0.25,
                },
                {
                    label: "Të dështuara",
                    data: data.per_day.failed,
                    borderColor: colors.red,
                    backgroundColor: colors.red,
                    tension: 0.25,
                },
            ],
        },
        options: {
            scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
        },
    });

    new Chart(document.getElementById("chart-by-type"), {
        type: "bar",
        data: {
            labels: data.by_type.labels,
            datasets: [{
                label: "Evente",
                data: data.by_type.values,
                backgroundColor: colors.blue,
            }],
        },
        options: {
            indexAxis: "y",
            plugins: { legend: { display: false } },
            scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
        },
    });
})();