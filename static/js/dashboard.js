"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const source = document.getElementById("dashboard-data");
  if (!source || typeof Chart === "undefined") return;
  const data = JSON.parse(source.textContent);
  const colors = ["#9682cd", "#87bca8", "#a3bce0", "#e0be88", "#c69cb9", "#b6abd3"];
  Chart.defaults.font.family = '"Segoe UI", Arial, sans-serif';
  Chart.defaults.font.size = 10;
  Chart.defaults.color = "#aaadbc";
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) Chart.defaults.animation = false;
  const options = {responsive: true, maintainAspectRatio: false, plugins: {legend: {display: false}, tooltip: {backgroundColor: "#504469", padding: 12, cornerRadius: 8}}, scales: {x: {grid: {display: false}, border: {display: false}, ticks: {maxRotation: 0}}, y: {beginAtZero: true, grid: {color: "#f0f1f6"}, border: {display: false}}}};
  const line = document.getElementById("attendance-trend");
  const gradient = line.getContext("2d").createLinearGradient(0, 0, 0, 230);
  gradient.addColorStop(0, "#bba8e238"); gradient.addColorStop(1, "#bba8e203");
  new Chart(line, {type: "line", data: {labels: data.trend.map(item => item.label), datasets: [{label: "Attendance %", data: data.trend.map(item => item.rate), borderColor: colors[0], backgroundColor: gradient, fill: true, tension: .36, borderWidth: 2, pointRadius: 3, pointBackgroundColor: "white", pointBorderWidth: 2, pointHoverRadius: 5}]}, options: {...options, scales: {...options.scales, y: {...options.scales.y, max: 100, ticks: {stepSize: 25, callback: value => `${value}%`}}}}});
  new Chart(document.getElementById("department-chart"), {type: "doughnut", data: {labels: data.departments.map(item => item.code), datasets: [{data: data.departments.map(item => item.total), backgroundColor: colors, borderWidth: 5, borderColor: "white", borderRadius: 3, hoverOffset: 3}]}, options: {responsive: true, maintainAspectRatio: false, cutout: "77%", plugins: {legend: {display: false}}}});
  const legend = document.getElementById("department-legend");
  data.departments.forEach((item, index) => {
    const row = document.createElement("div"); row.className = "legend-item";
    const dot = document.createElement("span"); dot.style.backgroundColor = colors[index % colors.length];
    const label = document.createTextNode(item.code);
    const count = document.createElement("b"); count.textContent = item.total;
    row.append(dot, label, count); legend.append(row);
  });
  new Chart(document.getElementById("grade-chart"), {type: "bar", data: {labels: Object.keys(data.grades), datasets: [{label: "Assessments", data: Object.values(data.grades), backgroundColor: ["#87bca8", "#9ccdb8", "#a3bce0", "#b6abd3", "#e0be88", "#d9a5b0"], borderRadius: 5, maxBarThickness: 25}]}, options: {...options, scales: {...options.scales, y: {...options.scales.y, ticks: {precision: 0}}}}});
  new Chart(document.getElementById("enrollment-chart"), {type: "bar", data: {labels: data.courses.map(item => item.code), datasets: [{label: "Enrollments", data: data.courses.map(item => item.total), backgroundColor: "#b5a5d9", borderRadius: 5, maxBarThickness: 23}]}, options: {...options, indexAxis: "y", scales: {x: {beginAtZero: true, grid: {color: "#f0f1f6"}, border: {display: false}, ticks: {precision: 0}}, y: {grid: {display: false}, border: {display: false}}}}});
});
