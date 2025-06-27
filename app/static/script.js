document.addEventListener("DOMContentLoaded", function () {
  let currentFilter = "all";
  let currentSearch = "";
  let currentMonth = "";
  let currentYear = "";

  // Fault Row Click - Open Drawer
  document.addEventListener("click", function (e) {
    const row = e.target.closest(".fault-row");
    if (
      row &&
      !e.target.classList.contains("status-select") &&
      !e.target.closest(".action-btn")
    ) {
      openDrawerWithDetails(row.dataset.faultId);
    }
  });

  // Status Dropdown Change (AJAX Update)
  document.addEventListener("change", function (e) {
    if (e.target && e.target.classList.contains("status-select")) {
      const faultId = e.target.dataset.faultId;
      const newStatus = e.target.value;
      fetch(`/update_fault_status/${faultId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      })
        .then((res) => res.json())
        .then((data) => {
          showToast(data.message);
          loadTable();
        });
    }
  });

  // Filter Tabs (All, Open, Resolved)
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document
        .querySelectorAll(".tab")
        .forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      currentFilter = tab.dataset.filter;
      loadTable();
    });
  });

  // Search Button Click
  document.getElementById("searchBtn").addEventListener("click", () => {
    currentSearch = document.getElementById("searchInput").value.trim();
    loadTable();
  });

  // Month Filter Change
  document.getElementById("monthFilter").addEventListener("change", (e) => {
    currentMonth = e.target.value;
    loadTable();
  });

  // Year Filter Change
  document.getElementById("yearFilter").addEventListener("change", (e) => {
    currentYear = e.target.value;
    loadTable();
  });

  // Drawer Close
  document.getElementById("closeDrawer").addEventListener("click", () => {
    document.getElementById("drawer").classList.remove("open");
  });

  // Drawer Tabs Switching
  document.querySelectorAll(".drawer-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document
        .querySelectorAll(".drawer-tab")
        .forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      document
        .querySelectorAll(".tab-content")
        .forEach((content) => content.classList.remove("active"));
      document.getElementById(tab.dataset.tab + "Tab").classList.add("active");
    });
  });

  // Charts
  initCharts();

  // Auto Table Refresh every 3 minutes
  setInterval(() => loadTable(), 180000);

  // Initial Table Load
  loadTable();
});

// Load Table function with full filters
function loadTable() {
  const params = new URLSearchParams({
    filter: getActiveFilter(),
    search: document.getElementById("searchInput").value.trim(),
    month: document.getElementById("monthFilter").value,
    year: document.getElementById("yearFilter").value,
  });

  fetch(`/update_dashboard_table?${params.toString()}`)
    .then((res) => res.json())
    .then((data) => {
      document.querySelector("#faultsTable tbody").innerHTML = data.table;
    })
    .catch((err) => console.error("Error loading table:", err));
}

function getActiveFilter() {
  const activeTab = document.querySelector(".tab.active");
  return activeTab ? activeTab.dataset.filter : "all";
}

function openDrawerWithDetails(faultId) {
  fetch(`/get_fault_details/${faultId}`)
    .then((res) => {
      if (!res.ok) throw new Error("No customer details found");
      return res.json();
    })
    .then((data) => {
      const customer = data.customer;
      document.getElementById("customerCompany").textContent = customer.company;
      document.getElementById("customerIP").textContent = customer.ip_address;
      document.getElementById("customerPOP").textContent = customer.pop_site;
      document.getElementById("customerCircuit").textContent =
        customer.circuit_id;
      document.getElementById("customerEmail").textContent =
        customer.email || "N/A";
      document.getElementById("customerSwitch").textContent =
        customer.switch_info || "N/A";

      const historyBody = document.getElementById("faultHistoryBody");
      historyBody.innerHTML =
        data.history.length === 0
          ? `<tr><td colspan="4">No fault history found.</td></tr>`
          : data.history
              .map(
                (h) => `
            <tr>
              <td>${h.id}</td>
              <td>${h.issue}</td>
              <td>${h.status}</td>
              <td>${h.logged_time}</td>
            </tr>
          `
              )
              .join("");

      document.getElementById("drawer").classList.add("open");
    })
    .catch((err) => alert(err.message));
}

function showToast(message) {
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.innerText = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

function initCharts() {
  new Chart(document.getElementById("deptChart"), {
    type: "bar",
    data: {
      labels: window.chartData.deptLabels,
      datasets: [
        {
          label: "Faults by Department",
          data: window.chartData.deptValues,
          backgroundColor: "steelblue",
        },
      ],
    },
  });

  new Chart(document.getElementById("dateChart"), {
    type: "line",
    data: {
      labels: window.chartData.dateLabels,
      datasets: [
        {
          label: "Faults Over Time",
          data: window.chartData.dateValues,
          backgroundColor: "lightgreen",
          borderColor: "green",
          fill: false,
        },
      ],
    },
  });

  new Chart(document.getElementById("severityChart"), {
    type: "pie",
    data: {
      labels: window.chartData.severityLabels,
      datasets: [
        {
          label: "Fault Severity",
          data: window.chartData.severityValues,
          backgroundColor: ["orange", "gold", "red"],
        },
      ],
    },
  });
}

// Handle Delete Button
document.addEventListener("click", function (e) {
  if (e.target.classList.contains("delete")) {
    const faultId = e.target.dataset.faultId;
    if (confirm("Are you sure you want to delete this fault?")) {
      fetch(`/delete_fault/${faultId}`, { method: "POST" })
        .then((res) => res.json())
        .then((data) => {
          showToast(data.message);
          loadTable();
        })
        .catch(() => alert("Error deleting fault."));
    }
  }
});

// Open Edit Modal
document.addEventListener("click", function (e) {
  if (e.target.classList.contains("edit")) {
    const faultId = e.target.dataset.faultId;
    fetch(`/get_fault_details/${faultId}`)
      .then((res) => res.json())
      .then((data) => {
        document.getElementById("editFaultId").value = faultId;
        document.getElementById("editType").value = data.type || "";
        document.getElementById("editDescription").value =
          data.description || "";
        document.getElementById("editLocation").value = data.location || "";
        document.getElementById("editModal").classList.add("open");
      })
      .catch(() => alert("Error loading fault details"));
  }
});

document.getElementById("closeEditModal").addEventListener("click", () => {
  document.getElementById("editModal").classList.remove("open");
});

document
  .getElementById("editFaultForm")
  .addEventListener("submit", function (e) {
    e.preventDefault();
    const faultId = document.getElementById("editFaultId").value;
    const updatedData = {
      type: document.getElementById("editType").value,
      description: document.getElementById("editDescription").value,
      location: document.getElementById("editLocation").value,
    };

    fetch(`/edit_fault/${faultId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updatedData),
    })
      .then((res) => res.json())
      .then((data) => {
        showToast(data.message);
        document.getElementById("editModal").classList.remove("open");
        loadTable();
      })
      .catch(() => alert("Error updating fault"));
  });
