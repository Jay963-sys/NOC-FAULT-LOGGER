document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  initCharts();
  setInterval(loadTable, 180000); // Refresh every 3 minutes
  loadTable();
});

function setupEventListeners() {
  document.addEventListener("click", handleClicks);
  document.addEventListener("change", handleChange);

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document
        .querySelectorAll(".tab")
        .forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      clearSeverityFilter();
      clearDepartmentFilter();
      loadTable();
    });
  });

  const searchInput = document.getElementById("searchInput");
  searchInput.addEventListener("input", loadTable);
  searchInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      loadTable();
    }
  });

  document.getElementById("searchBtn").addEventListener("click", loadTable);
  document.getElementById("monthFilter").addEventListener("change", loadTable);
  document.getElementById("yearFilter").addEventListener("change", loadTable);

  document.getElementById("viewStatsBtn").addEventListener("click", () => {
    document.getElementById("statsDrawer").classList.add("open");
  });
  document.getElementById("closeStatsDrawer").addEventListener("click", () => {
    document.getElementById("statsDrawer").classList.remove("open");
  });
  document
    .getElementById("closeDetailsDrawer")
    .addEventListener("click", () => {
      document.getElementById("detailsDrawer").classList.remove("open");
    });
  document.getElementById("closeEditModal").addEventListener("click", () => {
    document.getElementById("editModal").classList.remove("open");
  });

  document
    .getElementById("editFaultForm")
    .addEventListener("submit", handleEditSubmit);

  document.querySelectorAll(".filter-card").forEach((card) => {
    card.addEventListener("click", () => {
      const status = card.dataset.status;
      const severity = card.dataset.severity;

      if (status) {
        document.querySelectorAll(".tab").forEach((t) => {
          t.classList.toggle("active", t.dataset.filter === status);
        });
        clearSeverityFilter();
        clearDepartmentFilter();
        loadTable();
      }

      if (severity) {
        clearDepartmentFilter();
        setSeverityFilter(severity);
        document
          .querySelectorAll(".tab")
          .forEach((t) => t.classList.remove("active"));
        document
          .querySelector(".tab[data-filter='all']")
          .classList.add("active");
        loadTable();
      }

      document.getElementById("statsDrawer").classList.remove("open");
    });
  });

  document.querySelectorAll(".dept-filter").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      clearSeverityFilter();
      setDepartmentFilter(btn.dataset.department);
      document
        .querySelectorAll(".tab")
        .forEach((t) => t.classList.remove("active"));
      document.querySelector(".tab[data-filter='all']").classList.add("active");
      loadTable();
      document.getElementById("statsDrawer").classList.remove("open");
    });
  });
}

function handleClicks(e) {
  const row = e.target.closest(".fault-row");

  if (
    row &&
    !e.target.classList.contains("status-select") &&
    !e.target.closest(".action-btn")
  ) {
    openDetailsDrawer(row.dataset.faultId);
  }

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
        document.getElementById("editOwner").value = data.owner_of_ticket || "";
        document.getElementById("editAssignedTo").value =
          data.assigned_to_person || "";
        document.getElementById("editModal").classList.add("open");
      })
      .catch(() => alert("Error loading fault details"));
  }
}

function handleChange(e) {
  if (e.target.classList.contains("status-select")) {
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
      })
      .catch(() => alert("Error updating status"));
  }
}

function handleEditSubmit(e) {
  e.preventDefault();

  const faultId = document.getElementById("editFaultId").value;
  const updatedData = {
    type: document.getElementById("editType").value,
    description: document.getElementById("editDescription").value,
    location: document.getElementById("editLocation").value,
    owner_of_ticket: document.getElementById("editOwner").value,
    assigned_to_person: document.getElementById("editAssignedTo").value,
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
}

function loadTable() {
  showLoader();

  const params = new URLSearchParams({
    filter: getActiveFilter(),
    search: document.getElementById("searchInput").value.trim(),
    month: document.getElementById("monthFilter").value,
    year: document.getElementById("yearFilter").value,
    severity: getSeverityFilter(),
    department: getDepartmentFilter(),
  });

  fetch(`/update_dashboard_table?${params.toString()}`)
    .then((res) => res.json())
    .then((data) => {
      injectTableHeader();
      document.querySelector("#faultsTable tbody").innerHTML = data.table;

      const countEl = document.querySelector(
        ".filter-card[data-severity='High'] p"
      );
      if (countEl && data.high_severity_count !== undefined) {
        countEl.textContent = data.high_severity_count;
      }
    })
    .catch(() => alert("Error loading table"))
    .finally(hideLoader);
}

function injectTableHeader() {
  const filter = getActiveFilter();

  let headerHTML = `
    <tr>
      <th>Ticket Number</th>
      <th>Company</th>
      <th>Circuit ID</th>
      <th>Type</th>
      <th>Description</th>
      <th>Location</th>
      <th>Owner of Ticket</th>
      <th>Assigned To (Staff)</th>
      <th>Department</th>
      <th>Status</th>
  `;

  if (filter === "Resolved") {
    headerHTML += `<th>Logged At</th><th>Resolved At</th><th>Total Pending (hrs)</th><th>Actions</th>`;
  } else if (filter === "Closed") {
    headerHTML += `<th>Logged At</th><th>Closed At</th><th>Total Pending (hrs)</th><th>Actions</th>`;
  } else {
    headerHTML += `<th>Severity</th><th>Logged Time</th><th>Pending (hrs)</th><th>Actions</th>`;
  }

  headerHTML += `</tr>`;
  document.getElementById("tableHeader").innerHTML = headerHTML;
}

function openDetailsDrawer(faultId) {
  fetch(`/get_fault_details/${faultId}`)
    .then((res) => {
      if (!res.ok) throw new Error("No customer details found");
      return res.json();
    })
    .then((data) => {
      const c = data.customer;
      document.getElementById("customerCompany").textContent = c.company;
      document.getElementById("customerIP").textContent = c.ip_address;
      document.getElementById("customerPOP").textContent = c.pop_site;
      document.getElementById("customerCircuit").textContent = c.circuit_id;
      document.getElementById("customerEmail").textContent = c.email || "N/A";
      document.getElementById("customerSwitch").textContent =
        c.switch_info || "N/A";

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

      document.getElementById("detailsDrawer").classList.add("open");
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

function showLoader() {
  document.querySelector(".table-loader").classList.remove("hidden");
}

function hideLoader() {
  document.querySelector(".table-loader").classList.add("hidden");
}

function getActiveFilter() {
  const activeTab = document.querySelector(".tab.active");
  return activeTab ? activeTab.dataset.filter : "all";
}

function getSeverityFilter() {
  return sessionStorage.getItem("severityFilter") || "";
}

function setSeverityFilter(value) {
  sessionStorage.setItem("severityFilter", value);
}

function clearSeverityFilter() {
  sessionStorage.removeItem("severityFilter");
}

function getDepartmentFilter() {
  return sessionStorage.getItem("departmentFilter") || "";
}

function setDepartmentFilter(value) {
  sessionStorage.setItem("departmentFilter", value);
}

function clearDepartmentFilter() {
  sessionStorage.removeItem("departmentFilter");
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
          backgroundColor: "#1E7F34",
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
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
          borderColor: "#1E7F34",
          fill: false,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
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
          backgroundColor: ["#ffc107", "#28a745", "#dc3545"],
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
    },
  });
}
