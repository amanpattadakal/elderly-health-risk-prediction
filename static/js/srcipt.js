function showError(id, msg) {
    const error = document.getElementById(id);
    error.style.display = "block";
    error.textContent = msg;
}

function hideError(id) {
    document.getElementById(id).style.display = "none";
}

/* LOGIN VALIDATION */
function validateLogin() {
    let email = document.getElementById("login-email");
    let pass = document.getElementById("login-pass");
    let ok = true;

    if (!email.value.includes("@")) {
        showError("email-error", "Invalid email");
        ok = false;
    } else hideError("email-error");

    if (pass.value.length < 6) {
        showError("pass-error", "Password must be 6+ characters");
        ok = false;
    } else hideError("pass-error");

    return ok;
}

/* REGISTER VALIDATION */
function validateRegister() {
    let name = document.getElementById("reg-name");
    let email = document.getElementById("reg-email");
    let pass = document.getElementById("reg-pass");
    let cpass = document.getElementById("reg-cpass");
    let ok = true;

    if (name.value.trim() === "") {
        showError("name-error", "Name required");
        ok = false;
    } else hideError("name-error");

    if (!email.value.includes("@")) {
        showError("email-error", "Invalid email");
        ok = false;
    } else hideError("email-error");

    if (pass.value.length < 6) {
        showError("pass-error", "Password too short");
        ok = false;
    } else hideError("pass-error");

    if (pass.value !== cpass.value) {
        showError("cpass-error", "Passwords don't match");
        ok = false;
    } else hideError("cpass-error");

    return ok;
}
