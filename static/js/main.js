// ===================== AUTH PAGE TABS =====================
const tabs = document.querySelectorAll(".tab");
const forms = document.querySelectorAll(".form");

tabs.forEach(tab => {
  tab.addEventListener("click", () => {
    tabs.forEach(t => t.classList.remove("active"));
    forms.forEach(f => f.classList.remove("active"));
    tab.classList.add("active");
    const targetForm = document.getElementById(tab.dataset.target);
    if(targetForm) targetForm.classList.add("active");
  });
});

// ===================== REGISTER FORM =====================
const registerForm = document.getElementById("registerForm");
if (registerForm) {
  registerForm.addEventListener("submit", async e => {
    e.preventDefault();

    const name = document.getElementById("regName").value.trim();
    const phone = document.getElementById("regPhone").value.trim();
    const password = document.getElementById("regPassword").value.trim();

    if (!name || !phone || !password) {
      alert("All fields are required for registration!");
      return;
    }

    try {
      const res = await fetch("/register", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ name, phone, password })
      });

      const data = await res.json();

      if (data.success) {
        alert("✅ Registration successful! Please login.");
        // Reset form
        registerForm.reset();
        // Switch to login tab
        document.querySelector(".tab[data-target='loginForm']").click();
      } else {
        alert("❌ " + data.message);
      }
    } catch (err) {
      console.error(err);
      alert("❌ Something went wrong. Please try again later.");
    }
  });
}

// ===================== LOGIN FORM =====================
const loginForm = document.getElementById("loginForm");
if (loginForm) {
  loginForm.addEventListener("submit", async e => {
    e.preventDefault();

    const phone = document.getElementById("loginPhone").value.trim();
    const password = document.getElementById("loginPassword").value.trim();

    if (!phone || !password) {
      alert("Both phone and password are required!");
      return;
    }

    try {
      const res = await fetch("/login", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ phone, password })
      });

      const data = await res.json();

      if (data.success) {
        window.location.href = "/dashboard";
      } else {
        alert("❌ " + data.message);
      }
    } catch (err) {
      console.error(err);
      alert("❌ Something went wrong. Please try again later.");
    }
  });
}
