const loginSection = document.getElementById("loginSection");
const chatSection = document.getElementById("chatSection");
const loginForm = document.getElementById("loginForm");
const chatWindow = document.getElementById("chatWindow");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const logoutBtn = document.getElementById("logoutBtn");
const userDisplay = document.getElementById("userDisplay");
const roleDisplay = document.getElementById("roleDisplay");
const loginError = document.getElementById("loginError");
const auditLogWindow = document.getElementById("auditLogWindow");
const refreshLogsBtn = document.getElementById("refreshLogsBtn");
const menuDropdown = document.getElementById("menuDropdown");
const commandSelect = document.getElementById("commandSelect");
const selectBtn = document.getElementById("selectBtn");

let currentUser = null;
let accessToken = null;
let pendingAction = null;
let selectedCommand = null;
let formData = null;

// Check if user is already logged in
function checkAuth() {
  const token = localStorage.getItem("accessToken");
  const user = localStorage.getItem("currentUser");
  if (token && user) {
    accessToken = token;
    currentUser = JSON.parse(user);
    showChat();
  } else {
    showLogin();
  }
}

function showLogin() {
  loginSection.style.display = "block";
  chatSection.style.display = "none";
  chatWindow.innerHTML = "";
}

function showChat() {
  loginSection.style.display = "none";
  chatSection.style.display = "block";
  userDisplay.textContent = `${currentUser.username}`;
  
  // Set role badge with different colors
  roleDisplay.textContent = currentUser.role.toUpperCase();
  roleDisplay.className = `role-badge ${currentUser.role}`;
  
  // Clear the chat window before displaying the welcome message
  chatWindow.innerHTML = "";
  
  // Display welcome message and menu
  appendMessage("system", `Welcome ${currentUser.username}! Please select what you'd like to do.`);
  displayMenuDropdown([
    "1. Add a new member",
    "2. Update a member",
    "3. Delete a member",
    "4. Show all members",
    "5. Query you want to perform"
  ]);
}

function switchTab(tabName) {
  // Hide all tab content
  document.querySelectorAll(".tab-content").forEach(tab => {
    tab.classList.remove("active");
  });
  
  // Remove active class from all tab buttons
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.classList.remove("active");
  });
  
  // Show selected tab
  document.getElementById(tabName + "Tab").classList.add("active");
  document.getElementById(tabName + "TabBtn").classList.add("active");
  
  // Load audit logs if switching to audit tab
  if (tabName === "audit") {
    loadAuditLogs();
  }
}

function appendMessage(sender, text) {
  const bubble = document.createElement("div");
  bubble.className = `msg ${sender}`;
  bubble.textContent = text;
  chatWindow.appendChild(bubble);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function appendTable(rows) {
  if (!rows || rows.length === 0) {
    appendMessage("system", "No records found.");
    return;
  }

  const wrapper = document.createElement("div");
  wrapper.className = "msg system";

  const table = document.createElement("table");
  table.className = "result-table";

  const headers = Object.keys(rows[0]);
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");

  headers.forEach((header) => {
    const th = document.createElement("th");
    th.textContent = header;
    headerRow.appendChild(th);
  });

  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    headers.forEach((header) => {
      const td = document.createElement("td");
      td.textContent = row[header] ?? "";
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  table.appendChild(tbody);
  wrapper.appendChild(table);
  chatWindow.appendChild(wrapper);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function normalizeConfirmWord(text) {
  return ["yes", "y", "confirm", "proceed"].includes(text.trim().toLowerCase());
}

async function sendQuery(payload) {
  const response = await fetch("/query", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${accessToken}`
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    if (response.status === 401) {
      logout();
      throw new Error("Session expired. Please login again.");
    }
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Request failed.");
  }

  return response.json();
}

async function loadAuditLogs() {
  try {
    const response = await fetch("/audit-logs", {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${accessToken}`
      }
    });

    if (!response.ok) {
      auditLogWindow.innerHTML = `<p class="error">Failed to load audit logs</p>`;
      return;
    }

    const data = await response.json();
    const logs = data.logs;

    if (!logs || logs.length === 0) {
      auditLogWindow.innerHTML = `<p class="info">No activity logs found</p>`;
      return;
    }

    // Create table for logs
    const table = document.createElement("table");
    table.className = "audit-table";
    
    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");
    
    const headers = ["Timestamp", "User", "Role", "Action", "Table", "Details"];
    headers.forEach(header => {
      const th = document.createElement("th");
      th.textContent = header;
      headerRow.appendChild(th);
    });
    
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    logs.forEach(log => {
      const tr = document.createElement("tr");
      
      const td1 = document.createElement("td");
      const timestamp = new Date(log.timestamp);
      td1.textContent = timestamp.toLocaleString();
      tr.appendChild(td1);
      
      const td2 = document.createElement("td");
      td2.textContent = log.username;
      tr.appendChild(td2);
      
      const td3 = document.createElement("td");
      td3.textContent = log.action;
      tr.appendChild(td3);
      
      const td4 = document.createElement("td");
      td4.textContent = log.table_name || "-";
      tr.appendChild(td4);
      
      const td5 = document.createElement("td");
      td5.textContent = log.record_id || "-";
      tr.appendChild(td5);
      
      const td6 = document.createElement("td");
      td6.textContent = log.details ? log.details.substring(0, 50) + "..." : "-";
      tr.appendChild(td6);
      
      tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    auditLogWindow.innerHTML = "";
    auditLogWindow.appendChild(table);
  } catch (error) {
    auditLogWindow.innerHTML = `<p class="error">Error loading audit logs: ${error.message}</p>`;
  }
}

// Login handler
loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;

  try {
    const response = await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      loginError.textContent = errorData.detail || "Login failed";
      return;
    }

    const data = await response.json();
    accessToken = data.access_token;
    currentUser = data.user;

    localStorage.setItem("accessToken", accessToken);
    localStorage.setItem("currentUser", JSON.stringify(currentUser));

    loginError.textContent = "";
    loginForm.reset();
    showChat();
  } catch (error) {
    loginError.textContent = "An error occurred during login";
  }
});

// Logout handler
logoutBtn.addEventListener("click", logout);

function logout() {
  localStorage.removeItem("accessToken");
  localStorage.removeItem("currentUser");
  accessToken = null;
  currentUser = null;
  pendingAction = null;
  selectedCommand = null;
  formData = null;
  chatWindow.innerHTML = "";
  auditLogWindow.innerHTML = "";
  loginError.textContent = "";
  hideMenuDropdown();
  showLogin();
}

// Chat form handler
chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value;
  if (!message && formData === null) { // Only block if not in a form and input is empty
    return;
  }

  appendMessage("user", message);
  messageInput.value = "";

  try {
    let payload;

    if (pendingAction && normalizeConfirmWord(message)) {
      console.log("DEBUG: Confirmation detected. pendingAction=", pendingAction);
      payload = {
        message,
        confirm: true,
        pending_action: pendingAction,
      };
      console.log("DEBUG: Confirmation payload=", payload);
    } else {
      console.log("DEBUG: Not a confirmation. pendingAction=", pendingAction, "normalizeConfirmWord=", normalizeConfirmWord(message));
      pendingAction = null;
      payload = { message };
      
      // Add selected command if in menu selection mode
      if (selectedCommand) {
        payload.selected_command = selectedCommand;
      }
      
      // Add form data if collecting form
      if (formData !== null) {
        payload.form_data = formData;
      }
    }

    const data = await sendQuery(payload);
    appendMessage("system", data.message || "Done.");

    // FIRST: Display results table if available (do this BEFORE showing menu)
    if (data.result?.rows) {
      appendTable(data.result.rows);
    }

    // Display other result data if not a select action
    if (data.result && data.action?.action !== "select") {
      appendMessage("system", JSON.stringify(data.result, null, 2));
    }

    // THEN: Handle menu display
    if (data.show_menu && data.menu_options) {
      displayMenuDropdown(data.menu_options);
      messageInput.value = "";
      return;
    } else {
      hideMenuDropdown();
    }

    // Handle form collection
    if (data.collecting_form) {
      formData = data.form_data || {};
      messageInput.placeholder = "Enter the requested information";
      messageInput.value = "";
      return;
    } else {
      formData = null;
      selectedCommand = null;
      messageInput.placeholder = "Type a command (e.g. Show all choir members)";
    }

    if (data.requires_confirmation && data.action) {
      console.log("DEBUG: Setting pendingAction from requires_confirmation response");
      pendingAction = data.action;
      // Clear form state when waiting for confirmation
      formData = null;
      selectedCommand = null;
      messageInput.placeholder = "Type 'yes' to confirm or 'cancel' to abort";
      messageInput.value = "";
      appendMessage("system", "Type 'yes' to confirm this action.");
      return;
    } else {
      console.log("DEBUG: Not setting pendingAction. requires_confirmation=", data.requires_confirmation, "action=", data.action);
    }

    // After a successful action, reset to the main menu
    if (data.action_completed) {
      // Instead of just showing the chat, which might not reset everything,
      // let's explicitly call the function that shows the welcome/menu.
      showChat();
      return; // Stop further processing
    }

    // If we are not in a form and no other specific action, reset placeholder
    if (formData === null) {
      messageInput.placeholder = "Type a command (e.g. Show all choir members)";
    }
  } catch (error) {
    appendMessage("system", `Error: ${error.message}`);
    // On error, also reset to a known state
    showChat();
  }
});

// Menu dropdown handler
selectBtn.addEventListener("click", async (event) => {
  event.preventDefault();
  const selectedValue = commandSelect.value;
  
  if (!selectedValue) {
    appendMessage("system", "Please select a command first.");
    return;
  }

  // Map the display text to command value
  const commandMap = {
    "1. Add a new member": "add",
    "2. Update a member": "update",
    "3. Delete a member": "delete",
    "4. Show all members": "show",
    "5. Query you want to perform": "query"
  };
  
  const command = commandMap[selectedValue] || selectedValue;
  selectedCommand = command;
  
  // Clear chat for a fresh start with new command
  chatWindow.innerHTML = "";
  
  appendMessage("user", selectedValue);
  hideMenuDropdown();
  chatForm.style.display = "grid";
  
  // Send the selection to backend
  try {
    const payload = {
      message: selectedValue,
      selected_command: command
    };
    
    const data = await sendQuery(payload);
    appendMessage("system", data.message || "Done.");
    
    console.log("DEBUG selectBtn response:", data);
    console.log("DEBUG result:", data.result);
    console.log("DEBUG result.rows:", data.result?.rows);
    
    // FIRST: Display results table if available (do this BEFORE showing menu)
    if (data.result && data.result.rows && data.result.rows.length > 0) {
      console.log("DEBUG: Displaying table with", data.result.rows.length, "rows");
      appendTable(data.result.rows);
    } else if (data.result && Array.isArray(data.result)) {
      // In case result is directly an array
      console.log("DEBUG: Result is an array, displaying table");
      appendTable(data.result);
    }
    
    // Display other result data if not a select action
    if (data.result && data.action?.action !== "select") {
      appendMessage("system", JSON.stringify(data.result, null, 2));
    }
    
    // Handle form collection
    if (data.collecting_form) {
      formData = data.form_data || {};
      messageInput.placeholder = "Enter the requested information";
      messageInput.value = "";
      messageInput.focus();
      return;
    }
    
    // THEN: Handle menu display
    if (data.show_menu && data.menu_options) {
      displayMenuDropdown(data.menu_options);
      return;
    }
    
    messageInput.value = "";
    messageInput.focus();
  } catch (error) {
    appendMessage("system", `Error: ${error.message}`);
  }
});

function displayMenuDropdown(options) {
  menuDropdown.style.display = "block";
  chatForm.style.display = "none";
  commandSelect.innerHTML = '<option value="">Choose an action...</option>';
  
  options.forEach(option => {
    const optElement = document.createElement("option");
    optElement.value = option;
    optElement.textContent = option;
    commandSelect.appendChild(optElement);
  });
  
  commandSelect.focus();
}

function hideMenuDropdown() {
  menuDropdown.style.display = "none";
  chatForm.style.display = "grid";
  commandSelect.innerHTML = '<option value="">Choose an action...</option>';
  messageInput.focus();
}

// Refresh logs button
refreshLogsBtn.addEventListener("click", loadAuditLogs);

// Initialize app
checkAuth();

// Show welcome message after login
function showWelcomeMessage() {
  appendMessage(
    "system",
    `Welcome ${currentUser.username}! Try: 'Add a new member John Doe with phone 0240000000 in the choir'`
  );
}
