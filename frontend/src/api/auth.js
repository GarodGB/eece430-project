export async function login(username, password) {
  const response = await fetch('/api/login/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username, password }),
  })

  if (!response.ok) {
    if (response.status === 401 || response.status === 400) {
      throw new Error('Check your username and password.')
    }
    throw new Error('Login is unavailable. Please try again.')
  }

  const tokens = await response.json()

  const userResponse = await fetch('/api/me/', {
    headers: {
      Authorization: `Bearer ${tokens.access}`,
    },
  })

  if (!userResponse.ok) {
    throw new Error('Could not load your account. Please try logging in again.')
  }

  const user = await userResponse.json()

  return {
    user,
    accessToken: tokens.access,
    refreshToken: tokens.refresh,
  }
}