// import { PublicClientApplication } from '@azure/msal-browser';
// import msalConfig from './pages/LoginPage/config/msalConfig';

// export const msalInstance = new PublicClientApplication(msalConfig);


import { PublicClientApplication } from "@azure/msal-browser";

export const msalConfig = {
  auth: {
    clientId: 'b3c486e5-cc94-441e-91fc-8a7c068ce579',
    authority:
      'https://login.microsoftonline.com/cec3b02a-ea8c-40ed-a66f-a89023ac3286',
    redirectUri: 'http://localhost:5173/layout',
    postLogoutRedirectUri: 'http://localhost:5173/login',
  },
  cache: {
    cacheLocation: "localStorage",
    storeAuthStateInCookie: false,
  },
};

export const msalInstance = new PublicClientApplication(msalConfig);

