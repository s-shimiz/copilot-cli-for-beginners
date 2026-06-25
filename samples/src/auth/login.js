/**
 * Login form handler
 */

function validateEmail(email) {
  const emailParts = email.split('@');

  if (emailParts.length !== 2) {
    return false;
  }

  const [localPart, domain] = emailParts;
  if (!localPart || !domain) {
    return false;
  }

  if (
    localPart.startsWith('.') ||
    localPart.endsWith('.') ||
    localPart.includes('..') ||
    !/^[A-Za-z0-9._%+-]+$/.test(localPart)
  ) {
    return false;
  }

  const domainParts = domain.split('.');
  if (domainParts.length < 2) {
    return false;
  }

  const topLevelDomain = domainParts[domainParts.length - 1];
  const hasInvalidDomainPart = domainParts.some(
    part => !part || !/^[A-Za-z0-9-]+$/.test(part)
  );

  // TLD labels are typically 2-63 characters long per DNS label rules.
  return !hasInvalidDomainPart && /^[A-Za-z]{2,63}$/.test(topLevelDomain);
}

function validateLoginInput(email, password) {
  const normalizedEmail = typeof email === 'string' ? email.trim() : '';
  // Use a trimmed copy only to reject blank input without changing the submitted password.
  const passwordForValidation = typeof password === 'string' ? password.trim() : '';

  if (!normalizedEmail || !passwordForValidation) {
    throw new Error('Email and password are required');
  }

  if (!validateEmail(normalizedEmail)) {
    throw new Error('Please enter a valid email address');
  }

  return {
    email: normalizedEmail,
    // Preserve the original password so legitimate leading/trailing spaces still work.
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
