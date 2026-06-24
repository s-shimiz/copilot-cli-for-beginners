/**
 * Login form handler
 */

function validateEmail(email) {
  // Allow a standard local part, require dot-separated domains, and reject consecutive dots.
  const emailRegex = /^(?!.*\.\.)([A-Za-z0-9._%+-]+)@([A-Za-z0-9-]+\.)+[A-Za-z]{2,}$/;
  return emailRegex.test(email);
}

function validateLoginInput(email, password) {
  const normalizedEmail = typeof email === 'string' ? email.trim() : '';
  const trimmedPassword = typeof password === 'string' ? password.trim() : '';

  if (!normalizedEmail || !trimmedPassword) {
    throw new Error('Email and password are required');
  }

  if (!validateEmail(normalizedEmail)) {
    throw new Error('Please enter a valid email address');
  }

  return {
    email: normalizedEmail,
    password
  };
}

async function handleLogin(email, password) {
  const validatedInput = validateLoginInput(email, password);

  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(validatedInput)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || 'Login failed');
  }

  const data = await response.json();

  // Store token
  localStorage.setItem('authToken', data.token);
  localStorage.setItem('user', JSON.stringify(data.user));

  return data.user;
}

function isLoggedIn() {
  return !!localStorage.getItem('authToken');
}

function logout() {
  localStorage.removeItem('authToken');
  localStorage.removeItem('user');
  window.location.href = '/login';
}

function getCurrentUser() {
  const userStr = localStorage.getItem('user');
  return userStr ? JSON.parse(userStr) : null;
}

module.exports = {
  handleLogin,
  validateEmail,
  validateLoginInput,
  isLoggedIn,
  logout,
  getCurrentUser
};
