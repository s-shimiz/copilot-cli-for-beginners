const test = require('node:test');
const assert = require('node:assert/strict');

const {
  handleLogin,
  validateLoginInput
} = require('./login');

test('validateLoginInput rejects blank email and password values', () => {
  assert.throws(
    () => validateLoginInput('   ', 'password123'),
    /Email and password are required/
  );

  assert.throws(
    () => validateLoginInput('reader@example.com', '   '),
    /Email and password are required/
  );
});

test('validateLoginInput rejects invalid email formats', () => {
  for (const { email, reason } of [
    { email: 'reader-example.com', reason: 'missing @ symbol' },
    { email: 'reader@domain.', reason: 'domain ends with a dot' },
    { email: 'reader@.com', reason: 'domain starts with a dot' },
    { email: 'reader@@example.com', reason: 'contains multiple @ symbols' }
  ]) {
    assert.throws(
      () => validateLoginInput(email, 'password123'),
      {
        message: /Please enter a valid email address/
      },
      reason
    );
  }
});

test('handleLogin trims email before submitting and stores auth data', async () => {
  const originalFetch = global.fetch;
  const originalLocalStorage = global.localStorage;

  const storage = new Map();
  const user = { id: 1, name: 'Reader', email: 'reader@example.com' };

  global.localStorage = {
    getItem(key) {
      return storage.get(key) ?? null;
    },
    setItem(key, value) {
      storage.set(key, value);
    },
    removeItem(key) {
      storage.delete(key);
    }
  };

  global.fetch = async (url, options) => {
    assert.equal(url, '/api/auth/login');

    const body = JSON.parse(options.body);
    assert.deepEqual(body, {
      email: 'reader@example.com',
      password: 'password123'
    });

    return {
      ok: true,
      async json() {
        return { token: 'token-123', user };
      }
    };
  };

  try {
    const loggedInUser = await handleLogin('  reader@example.com  ', 'password123');

    assert.deepEqual(loggedInUser, user);
    assert.equal(storage.get('authToken'), 'token-123');
    assert.equal(storage.get('user'), JSON.stringify(user));
  } finally {
    global.fetch = originalFetch;
    global.localStorage = originalLocalStorage;
  }
});
