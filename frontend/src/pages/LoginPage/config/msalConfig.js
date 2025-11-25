const msalConfig = {
  auth: {
    clientId: 'ba584753-5f5b-4e2d-9da2-3a722e97686d',
    authority:
      'https://login.microsoftonline.com/9be81a95-7870-42f4-bb8d-a44ada88130a',
    redirectUri: 'http://localhost:5173/layout/chat',
    postLogoutRedirectUri: 'http://localhost:5173/login',
  },
};

export default msalConfig;
