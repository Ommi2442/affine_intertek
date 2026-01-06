const msalConfig = {
  auth: {
    clientId: 'b3c486e5-cc94-441e-91fc-8a7c068ce579',
    authority:
      'https://login.microsoftonline.com/cec3b02a-ea8c-40ed-a66f-a89023ac3286',
    redirectUri: 'https://red-cliff-09de2ee0f.3.azurestaticapps.net/layout',
    postLogoutRedirectUri: 'https://red-cliff-09de2ee0f.3.azurestaticapps.net/login',
  },
  cache: {
    cacheLocation: 'sessionStorage',
    storeAuthStateInCookie: false,
  },
};

export default msalConfig;
